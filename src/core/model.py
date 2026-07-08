"""FIBE fishery model: main Mesa model class.

Defines ``FisheryModel``, which orchestrates spatial patch initialisation,
agent creation, daily stepping, data collection, and optional Ecospace
coupling.
"""

import logging
import os
import random
from collections import defaultdict
from datetime import datetime
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from mesa import Model
from mesa.datacollection import DataCollector
from mesa.space import MultiGrid

from src.core import config
from src.domain.environment.hotspots import get_hotspots_for_step
from src.domain.environment.grid import init_patches as init_patches_helper
from src.domain.environment.patches import set_patch_fish_stock
from src.domain.environment.patches import get_patch_info as get_patch_info_helper
from src.domain.environment.stock_ops import reduce_stock as reduce_stock_helper
from src.domain.environment.regions import (
    get_carrying_capacity as get_carrying_capacity_helper,
    get_density as get_density_helper,
    get_region as get_region_helper,
)
from src.domain.environment.spatial_index import (
    build_density_map_exact as build_density_map_exact_helper,
    build_density_offsets as build_density_offsets_helper,
    prepare_spatial_indexes as prepare_spatial_indexes_helper,
)
from src.domain.environment.stock_ops import (
    _recalculate_regional_capacities as recalculate_regional_capacities_helper,
    update_patches as update_patches_helper,
    validate_regional_stocks as validate_regional_stocks_helper,
)
from src.domain.environment.utils import (
    get_random_position_in_region as get_random_position_in_region_helper,
    restricted_area as restricted_area_helper,
)
from src.domain.environment.weather import determine_weather as determine_weather_helper
from src.domain.environment.fish_dynamics import (
    update_fish_stock as update_fish_stock_helper,
    update_fish_stock_yearly as update_fish_stock_yearly_helper,
)
from src.domain.agents.factory import create_agents as create_agents_helper
from src.servicies.coupling_service import (
    wait_for_coupling_update as wait_for_coupling_update_helper,
    read_csv_biomass as read_csv_biomass_helper,
    update_biomass as update_biomass_helper,
)
from src.servicies.metrics import (
    append_daily_agent_rows_for_monthly_export as append_daily_agent_rows_for_monthly_export_helper,
    build_datacollector as build_datacollector_helper,
    build_daily_agent_metrics_cache as build_daily_agent_metrics_cache_helper,
    collect_yearly_data as collect_yearly_data_helper,
    calculate_gini as calculate_gini_helper,
    export_monthly_agent_buffer as export_monthly_agent_buffer_helper,
    get_total_catch_all_agents as get_total_catch_all_agents_helper,
    safe_mean as safe_mean_helper,
    safe_median as safe_median_helper,
)
from src.interfaces.cli.report import print_final_summary as print_final_summary_helper
from src.servicies.coupling_service import wait_for_coupling_update, read_csv_biomass, update_biomass

logger = logging.getLogger(__name__)
class FisheryModel(Model):
    """Agent-based fishery model built on Mesa.

    Manages the spatial grid, fish-stock dynamics, fisher agents, data
    collection, and optional coupling with an Ecospace biomass model.

    Attributes:
        current_step: Current simulation day (incremented each ``step``).
        end_of_sim: Total number of days to simulate.
        verbose: Whether to print progress messages.
        coupling: Whether Ecospace coupling is enabled.
        bad_weather: Whether today is a bad-weather day.
        patches: Dict mapping ``(x, y)`` to patch attribute dicts.
        yearly_data: List of yearly summary dicts accumulated over the run.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        end_of_sim: int,
        num_archipelago: int,
        num_coastal: int,
        num_trawler: int,
        verbose: bool = True,
        growth_rate: Optional[float] = None,
        fish_price: Optional[float] = None,
        bad_weather_probability: Optional[float] = None,
        initial_capital: Optional[float] = None,
        archipelago_names: Optional[List[str]] = None,
        coastal_names: Optional[List[str]] = None,
        trawler_names: Optional[List[str]] = None,
        coupling: Optional[bool] = None,
        config_loader: Optional[Any] = None,
    ) -> None:
        """Initialises the fishery model.

        Args:
            end_of_sim: Number of simulation days to run.
            num_archipelago: Number of archipelago-type fishers.
            num_coastal: Number of coastal-type fishers.
            num_trawler: Number of trawler-type fishers.
            verbose: If True, prints progress information.
            growth_rate: Annual logistic growth rate override. Uses
                ``config.GROWTH_RATE`` if None.
            fish_price: Fish market price override (SEK). Uses
                ``config.FISH_PRICE`` if None.
            bad_weather_probability: Daily bad-weather probability
                override. Uses ``config.BAD_WEATHER_PROBABILITY`` if
                None.
            initial_capital: Starting capital override (SEK). Uses
                ``config.INITIAL_CAPITAL`` if None.
            archipelago_names: Optional list of names for archipelago
                agents.
            coastal_names: Optional list of names for coastal agents.
            trawler_names: Optional list of names for trawler agents.
            coupling: Whether to enable Ecospace biomass coupling.
        """
        super().__init__()

        self.coupling = coupling
        self.verbose = verbose
        self.current_step = 0
        self.end_of_sim = end_of_sim

        self.num_archipelago = num_archipelago
        self.num_coastal = num_coastal
        self.num_trawler = num_trawler

        self.archipelago_names = archipelago_names
        self.coastal_names = coastal_names
        self.trawler_names = trawler_names
        self.config_loader = config_loader

        self.social_influence = config.SOCIAL_INFLUENCE

        # Time constants
        self.WEEK = config.WEEK
        self.MONTH = config.MONTH
        self.SEASON = config.SEASON
        self.HALFYEAR = config.HALFYEAR
        self.YEAR = config.YEAR

        # Weather
        self.bad_weather = False
        self.bad_weather_probability = (
            float(bad_weather_probability)
            if bad_weather_probability is not None
            else config.BAD_WEATHER_PROBABILITY
        )

        # Spatial regions
        self.REGION_A = config.REGION_A
        self.REGION_B = config.REGION_B
        self.REGION_C = config.REGION_C
        self.REGION_D = config.REGION_D
        self.LAND = config.LAND

        # Density labels
        self.LOW = config.LOW
        self.MEDIUM = config.MEDIUM
        self.HIGH = config.HIGH
        self.MEDIUM_HIGH = config.MEDIUM_HIGH
        self.LOW_MEDIUM = config.LOW_MEDIUM

        # Existence costs (by vessel type)
        self.LOW_COST_EXISTENCE = config.ARCHIPELAGO_COST_EXISTENCE
        self.MEDIUM_COST_EXISTENCE = config.COASTAL_COST_EXISTENCE
        self.HIGH_COST_EXISTENCE = config.TRAWLER_COST_EXISTENCE

        # Activity costs
        self.LOW_COST_ACTIVITY = config.ARCHIPELAGO_COST_ACTIVITY
        self.MEDIUM_COST_ACTIVITY = config.COASTAL_COST_ACTIVITY
        self.HIGH_COST_ACTIVITY = config.TRAWLER_COST_ACTIVITY

        # Travel costs
        self.LOW_COST_TRAVEL = config.LOW_COST_TRAVEL
        self.MEDIUM_COST_TRAVEL = config.MEDIUM_COST_TRAVEL
        self.MEDIUM_COST_TRAVEL_BIGVESSEL = config.MEDIUM_COST_TRAVEL_BIGVESSEL
        self.HIGH_COST_TRAVEL = config.HIGH_COST_TRAVEL

        # Carrying capacities
        self.LOW_CARRYING_CAPACITY = config.LOW_CARRYING_CAPACITY
        self.MEDIUM_CARRYING_CAPACITY = config.MEDIUM_CARRYING_CAPACITY
        self.HIGH_CARRYING_CAPACITY = config.HIGH_CARRYING_CAPACITY
        self.CARRYING_CAPACITY_A = config.CARRYING_CAPACITY_A_INITIAL
        self.CARRYING_CAPACITY_B = config.CARRYING_CAPACITY_B_INITIAL
        self.CARRYING_CAPACITY_C = config.CARRYING_CAPACITY_C_INITIAL
        self.CARRYING_CAPACITY_D = config.CARRYING_CAPACITY_D_INITIAL

        # MSY levels
        self.MSY_STOCK_A = config.get_msy_stock(self.CARRYING_CAPACITY_A)
        self.MSY_STOCK_B = config.get_msy_stock(self.CARRYING_CAPACITY_B)
        self.MSY_STOCK_C = config.get_msy_stock(self.CARRYING_CAPACITY_C)
        self.MSY_STOCK_D = config.get_msy_stock(self.CARRYING_CAPACITY_D)

        # Catchability
        self.CATCHABILITY_ARCHEPELAGO = config.ARCHIPELAGO_CATCHABILITY
        self.CATCHABILITY_COASTAL = config.COASTAL_CATCHABILITY
        self.CATCHABILITY_TRAWLER = config.TRAWLER_CATCHABILITY
        self.SD_CARCAP = config.SD_CARCAP

        # Initial hotspots
        self.HOTSPOTS_A = get_hotspots_for_step(0, "A")
        self.HOTSPOTS_B = get_hotspots_for_step(0, "B")
        self.HOTSPOTS_C = get_hotspots_for_step(0, "C")
        self.HOTSPOTS_D = get_hotspots_for_step(0, "D")

        # Economic parameters
        self.GROWTH_RATE = (
            float(growth_rate)
            if growth_rate is not None
            else config.GROWTH_RATE
        )
        self.FISH_PRICE = (
            float(fish_price)
            if fish_price is not None
            else config.FISH_PRICE
        )
        self.initial_capital = (
            float(initial_capital)
            if initial_capital is not None
            else config.INITIAL_CAPITAL
        )
        self.init_stock_size = config.INIT_STOCK_SIZE

        # Spatial grid
        self.grid = MultiGrid(
            config.GRID_WIDTH, config.GRID_HEIGHT, torus=False
        )

        # Internal caches and buffers
        self._region_stock_cache: Dict[str, float] = {
            "A": 0, "B": 0, "C": 0, "D": 0, "TOTAL": 0
        }
        self._daily_agent_metrics: Dict[str, Any] = {}
        self._monthly_agent_rows: List[Dict[str, Any]] = []
        self.yearly_data: List[Dict[str, Any]] = []
        self.last_year_catches: Dict[int, float] = {}

        # Patch and agent initialisation
        self.init_patches()
        self._initialize_region_stock_cache()

        if self.verbose:
            logger.info("\n" + "=" * 60)
            logger.info("HOTSPOT DISTRIBUTION")
            logger.info("\n" + "=" * 60)
            self.validate_hotspot_distribution()

        self._recalculate_regional_capacities()
        self._create_agents()

        self.num_fishing_midday = sum(
            1 for a in self.agents if a.gone_fishing
        )
        self.num_at_home_midday = sum(
            1 for a in self.agents if a.at_home
        )
        self.num_fished_today = 0

        self.datacollector = self._build_datacollector()
        self._build_daily_agent_metrics_cache()
        self.datacollector.collect(self)

    def init_patches(self) -> None:
        init_patches_helper(self)

    def _prepare_spatial_indexes(self) -> None:
        prepare_spatial_indexes_helper(self)

    def _build_density_offsets(self) -> None:
        build_density_offsets_helper(self)

    def _build_density_map_exact(self) -> None:
        build_density_map_exact_helper(self)

    def _set_patch_fish_stock(self, pos, new_stock):
        return set_patch_fish_stock(self, pos, new_stock)

    def _initialize_region_stock_cache(self) -> None:
        self._region_stock_cache = {
            region: sum(
                patch["fish_stock"]
                for patch in self.patches.values()
                if patch["region"] == region
            )
            for region in ("A", "B", "C", "D")
        }
        self._region_stock_cache["TOTAL"] = sum(
            self._region_stock_cache[region]
            for region in ("A", "B", "C", "D")
        )

    def _recalculate_regional_capacities(self) -> None:
        recalculate_regional_capacities_helper(self)

    def _create_agents(self) -> None:
        create_agents_helper(self)

    def _get_random_position_in_region(self, region: str):
        return get_random_position_in_region_helper(self, region)

    def restricted_area(self, habitat):
        return restricted_area_helper(self, habitat)

    def get_region(self, x: int, y: int) -> str:
        return get_region_helper(self, x, y)

    def get_density(self, x: int, y: int, region: str):
        return get_density_helper(self, x, y, region)

    def get_patch_info(self, x: int, y: int):
        return get_patch_info_helper(self, x, y)

    def reduce_stock(self, x: int, y: int, catch_amount: float) -> float:
        return reduce_stock_helper(self, x, y, catch_amount)

    def get_carrying_capacity(self, region: str, density):
        return get_carrying_capacity_helper(self, region, density)

    def determine_weather(self) -> bool:
        return determine_weather_helper(self)

    def update_fish_stock(self, time_step_days: int = 1) -> None:
        update_fish_stock_helper(self, time_step_days=time_step_days)

    def update_fish_stock_yearly(self) -> None:
        update_fish_stock_yearly_helper(self)

    def update_patches(self, new_fish_stocks):
        return update_patches_helper(self, new_fish_stocks)

    def validate_regional_stocks(self):
        return validate_regional_stocks_helper(self)

    def _wait_for_coupling_update(self, json_path: str = "config/config.json", poll_interval: float = 0.5):
        return wait_for_coupling_update_helper(self, json_path=json_path, poll_interval=poll_interval)

    def _read_csv_biomass(self):
        return read_csv_biomass_helper(self)

    def _update_biomass(self, species_maps):
        return update_biomass_helper(self, species_maps)

    def _build_datacollector(self):
        return build_datacollector_helper(self)

    def _build_daily_agent_metrics_cache(self) -> None:
        build_daily_agent_metrics_cache_helper(self)

    def _append_daily_agent_rows_for_monthly_export(self) -> None:
        append_daily_agent_rows_for_monthly_export_helper(self)

    def _export_monthly_agent_buffer(self) -> None:
        export_monthly_agent_buffer_helper(self)

    def collect_yearly_data(self):
        return collect_yearly_data_helper(self)

    def get_total_catch_all_agents(self) -> float:
        return get_total_catch_all_agents_helper(self)

    def _safe_mean(self, values):
        return safe_mean_helper(self, values)

    def _safe_median(self, values):
        return safe_median_helper(self, values)

    def calculate_gini(self, values):
        return calculate_gini_helper(self, values)

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------


    def validate_hotspot_distribution(self) -> None:
        """Prints density distribution statistics for each region.

        For each region, counts patches labelled HIGH, MEDIUM, and LOW
        and prints the percentages.
        """
        for region_name in ("A", "B", "C", "D"):
            high_count = 0
            medium_count = 0
            low_count = 0

            for patch in self.patches.values():
                if patch["region"] == region_name:
                    density = patch["density"]
                    if density == self.HIGH:
                        high_count += 1
                    elif density == self.MEDIUM:
                        medium_count += 1
                    elif density == self.LOW:
                        low_count += 1

            total = high_count + medium_count + low_count
            if total > 0:
                logger.info(f"Region {region_name}:")
                logger.info(
                    "Density distribution",
                    extra={
                        "HIGH": high_count,
                        "MEDIUM": medium_count,
                        "LOW": low_count
                    }
                )
    def get_initial_fish_stock(
        self, carrying_capacity: int, region: str
    ) -> int:
        """Returns the initial fish stock for a patch (NetLogo-aligned).

        Args:
            carrying_capacity: Carrying capacity of the patch.
            region: Region label; LAND / NULL cells always return 0.

        Returns:
            Initial fish stock according to ``config.INIT_STOCK_SIZE``.

        Raises:
            ValueError: If ``config.INIT_STOCK_SIZE`` is not a
                recognised mode.
        """
        if region in ("LAND", "NULL"):
            return 0

        mode = config.INIT_STOCK_SIZE

        if mode == "random":
            return (
                self.random.randrange(carrying_capacity)
                if carrying_capacity > 0
                else 0
            )
        if mode == "carryingCap":
            return round(carrying_capacity)
        if mode == "halfCarryingCap":
            return round(0.5 * carrying_capacity)
        if mode == "quartCarryingCap":
            return round(0.25 * carrying_capacity)

        raise ValueError(
            f"Invalid initial stock size mode: {mode}"
        )

    # ------------------------------------------------------------------
    # Stock queries
    # ------------------------------------------------------------------

    def get_region_stock(self, region_name: str) -> float:
        """Returns the cached total stock for a region.

        Args:
            region_name: Region identifier.

        Returns:
            Current fish stock total, or 0 if the region is unknown.
        """
        return self._region_stock_cache.get(region_name, 0)

    def get_total_stock(self) -> float:
        """Returns the total fish stock across all fishing regions.

        Returns:
            Sum of fish stocks in all non-LAND regions.
        """
        return self._region_stock_cache["TOTAL"]

    def get_region_carrying_capacity(self, region_name: str) -> float:
        """Returns the total carrying capacity for a region.

        Args:
            region_name: Region identifier.

        Returns:
            Carrying capacity, or 0 for LAND / NULL / unknown regions.
        """
        capacities: Dict[str, float] = {
            "A": self.CARRYING_CAPACITY_A,
            "B": self.CARRYING_CAPACITY_B,
            "C": self.CARRYING_CAPACITY_C,
            "D": self.CARRYING_CAPACITY_D,
            "LAND": 0,
            "NULL": 0,
        }
        return capacities.get(region_name, 0)


    

    # ------------------------------------------------------------------
    # Main step
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Advances the model by one day.

        Execution order:

        1. Determine weather.
        2. If year boundary: apply yearly stock growth, reset agent
           counters, print verbose summary, collect yearly data.
        3. Reset daily flags on all agents.
        4. Each agent acts; midday counters updated.
        5. Rebuild metrics cache; DataCollector collects.
        6. Append agent rows to the monthly buffer.
        7. Finalize day on all agents.
        8. Log yearly summary (verbose).
        9. Increment ``current_step``.
        10. Check end condition.
        11. Monthly updates (hotspots, coupling export).
        """
        # 1. Weather
        self.determine_weather()

        is_new_year = (
            self.current_step % self.YEAR == 0 and self.current_step > 0
        )
        yearly_summary = None
        yearly_catch = 0.0

        # 2. Yearly actions
        if is_new_year:
            self.update_fish_stock_yearly()

            for agent in self.agents:
                agent.reset_yearly_counters()

            if self.verbose:
                print(f"\n{'=' * 60}")
                print(f"{'=' * 60}")
                active = [a for a in self.agents if not a.bankrupt]
                bankrupt = [a for a in self.agents if a.bankrupt]
                print(
                    f"\nAgents: {len(active)} active,"
                    f" {len(bankrupt)} bankrupt"
                )
                if active:
                    avg_capital = (
                        sum(a.capital for a in active) / len(active)
                    )
                    avg_catch = (
                        sum(a.accumulated_catch for a in active)
                        / len(active)
                    )
                    print(f"Average capital: {avg_capital:.0f} SEK")
                    print(f"Average catch: {avg_catch:.0f} fish")
                    for ftype in ("archipelago", "coastal", "trawler"):
                        type_agents = [
                            a for a in active if a.fisher_type == ftype
                        ]
                        if type_agents:
                            avg_cap = (
                                sum(a.capital for a in type_agents)
                                / len(type_agents)
                            )
                            print(
                                f"  {ftype.capitalize()}:"
                                f" {len(type_agents)} agents,"
                                f" avg capital = {avg_cap:.0f} SEK"
                            )
                print(f"{'=' * 60}\n")

            yearly_summary = self.collect_yearly_data()
            current_catches = {
                a.unique_id: a.total_catch for a in self.agents
            }
            yearly_catch = sum(
                current_catches[aid]
                - self.last_year_catches.get(aid, 0)
                for aid in current_catches
            )
            self.last_year_catches = current_catches

        # 3. Reset daily flags
        for agent in self.agents:
            agent.reset_daily_flags()

        # 4. Agents act
        self.num_fishing_midday = 0
        self.num_at_home_midday = 0
        self.num_fished_today = 0

        for agent in self.agents:
            agent.step()
            if agent.gone_fishing:
                self.num_fishing_midday += 1
            if agent.at_home:
                self.num_at_home_midday += 1
            if agent.fished_today:
                self.num_fished_today += 1

        # 5. Rebuild caches and collect
        self._build_daily_agent_metrics_cache()
        self.datacollector.collect(self)

        # 6. Monthly buffer
        self._append_daily_agent_rows_for_monthly_export()

        # 7. Finalize day
        for agent in self.agents:
            agent.finalize_day()

        # 8. Yearly logs
        if is_new_year and yearly_summary is not None and self.verbose:
            year = self.current_step // self.YEAR
            print(f"\n{'=' * 60}")
            print(f"YEAR {year} COMPLETED")
            print(f"{'=' * 60}")
            print(
                f"Stocks: A={yearly_summary['stock_A']:,.0f}"
                f" ({yearly_summary['stock_A_pct_K']:.1%}),"
                f" B={yearly_summary['stock_B']:,.0f}"
                f" ({yearly_summary['stock_B_pct_K']:.1%})"
            )
            print(f"Yearly catch: {yearly_catch:,.0f}")
            print(f"Total catch: {yearly_summary['total_catch_all']:,.0f}")
            num_ag = max(yearly_summary["num_agents"], 1)
            print(
                f"Avg capital:"
                f" {yearly_summary['total_capital'] / num_ag:,.2f}"
            )
            print(f"Gini capital: {yearly_summary['gini_capital']:.3f}")
            print(
                f"Success rate: {yearly_summary['avg_success_rate']:.1%}"
            )
            print(f"{'=' * 60}\n")

        # 9. Increment step
        self.current_step += 1

        # 10. End condition
        if self.current_step >= self.end_of_sim:
            self.running = False
            if self.verbose:
                self.print_final_summary()

        # 11. Monthly updates
        if self.current_step % self.MONTH == 0:
            self.HOTSPOTS_A = get_hotspots_for_step(
                self.current_step, "A"
            )
            self.HOTSPOTS_B = get_hotspots_for_step(
                self.current_step, "B"
            )
            self.HOTSPOTS_C = get_hotspots_for_step(
                self.current_step, "C"
            )
            self.HOTSPOTS_D = get_hotspots_for_step(
                self.current_step, "D"
            )

            if self.coupling:
                species_maps, _ = self._wait_for_coupling_update(
                    json_path="configs_json/config.json",
                    poll_interval=0.5,
                )
                fish = update_biomass(self, species_maps)
                logger.info(
                    "Stock before coupling update",
                    extra={
                        "A": self.get_region_stock("A"),
                        "B": self.get_region_stock("B"),
                        "C": self.get_region_stock("C"),
                        "D": self.get_region_stock("D"),
                    }
                )
                self.update_patches(fish)
                logger.info(
                    "Stock after coupling update",
                    extra={
                        "A": self.get_region_stock("A"),
                        "B": self.get_region_stock("B"),
                        "C": self.get_region_stock("C"),
                        "D": self.get_region_stock("D"),
                    }
                )
                self._export_monthly_agent_buffer()

    # ------------------------------------------------------------------
    # Run helpers
    # ------------------------------------------------------------------

    def run_model(self, steps: Optional[int] = None) -> None:
        """Runs the model for a given number of steps.

        Args:
            steps: Number of daily steps to execute. Defaults to
                ``end_of_sim`` if None.
        """
        if steps is None:
            steps = self.end_of_sim

        if self.verbose:
            logger.info(
                "Simulation started",
                extra={
                    "steps": steps,
                    "yaers": steps / self.YEAR,
                    "agents": len(self.agents),
                }
            )

        for _ in range(steps):
            self.step()
            if not self.running:
                break

        if self.verbose:
            logger.info(
                "Simulation completed",
                extra={
                    "days": self.current_step,
                    "years": self.current_step / self.YEAR,
                }
            )

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------



    def get_model_summary(self) -> Dict[str, Any]:
        """Returns a snapshot of the current model state.

        Returns:
            Dictionary with step, year, agent counts, stocks, catch
            total, average capital, and weather flag.
        """
        agents_list = list(self.agents)
        num_agents = len(agents_list)

        return {
            "current_step": self.current_step,
            "current_year": self.current_step // self.YEAR,
            "current_day": self.current_step % self.YEAR,
            "num_agents": num_agents,
            "num_fishing": self.num_fishing_midday,
            "num_at_home": self.num_at_home_midday,
            "num_fished_today": self.num_fished_today,
            "total_stock": self.get_total_stock(),
            "stock_A": self.get_region_stock("A"),
            "stock_B": self.get_region_stock("B"),
            "stock_C": self.get_region_stock("C"),
            "stock_D": self.get_region_stock("D"),
            "total_catch": sum(a.total_catch for a in agents_list),
            "avg_capital": (
                sum(a.capital for a in agents_list) / num_agents
                if num_agents > 0
                else 0
            ),
            "bad_weather": self.bad_weather,
        }

    def print_final_summary(self) -> None:
        print_final_summary_helper(self)
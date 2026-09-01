"""FIBE fishery model: main Mesa model class.

Defines ``FisheryModel``, which orchestrates spatial patch initialisation,
agent creation, daily stepping, data collection, and optional Ecospace
coupling.
"""

import logging
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta
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
from src.domain.environment.stock_ops import update_patches as update_patches_helper
from src.domain.environment.stock_ops import update_patches_species as update_patches_species_helper
from src.domain.environment.spatial_index import (
    build_density_map_exact as build_density_map_exact_helper,
    build_density_offsets as build_density_offsets_helper,
    prepare_spatial_indexes as prepare_spatial_indexes_helper,
)
from src.domain.environment.utils import (
    restricted_habitat as restricted_habitat_helper,
)
from src.domain.environment.restricted_areas import (
    restricted_area_status as restricted_area_status_helper,
)
from src.domain.environment.weather import determine_weather as determine_weather_helper
from src.domain.environment.fish_dynamics import (
    update_fish_stock as update_fish_stock_helper,
    update_fish_stock_yearly as update_fish_stock_yearly_helper,
)
from src.domain.agents.factory import create_agents as create_agents_helper, create_single_agent as create_single_agent_helper
from src.servicies.coupling_service import (
    wait_for_coupling_update as wait_for_coupling_update_helper,
    read_csv_biomass as read_csv_biomass_helper,
    update_biomass as update_biomass_helper,
    update_biomass_species as update_biomass_species_helper,
    read_desired_num_agents as read_desired_num_agents_helper,
)
from src.servicies.metrics import (
    append_daily_agent_rows_for_monthly_export as append_daily_agent_rows_for_monthly_export_helper,
    build_datacollector as build_datacollector_helper,
    build_daily_agent_metrics_cache as build_daily_agent_metrics_cache_helper,
    collect_yearly_data as collect_yearly_data_helper,
    calculate_gini as calculate_gini_helper,
    export_monthly_agent_buffer as export_monthly_agent_buffer_helper,
    export_monthly_fishing_mortality as export_monthly_fishing_mortality_helper,
    get_total_catch_all_agents as get_total_catch_all_agents_helper,
    safe_mean as safe_mean_helper,
    safe_median as safe_median_helper,
)
from src.interfaces.cli.report import print_final_summary as print_final_summary_helper
from src.servicies.coupling_service import wait_for_coupling_update, read_csv_biomass, update_biomass
from src.infrastructure.loader.loader import ConfigLoader
from src.domain.environment.ocean_currents import read_currents_map


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
        start_date: Optional[datetime] = None,
        config_loader: Optional[Any] = None,
        catchability_matrix: Optional[np.ndarray] = None,
        price_matrix: Optional[np.ndarray] = None,
        species_names: Optional[List[str]] = None,
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
            fish_price: Fish market price override (€). Uses
                ``config.FISH_PRICE`` if None.
            bad_weather_probability: Daily bad-weather probability
                override. Uses ``config.BAD_WEATHER_PROBABILITY`` if
                None.
            initial_capital: Starting capital override (€). Uses
                ``config.INITIAL_CAPITAL`` if None.
            archipelago_names: Optional list of names for archipelago
                agents.
            coastal_names: Optional list of names for coastal agents.
            trawler_names: Optional list of names for trawler agents.
            coupling: Whether to enable Ecospace biomass coupling.
            catchability_matrix: Per-species catchability (F, N).
            price_matrix: Per-species price (F, N).
            species_names: List of species IDs in 3D array order.
        """
        super().__init__()

        self.coupling = coupling
        self.verbose = verbose
        self.current_step = 0
        if start_date is None:
            start_date = "2024-01-01"
        self.current_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        self.end_of_sim = end_of_sim
        self.start_date = start_date

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

        # Spatial data
        self.LAND = config.LAND
        self.topology = config.TOPOLOGY

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

        # Catchability
        self.SD_CARCAP = config.SD_CARCAP

        # Species matrices
        self.catchability_matrix = catchability_matrix
        self.price_matrix = price_matrix
        self.species_names = species_names or []
        self.species_to_idx = {name: i for i, name in enumerate(self.species_names)}
        self.flotilla_indices = {
            "archipelago": 1,
            "coastal": 2,
            "trawler": 3,
        }

        # Set from init_patches
        self.species_biomass: Optional[np.ndarray] = None
        self.species_ratio: Optional[np.ndarray] = None

        # Initial hotspots
        self.HOTSPOTS = get_hotspots_for_step(0)

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
        self._region_stock_cache: Dict[str, float] = {"TOTAL": 0}
        self._daily_agent_metrics: Dict[str, Any] = {}
        self._monthly_agent_rows: List[Dict[str, Any]] = []
        self.yearly_data: List[Dict[str, Any]] = []
        self.last_year_catches: Dict[int, float] = {}

        # Last coupling step consumed
        self._coupling_step_consumed: Optional[int] = None

        # Patch and agent initialisation
        self.init_patches()
        self._initialize_stock_cache()
        self._create_agents()

        # Dynamic fleet: monotone ID and retired archive (IDs never reused)
        self._retired_agents: List[Any] = []
        self._retired_ids: set[int] = set()
        if len(self.agents) > 0:
            try:
                max_id = max(a.unique_id for a in self.agents)
                self._next_agent_id = int(max_id) + 1
            except Exception:
                self._next_agent_id = len(self.agents)
        else:
            self._next_agent_id = 0
        # Keep Mesa counter in sync to avoid collisions if Mesa creates agents
        try:
            if hasattr(self, "agent_id_counter"):
                if self._next_agent_id > self.agent_id_counter:
                    self.agent_id_counter = self._next_agent_id
        except Exception:
            pass

        n_rows, n_cols, n_species = self.species_biomass.shape
        n_flotillas = max(self.flotilla_indices.values())
        self.monthly_catch_by_flotilla = np.zeros(
            (n_flotillas + 1, n_rows, n_cols, n_species)
        )
        self.month_start_biomass = self.species_biomass.copy()

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

    def _get_carrying_capacity(self, density: Optional[str]) -> int:
        if density is None:
            return 0
        base_capacity_map = {
            "HIGH": self.HIGH_CARRYING_CAPACITY,
            "MEDIUM": self.MEDIUM_CARRYING_CAPACITY,
            "LOW": self.LOW_CARRYING_CAPACITY,
        }
        density_upper = density.upper() if isinstance(density, str) else str(density).upper()
        if density_upper not in base_capacity_map:
            return 0
        base_capacity = base_capacity_map[density_upper]
        sd = self.SD_CARCAP * base_capacity
        random_capacity = np.random.normal(base_capacity, sd)
        return max(1, round(random_capacity))

    def get_cell_value(self, x: int, y: int, fisher_type: str) -> float:
        if (x, y) in self._land_set:
            return 0.0
        f_idx = self.flotilla_indices[fisher_type]
        catchability_vec = self.catchability_matrix[f_idx]
        price_vec = self.price_matrix[f_idx]
        biomass_vec = self.species_biomass[y, x, :]
        potential_catch = np.minimum(catchability_vec, biomass_vec)
        return float(np.sum(potential_catch * price_vec))

    def get_vicinity_value(
        self, x: int, y: int, fisher_type: str, radius: int = 1
    ) -> float:
        total = 0.0
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.grid.width and 0 <= ny < self.grid.height:
                    total += self.get_cell_value(nx, ny, fisher_type)
        return total

    def _sync_patch_fish_stock(self, x: int, y: int) -> None:
        pos = (x, y)
        if pos in self.patches:
            self.patches[pos]["fish_stock"] = float(
                np.sum(self.species_biomass[y, x, :])
            )

    def _initialize_stock_cache(self) -> None:
        self._region_stock_cache["TOTAL"] = sum(
            patch["fish_stock"] for patch in self.patches.values()
        )

    def _create_agents(self) -> None:
        create_agents_helper(self)

    def _create_single_agent(self, fisher_type: str, agent_id: int) -> Any:
        return create_single_agent_helper(self, fisher_type, agent_id)

    # ------------------------------------------------------------------
    # Dynamic fleet management (IDs unique, retirement definitive)
    # ------------------------------------------------------------------

    def _retire_agents(self, fisher_type: str, n: int) -> int:
        """Retires n random active agents of a given flotilla.

        Retirement is definitive: agents are marked retired, removed from
        grid and deregistered, archived in ``_retired_agents`` and their
        IDs are never reused (requirement).

        Args:
            fisher_type: Flotilla type.
            n: Number to retire.

        Returns:
            Number actually retired.
        """
        if n <= 0:
            return 0
        candidates = [a for a in self.agents if a.fisher_type == fisher_type and not getattr(a, "retired", False)]
        if not candidates:
            return 0
        n = min(n, len(candidates))
        # Random equitable
        to_remove = self.random.sample(candidates, n) if len(candidates) > n else candidates
        retired = 0
        for agent in to_remove:
            agent.retired = True
            agent.retired_at_step = self.current_step
            # Immediate removal without landing (requirement 2)
            try:
                if getattr(agent, "pos", None) is not None:
                    self.grid.remove_agent(agent)
            except Exception:
                pass
            # Clear spatial state
            agent.current_location = None
            agent.at_sea = False
            agent.gone_fishing = False
            agent.at_home = False
            self._retired_agents.append(agent)
            self._retired_ids.add(agent.unique_id)
            try:
                agent.remove()  # Mesa deregister
            except Exception:
                # Fallback
                try:
                    self.deregister_agent(agent)
                except Exception:
                    pass
            retired += 1
            if self.verbose:
                logger.info(f"Retired agent {agent.unique_id} ({fisher_type}) at step {self.current_step}")
        # Update cached counts
        if fisher_type == "archipelago":
            self.num_archipelago = sum(1 for a in self.agents if a.fisher_type == "archipelago")
        elif fisher_type == "coastal":
            self.num_coastal = sum(1 for a in self.agents if a.fisher_type == "coastal")
        elif fisher_type == "trawler":
            self.num_trawler = sum(1 for a in self.agents if a.fisher_type == "trawler")
        return retired

    def _create_agents_batch(self, fisher_type: str, n: int) -> int:
        """Creates n new agents of a given flotilla with new IDs."""
        if n <= 0:
            return 0
        created = 0
        for _ in range(n):
            agent_id = self._next_agent_id
            self._next_agent_id += 1
            # Keep Mesa counter synced
            try:
                if agent_id >= self.agent_id_counter:
                    self.agent_id_counter = agent_id + 1
            except Exception:
                pass
            self._create_single_agent(fisher_type, agent_id)
            created += 1
            if self.verbose:
                logger.info(f"Created agent {agent_id} ({fisher_type}) at step {self.current_step}")
        if fisher_type == "archipelago":
            self.num_archipelago = sum(1 for a in self.agents if a.fisher_type == "archipelago")
        elif fisher_type == "coastal":
            self.num_coastal = sum(1 for a in self.agents if a.fisher_type == "coastal")
        elif fisher_type == "trawler":
            self.num_trawler = sum(1 for a in self.agents if a.fisher_type == "trawler")
        return created

    def _apply_fleet_resize(self, desired: Optional[Dict[str, int]]) -> None:
        """Applies desired fleet sizes per flotilla (random retire / random port create)."""
        if not desired:
            return
        # Normalize keys
        desired_norm = {
            "archipelago": int(desired.get("num_archipelago", self.num_archipelago)),
            "coastal": int(desired.get("num_coastal", self.num_coastal)),
            "trawler": int(desired.get("num_trawler", self.num_trawler)),
        }
        for ftype in ("archipelago", "coastal", "trawler"):
            current = sum(1 for a in self.agents if a.fisher_type == ftype)
            target = desired_norm[ftype]
            if target < 0:
                target = 0
            delta = target - current
            if delta < 0:
                self._retire_agents(ftype, -delta)
            elif delta > 0:
                self._create_agents_batch(ftype, delta)
        # After resize, rebuild daily cache so datacollector sees new counts next step
        try:
            self._build_daily_agent_metrics_cache()
        except Exception:
            pass

    def _read_desired_counts(self, json_path: str = "configs_json/config.json") -> Optional[Dict[str, int]]:
        return read_desired_num_agents_helper(json_path)

    def restricted_habitat(self, habitat):
        return restricted_habitat_helper(self, habitat)

    def restricted_area_status(self, flottille: str, date: datetime, zone_index: int) -> str:
        return restricted_area_status_helper(flottille, date, zone_index)

    def get_depth(self, x: int, y: int) -> int:
        if 0 <= y < len(self.topology) and 0 <= x < len(self.topology[y]):
            return self.topology[y][x]
        return 0

    def get_patch_info(self, x: int, y: int):
        return get_patch_info_helper(self, x, y)

    def reduce_stock(self, x: int, y: int, catch_amount: float) -> float:
        return reduce_stock_helper(self, x, y, catch_amount)

    def determine_weather(self) -> bool:
        return determine_weather_helper(self)

    def update_fish_stock(self, time_step_days: int = 1) -> None:
        update_fish_stock_helper(self, time_step_days=time_step_days)

    def update_fish_stock_yearly(self) -> None:
        update_fish_stock_yearly_helper(self)

    def update_patches(self, new_fish_stocks):
        return update_patches_helper(self, new_fish_stocks)

    def update_patches_species(self, species_biomass, species_names):
        return update_patches_species_helper(self, species_biomass, species_names)

    def _wait_for_coupling_update(
        self,
        json_path: str = "config/config.json",
        poll_interval: float = 0.5,
        timeout: Optional[float] = 60.0,
    ):
        return wait_for_coupling_update_helper(
            self,
            json_path=json_path,
            poll_interval=poll_interval,
            timeout=timeout,
        )

    def _read_csv_biomass(self):
        return read_csv_biomass_helper(self)

    def _update_biomass(self, species_maps):
        return update_biomass_helper(self, species_maps)

    def _update_biomass_species(self, species_maps):
        return update_biomass_species_helper(self, species_maps, self.species_names)

    def _build_datacollector(self):
        return build_datacollector_helper(self)

    def _build_daily_agent_metrics_cache(self) -> None:
        build_daily_agent_metrics_cache_helper(self)

    def _append_daily_agent_rows_for_monthly_export(self) -> None:
        append_daily_agent_rows_for_monthly_export_helper(self)

    def _export_monthly_agent_buffer(self) -> None:
        export_monthly_agent_buffer_helper(self)

    def _accumulate_monthly_catch(self, f_idx: int, y: int, x: int, catch_vec) -> None:
        if self.monthly_catch_by_flotilla is not None:
            self.monthly_catch_by_flotilla[f_idx, y, x, :] += catch_vec

    def _export_monthly_fishing_mortality(self) -> None:
        export_monthly_fishing_mortality_helper(self)

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
    # Stock queries
    # ------------------------------------------------------------------

    def get_total_stock(self) -> float:
        return self._region_stock_cache["TOTAL"]

    # ------------------------------------------------------------------
    # Main step
    # ------------------------------------------------------------------

    def step(self) -> None:
        self.currents_map = read_currents_map(self.current_date.strftime("%Y-%m-%d"))
        self.determine_weather()

        is_new_year = (
            self.current_step % self.YEAR == 0 and self.current_step > 0
        )
        yearly_summary = None
        yearly_catch = 0.0

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
                    print(f"Average capital: {avg_capital:.0f} €")
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
                                f" avg capital = {avg_cap:.0f} €"
                            )
                print(f"{'=' * 60}\n")

            yearly_summary = self.collect_yearly_data()
            # Include retired agents so yearly catch accounts for fleet reductions
            current_catches = {
                a.unique_id: a.total_catch for a in self.agents
            }
            # Add retired (frozen) catches to keep total monotone
            for a in getattr(self, "_retired_agents", []):
                current_catches[a.unique_id] = a.total_catch
            yearly_catch = sum(
                current_catches[aid]
                - self.last_year_catches.get(aid, 0)
                for aid in current_catches
            )
            self.last_year_catches = current_catches

        self.agents.shuffle_do("reset_daily_flags")

        self.num_fishing_midday = 0
        self.num_at_home_midday = 0
        self.num_fished_today = 0

        shuffled = list(self.agents)
        self.random.shuffle(shuffled)
        for agent in shuffled:
            agent.step()
            if agent.gone_fishing:
                self.num_fishing_midday += 1
            if agent.at_home:
                self.num_at_home_midday += 1
            if agent.fished_today:
                self.num_fished_today += 1

        self._build_daily_agent_metrics_cache()
        self.datacollector.collect(self)

        self._append_daily_agent_rows_for_monthly_export()

        self.agents.shuffle_do("finalize_day")

        if is_new_year and yearly_summary is not None and self.verbose:
            year = self.current_step // self.YEAR
            print(f"\n{'=' * 60}")
            print(f"YEAR {year} COMPLETED")
            print(f"{'=' * 60}")
            print(f"Total stock: {self.get_total_stock():,.0f}")
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

        self.current_step += 1
        self.current_date += timedelta(days=1)

        if self.current_step >= self.end_of_sim:
            self.running = False
            if self.verbose:
                self.print_final_summary()

        if self.current_step % self.MONTH == 0:
            self.HOTSPOTS = get_hotspots_for_step(
                self.current_step,
            )

            desired = None
            if self.coupling:
                species_maps, _, desired = self._wait_for_coupling_update(
                    json_path="configs_json/config.json",
                    poll_interval=0.5,
                )
                new_species_biomass = self._update_biomass_species(species_maps)
                self.update_patches_species(new_species_biomass, self.species_names)
                if desired is not None:
                    self._apply_fleet_resize(desired)
                self._export_monthly_agent_buffer()
                self._export_monthly_fishing_mortality()
            else:
                # Non-coupling mode: still allow dynamic fleet via config polling (for tests)
                desired = self._read_desired_counts(json_path="configs_json/config.json")
                if desired is not None:
                    self._apply_fleet_resize(desired)
                # Keep monthly exports consistent even without coupling
                if self.current_step > 0:
                    self._export_monthly_agent_buffer()
                    self._export_monthly_fishing_mortality()

    # ------------------------------------------------------------------
    # Run helpers
    # ------------------------------------------------------------------

    def run_model(self, steps: Optional[int] = None) -> None:
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
        agents_list = list(self.agents)
        num_agents = len(agents_list)
        retired_agents = getattr(self, "_retired_agents", [])

        return {
            "current_step": self.current_step,
            "current_year": self.current_step // self.YEAR,
            "current_day": self.current_step % self.YEAR,
            "num_agents": num_agents,
            "num_retired": len(retired_agents),
            "num_archipelago": sum(1 for a in agents_list if a.fisher_type == "archipelago"),
            "num_coastal": sum(1 for a in agents_list if a.fisher_type == "coastal"),
            "num_trawler": sum(1 for a in agents_list if a.fisher_type == "trawler"),
            "num_fishing": self.num_fishing_midday,
            "num_at_home": self.num_at_home_midday,
            "num_fished_today": self.num_fished_today,
            "total_stock": self.get_total_stock(),
            "total_catch": sum(a.total_catch for a in agents_list),
            "total_catch_including_retired": sum(a.total_catch for a in agents_list) + sum(a.total_catch for a in retired_agents),
            "avg_capital": (
                sum(a.capital for a in agents_list) / num_agents
                if num_agents > 0
                else 0
            ),
            "bad_weather": self.bad_weather,
        }

    def print_final_summary(self) -> None:
        print_final_summary_helper(self)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def get_output_map(self) -> np.ndarray:
        stock_map = np.zeros(
            (self.grid.height, self.grid.width), dtype=int
        )
        for (x_coord, y_coord), patch in self.patches.items():
            stock_map[y_coord, x_coord] = int(patch["fish_stock"])
        return stock_map

    def save_output_map(self, directory: str, filename: str) -> None:
        stock_map = self.get_output_map()
        os.makedirs(directory, exist_ok=True)
        np.savetxt(
            os.path.join(directory, filename),
            stock_map, fmt="%d", delimiter=",",
        )

    def export_data(
        self,
        filename_prefix: str = "fibe_output",
        directory: str = "./results/",
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = os.path.join(directory, timestamp)
        os.makedirs(export_dir, exist_ok=True)

        model_df = self.datacollector.get_model_vars_dataframe()
        model_path = os.path.join(
            export_dir, f"{filename_prefix}_model_{timestamp}.csv"
        )
        model_df.to_csv(model_path, index=False)

        agent_df = self.datacollector.get_agent_vars_dataframe()
        agent_path = os.path.join(
            export_dir, f"{filename_prefix}_agent_{timestamp}.csv"
        )
        agent_df.to_csv(agent_path, index=False)

        if self.yearly_data:
            yearly_df = pd.DataFrame(self.yearly_data)
            yearly_path = os.path.join(
                export_dir, f"{filename_prefix}_yearly_{timestamp}.csv"
            )
            yearly_df.to_csv(yearly_path, index=False)
            self.save_output_map(
                export_dir, f"{filename_prefix}_stock_{timestamp}.csv"
            )

        if self.verbose:
            print(f"\nAll data exported with timestamp: {timestamp}")

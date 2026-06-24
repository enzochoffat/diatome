"""FIBE fishery model: main Mesa model class.

Defines ``FisheryModel``, which orchestrates spatial patch initialisation,
agent creation, daily stepping, data collection, and optional Ecospace
coupling.
"""

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

from src import config
from src import ecospace_outputs
from src.Couplage.couplage import Coupling
from src.agent import FisherAgent
from src.config import get_hotspots_for_step


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
        config_loader: Optional[ConfigLoader] = None,
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
        self.config_loader = config_loader

        self.num_archipelago = num_archipelago
        self.num_coastal = num_coastal
        self.num_trawler = num_trawler

        self.archipelago_names = archipelago_names
        self.coastal_names = coastal_names
        self.trawler_names = trawler_names

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
            print("\n" + "=" * 60)
            print("HOTSPOT DISTRIBUTION")
            print("=" * 60)
            self.validate_hotspot_distribution()
            print("=" * 60 + "\n")

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

    # ------------------------------------------------------------------
    # Region-stock cache
    # ------------------------------------------------------------------

    def _initialize_region_stock_cache(self) -> None:
        """Rebuilds the regional stock cache from scratch.

        Iterates over all patches, summing fish stocks per region into
        ``_region_stock_cache``.
        """
        cache: Dict[str, float] = {
            "A": 0, "B": 0, "C": 0, "D": 0, "TOTAL": 0
        }
        for patch in self.patches.values():
            region = patch["region"]
            if region in ("A", "B", "C", "D"):
                fish_stock = patch["fish_stock"]
                cache[region] += fish_stock
                cache["TOTAL"] += fish_stock
        self._region_stock_cache = cache

    def _refresh_region_stocks_cache(self) -> None:
        """Alias for ``_initialize_region_stock_cache``."""
        self._initialize_region_stock_cache()

    def _set_patch_fish_stock(self, pos: Tuple[int, int], new_stock: float) -> float:
        """Sets the fish stock of one patch and updates the regional cache.

        Args:
            pos: ``(x, y)`` grid position.
            new_stock: Desired new stock level (floored at 0).

        Returns:
            The actual new stock stored in the patch.
        """
        patch = self.patches[pos]
        old_stock = patch["fish_stock"]
        new_stock = max(0.0, new_stock)
        delta = new_stock - old_stock

        patch["fish_stock"] = new_stock
        if delta:
            region = patch["region"]
            if region in ("A", "B", "C", "D"):
                self._region_stock_cache[region] += delta
                self._region_stock_cache["TOTAL"] += delta

        return patch["fish_stock"]

    def _adjust_patch_fish_stock(
        self, pos: Tuple[int, int], delta: float
    ) -> float:
        """Adds a delta to one patch's stock, updating the regional cache.

        Args:
            pos: ``(x, y)`` grid position.
            delta: Amount to add (negative values reduce the stock).

        Returns:
            The new stock level of the patch.
        """
        current_stock = self.patches[pos]["fish_stock"]
        return self._set_patch_fish_stock(pos, current_stock + delta)

    # ------------------------------------------------------------------
    # Daily metrics cache
    # ------------------------------------------------------------------

    def _build_daily_agent_metrics_cache(self) -> None:
        """Computes and caches per-step aggregate metrics across all agents.

        Populates ``_daily_agent_metrics`` with totals, averages, Gini
        coefficients, and per-region catch breakdowns.
        """
        agents = list(self.agents)

        capitals: List[float] = []
        wealths: List[float] = []
        catches: List[float] = []
        profits: List[float] = []
        revenues: List[float] = []
        costs: List[float] = []
        days_at_sea: List[int] = []
        growth_perceptions: List[float] = []
        memory_sizes: List[int] = []

        by_type_count: Dict[str, int] = {
            "archipelago": 0, "coastal": 0, "trawler": 0
        }
        by_region_catch: Dict[str, float] = {
            "A": 0, "B": 0, "C": 0, "D": 0
        }

        num_bankrupt = 0
        total_catch_daily = 0.0
        total_catch_cumulative = 0.0
        total_capital = 0.0
        total_profit = 0.0
        total_revenue = 0.0
        total_costs = 0.0
        total_trips = 0
        num_perceive_scarcity = 0
        success_rate_sum = 0.0
        success_rate_count = 0
        min_capital: Optional[float] = None
        max_capital: Optional[float] = None

        for agent in agents:
            ftype = agent.fisher_type
            if ftype in by_type_count:
                by_type_count[ftype] += 1

            if agent.bankrupt:
                num_bankrupt += 1

            total_catch_daily += agent.accumulated_catch
            total_catch_cumulative += agent.total_catch
            total_capital += agent.capital
            total_profit += agent.total_profit
            total_revenue += agent.total_revenue
            total_costs += agent.total_cost

            capitals.append(agent.capital)
            wealths.append(agent.wealth)
            catches.append(agent.total_catch)
            profits.append(agent.total_profit)
            revenues.append(agent.total_revenue)
            costs.append(agent.total_cost)
            days_at_sea.append(agent.days_at_sea)
            growth_perceptions.append(agent.growth_perception)
            memory_sizes.append(len(agent.memory))

            if getattr(agent, "perceive_scarcity", False):
                num_perceive_scarcity += 1

            trips = agent.profitable_trip + agent.unprofitable_trip
            total_trips += trips
            if trips > 0:
                success_rate_sum += agent.profitable_trip / trips
                success_rate_count += 1

            if agent.current_region in by_region_catch:
                by_region_catch[agent.current_region] += (
                    agent.accumulated_catch
                )

            if min_capital is None or agent.capital < min_capital:
                min_capital = agent.capital
            if max_capital is None or agent.capital > max_capital:
                max_capital = agent.capital

        self._daily_agent_metrics = {
            "num_agents": len(agents),
            "num_archipelago": by_type_count["archipelago"],
            "num_coastal": by_type_count["coastal"],
            "num_trawler": by_type_count["trawler"],
            "num_bankrupt": num_bankrupt,
            "total_catch_daily": total_catch_daily,
            "total_catch_cumulative": total_catch_cumulative,
            "total_capital": total_capital,
            "avg_capital": self._safe_mean(capitals),
            "median_capital": self._safe_median(capitals),
            "min_capital": min_capital if min_capital is not None else 0,
            "max_capital": max_capital if max_capital is not None else 0,
            "total_profit": total_profit,
            "avg_profit": self._safe_mean(profits),
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "gini_capital": self.calculate_gini(capitals) if capitals else 0,
            "gini_wealth": self.calculate_gini(wealths) if wealths else 0,
            "gini_catch": self.calculate_gini(catches) if catches else 0,
            "avg_days_at_sea": self._safe_mean(days_at_sea),
            "total_trips": total_trips,
            "avg_success_rate": (
                success_rate_sum / success_rate_count
                if success_rate_count
                else 0
            ),
            "avg_growth_perception": self._safe_mean(growth_perceptions),
            "num_perceive_scarcity": num_perceive_scarcity,
            "avg_memory_size": self._safe_mean(memory_sizes),
            "catch_region_A": by_region_catch["A"],
            "catch_region_B": by_region_catch["B"],
            "catch_region_C": by_region_catch["C"],
            "catch_region_D": by_region_catch["D"],
        }

    # ------------------------------------------------------------------
    # Monthly export
    # ------------------------------------------------------------------

    def _append_daily_agent_rows_for_monthly_export(self) -> None:
        """Appends one row per agent to the monthly export buffer.

        Stores the current-step snapshot in ``_monthly_agent_rows`` to
        avoid reconstructing history from the DataCollector later.
        """
        step_value = self.current_step
        for agent in self.agents:
            self._monthly_agent_rows.append({
                "step": step_value,
                "unique_id": agent.unique_id,
                "fisher_type": agent.fisher_type,
                "age": agent.age,
                "capital": agent.capital,
                "wealth": agent.wealth,
                "total_profit": agent.total_profit,
                "total_revenue": agent.total_revenue,
                "total_cost": agent.total_cost,
                "bankrupt": agent.bankrupt,
                "total_catch": agent.total_catch,
                "days_at_sea": agent.days_at_sea,
                "profitable_trips": agent.profitable_trip,
                "unprofitable_trips": agent.unprofitable_trip,
                "at_home": agent.at_home,
                "gone_fishing": agent.gone_fishing,
                "fished_today": agent.fished_today,
                "at_sea": agent.at_sea,
                "current_location": (
                    agent.current_location if agent.gone_fishing else (0, 0)
                ),
                "catch": (
                    agent.accumulated_catch if agent.gone_fishing else 0
                ),
                "will_fish": agent.will_fish,
                "region_preference": agent.region_preference,
                "current_region": agent.current_region,
                "growth_perception": agent.growth_perception,
                "lay_low": agent.lay_low,
                "memory_size": len(agent.memory),
                "good_spots_count": len(agent.good_spots_memory),
            })

    def _export_monthly_agent_buffer(self) -> None:
        """Flushes the monthly agent buffer to a CSV file and clears it.

        Writes to ``./results/biomass/agent_<step>.csv``. Does nothing
        if the buffer is empty.
        """
        if not self._monthly_agent_rows:
            return

        os.makedirs("./results/biomass", exist_ok=True)
        df = pd.DataFrame(self._monthly_agent_rows)
        output_path = os.path.join(
            "./results/biomass", f"agent_{self.current_step}.csv"
        )
        df.to_csv(output_path, index=False)

        if self.verbose:
            print(
                f"Exported: agent_{self.current_step}.csv"
                f" ({len(df)} rows)"
            )

        self._monthly_agent_rows.clear()

    # ------------------------------------------------------------------
    # Coupling
    # ------------------------------------------------------------------

    def _wait_for_coupling_update(
        self,
        json_path: str = "configs/config.json",
        poll_interval: float = 0.5,
    ) -> Tuple[Any, Any]:
        """Blocks until the coupling config file is updated.

        Polls ``json_path`` for modification-time changes and returns
        the updated biomass maps once a change is detected.

        Args:
            json_path: Path to the JSON config monitored for changes.
            poll_interval: Polling interval in seconds.

        Returns:
            A tuple ``(species_maps, current_step_val)`` from the
            updated Ecospace CSV.
        """
        species_maps, last_step = Coupling.read_csv_biomass(self)
        current_step_val = last_step

        last_modified_time = 0.0
        current_modified_time = 0.0

        if os.path.exists(json_path):
            last_modified_time = os.path.getmtime(json_path)
            current_modified_time = last_modified_time

        while (
            current_modified_time <= last_modified_time
            and self.current_step != 28
        ):
            sleep(poll_interval)
            if os.path.exists(json_path):
                current_modified_time = os.path.getmtime(json_path)
                if current_modified_time > last_modified_time:
                    species_maps, current_step_val = (
                        Coupling.read_csv_biomass(self)
                    )
                    if self.verbose:
                        print(
                            f"File {json_path} updated. Proceeding with"
                            f" biomass update for step {current_step_val}."
                        )
            elif self.verbose:
                print(
                    f"File {json_path} not found."
                    " Waiting for the file to be created..."
                )

        return species_maps, current_step_val

    # ------------------------------------------------------------------
    # DataCollector
    # ------------------------------------------------------------------

    def _build_datacollector(self) -> DataCollector:
        """Constructs and returns the Mesa DataCollector.

        Returns:
            A configured ``DataCollector`` instance covering model-level
            and agent-level reporters.
        """
        return DataCollector(
            model_reporters={
                # Fish stocks
                "stock_A": lambda m: m._region_stock_cache["A"],
                "stock_B": lambda m: m._region_stock_cache["B"],
                "stock_C": lambda m: m._region_stock_cache["C"],
                "stock_D": lambda m: m._region_stock_cache["D"],
                "total_stock": lambda m: m._region_stock_cache["TOTAL"],
                "stock_below_MSY_A": lambda m: (
                    1 if m._region_stock_cache["A"] < m.MSY_STOCK_A else 0
                ),
                "stock_below_MSY_B": lambda m: (
                    1 if m._region_stock_cache["B"] < m.MSY_STOCK_B else 0
                ),
                "stock_below_MSY_C": lambda m: (
                    1 if m._region_stock_cache["C"] < m.MSY_STOCK_C else 0
                ),
                "stock_below_MSY_D": lambda m: (
                    1 if m._region_stock_cache["D"] < m.MSY_STOCK_D else 0
                ),
                # Agent counts
                "num_agents": lambda m: m._daily_agent_metrics["num_agents"],
                "num_archipelago": lambda m: m._daily_agent_metrics[
                    "num_archipelago"
                ],
                "num_coastal": lambda m: m._daily_agent_metrics["num_coastal"],
                "num_trawler": lambda m: m._daily_agent_metrics["num_trawler"],
                "num_fishing": lambda m: m.num_fishing_midday,
                "num_at_home": lambda m: m.num_at_home_midday,
                "num_fished_today": lambda m: m.num_fished_today,
                "num_bankrupt": lambda m: m._daily_agent_metrics[
                    "num_bankrupt"
                ],
                # Catches
                "total_catch_daily": lambda m: m._daily_agent_metrics[
                    "total_catch_daily"
                ],
                "total_catch_cumulative": lambda m: m._daily_agent_metrics[
                    "total_catch_cumulative"
                ],
                "total_catch": lambda m: m.get_total_catch_all_agents(),
                "avg_catch_per_agent": lambda m: (
                    m._daily_agent_metrics["total_catch_cumulative"]
                    / m._daily_agent_metrics["num_agents"]
                    if m._daily_agent_metrics["num_agents"]
                    else 0
                ),
                "catch_region_A": lambda m: m._daily_agent_metrics[
                    "catch_region_A"
                ],
                "catch_region_B": lambda m: m._daily_agent_metrics[
                    "catch_region_B"
                ],
                "catch_region_C": lambda m: m._daily_agent_metrics[
                    "catch_region_C"
                ],
                "catch_region_D": lambda m: m._daily_agent_metrics[
                    "catch_region_D"
                ],
                # Economics
                "total_capital": lambda m: m._daily_agent_metrics[
                    "total_capital"
                ],
                "avg_capital": lambda m: m._daily_agent_metrics["avg_capital"],
                "median_capital": lambda m: m._daily_agent_metrics[
                    "median_capital"
                ],
                "min_capital": lambda m: m._daily_agent_metrics["min_capital"],
                "max_capital": lambda m: m._daily_agent_metrics["max_capital"],
                "total_profit": lambda m: m._daily_agent_metrics[
                    "total_profit"
                ],
                "avg_profit": lambda m: m._daily_agent_metrics["avg_profit"],
                "total_revenue": lambda m: m._daily_agent_metrics[
                    "total_revenue"
                ],
                "total_costs": lambda m: m._daily_agent_metrics["total_costs"],
                # Inequality
                "gini_capital": lambda m: m._daily_agent_metrics[
                    "gini_capital"
                ],
                "gini_wealth": lambda m: m._daily_agent_metrics["gini_wealth"],
                "gini_catch": lambda m: m._daily_agent_metrics["gini_catch"],
                # Activity
                "avg_days_at_sea": lambda m: m._daily_agent_metrics[
                    "avg_days_at_sea"
                ],
                "total_trips": lambda m: m._daily_agent_metrics["total_trips"],
                "avg_success_rate": lambda m: m._daily_agent_metrics[
                    "avg_success_rate"
                ],
                # Memory and perception
                "avg_growth_perception": lambda m: m._daily_agent_metrics[
                    "avg_growth_perception"
                ],
                "num_perceive_scarcity": lambda m: m._daily_agent_metrics[
                    "num_perceive_scarcity"
                ],
                "avg_memory_size": lambda m: m._daily_agent_metrics[
                    "avg_memory_size"
                ],
                # Weather and time
                "bad_weather": lambda m: 1 if m.bad_weather else 0,
                "current_step": lambda m: m.current_step,
                "current_year": lambda m: m.current_step // m.YEAR,
                "current_day_of_year": lambda m: m.current_step % m.YEAR,
            },
            agent_reporters={
                # Identity
                "step": lambda a: a.model.current_step,
                "unique_id": "unique_id",
                "fisher_type": "fisher_type",
                "age": "age",
                # Financial
                "capital": "capital",
                "wealth": "wealth",
                "total_profit": "total_profit",
                "total_revenue": "total_revenue",
                "total_cost": "total_cost",
                "bankrupt": "bankrupt",
                # Activity
                "total_catch": "total_catch",
                "days_at_sea": "days_at_sea",
                "profitable_trips": "profitable_trip",
                "unprofitable_trips": "unprofitable_trip",
                "at_home": "at_home",
                "gone_fishing": "gone_fishing",
                "fished_today": "fished_today",
                "at_sea": "at_sea",
                "current_location": lambda a: (
                    a.current_location if a.gone_fishing else (0, 0)
                ),
                "catch": lambda a: (
                    a.accumulated_catch if a.gone_fishing else 0
                ),
                # Decision-making
                "will_fish": "will_fish",
                "region_preference": "region_preference",
                "current_region": "current_region",
                "growth_perception": "growth_perception",
                "lay_low": "lay_low",
                # Memory
                "memory_size": lambda a: len(a.memory),
                "good_spots_count": lambda a: len(a.good_spots_memory),
            },
        )

    # ------------------------------------------------------------------
    # Agent creation
    # ------------------------------------------------------------------

    def _create_agents(self) -> None:
        """Creates and places all fisher agents on the grid.

        Instantiates archipelago, coastal, and trawler agents in order,
        assigning each a starting position within an appropriate region.
        """
        agent_id = 0

        ports_dict = self.config_loader.get_port_assignments() if self.config_loader else {}
        port_coords = config.get_port_coordinates()
        

        for i in range(self.num_archipelago):
            name = (
                self.archipelago_names[agent_id]
                if self.archipelago_names
                else None
            )
            port = ports_dict.get("archipelago_ports", [0])
            index = port[i]
            agent = FisherAgent(
                agent_id, self, "archipelago",
                initial_capital=self.initial_capital, name=name, port=port_coords[index]
            )
            start_pos = (0, 0)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = self.get_region(*start_pos)
            agent_id += 1

        for i in range(self.num_coastal):
            offset = agent_id - self.num_archipelago
            name = (
                self.coastal_names[offset] if self.coastal_names else None
            )
            port = ports_dict.get("coastal_ports", [0])
            index = port[i]
            agent = FisherAgent(
                agent_id, self, "coastal",
                initial_capital=self.initial_capital, name=name, port=port_coords[index]
            )
            region = self.random.choice(["A", "B"])
            start_pos = self._get_random_position_in_region(region)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = region
            agent_id += 1

        for i in range(self.num_trawler):
            offset = agent_id - self.num_archipelago - self.num_coastal
            name = (
                self.trawler_names[offset] if self.trawler_names else None
            )
            port = ports_dict.get("trawler_ports", [0])
            index = port[i]
            agent = FisherAgent(
                agent_id, self, "trawler",
                initial_capital=self.initial_capital, name=name, port=port_coords[index]
            )
            region = self.random.choice(config.TRAWLER_ACCESSIBLE_REGIONS)
            start_pos = self._get_random_position_in_region(region)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = region
            agent_id += 1

    def _get_random_position_in_region(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Returns a random patch position within a named region.

        Args:
            region: Region identifier (``"A"``, ``"B"``, ``"C"``,
                or ``"D"``).

        Returns:
            A random ``(x, y)`` tuple from that region, or None if the
            region contains no patches.
        """
        candidates = [
            pos
            for pos, patch in self.patches.items()
            if patch["region"] == region
        ]
        return random.choice(candidates) if candidates else None

    # ------------------------------------------------------------------
    # Patch initialisation
    # ------------------------------------------------------------------

    def init_patches(self) -> None:
        """Initialises all grid patches with region, density, and stock.

        Builds spatial indexes and density maps, then loads the initial
        fish stock from Ecospace data (or falls back to the carrying
        capacity-based formula for non-fishing cells).
        """
        self._prepare_spatial_indexes()
        self._build_density_offsets()
        self._build_density_map_exact()

        width = self.grid.width
        height = self.grid.height
        growth_rate = self.GROWTH_RATE

        ecospace_data, _ = ecospace_outputs.get_ecospace_data()
        sum_data = np.sum(ecospace_data, axis=2)
        print(
            f"shape sum_data: {sum_data.shape},"
            f" width: {width}, height: {height}"
        )

        patches: Dict[Tuple[int, int], Dict[str, Any]] = {}

        for x_coord in range(height):
            for y_coord in range(width):
                region = self.get_region(x_coord, y_coord)
                density = self.get_density(x_coord, y_coord, region)
                carrying_capacity = self.get_carrying_capacity(
                    region, density
                )
                fish_stock = (
                    sum_data[x_coord, y_coord]
                    if region not in ("LAND", "NULL")
                    else 0
                )
                patches[(x_coord, y_coord)] = {
                    "region": region,
                    "density": density,
                    "fish_stock": fish_stock,
                    "carrying_capacity": carrying_capacity,
                    "growth_rate": growth_rate,
                    "regen_amount": 0,
                    "patch_stock_after_regrowth": fish_stock,
                }

        self.patches = patches

    def _prepare_spatial_indexes(self) -> None:
        """Builds set-based spatial indexes for O(1) region lookups.

        Populates ``_land_set``, ``_region_*_set``, ``_hotspots_*_set``,
        and the aggregating dicts ``_region_sets``, ``_hotspots_lists``,
        and ``_hotspots_sets``.
        """
        self._land_set = {tuple(c) for c in self.LAND}
        self._region_a_set = {tuple(c) for c in self.REGION_A}
        self._region_b_set = {tuple(c) for c in self.REGION_B}
        self._region_c_set = {tuple(c) for c in self.REGION_C}
        self._region_d_set = {tuple(c) for c in self.REGION_D}

        self._hotspots_a_list = [tuple(c) for c in self.HOTSPOTS_A]
        self._hotspots_b_list = [tuple(c) for c in self.HOTSPOTS_B]
        self._hotspots_c_list = [tuple(c) for c in self.HOTSPOTS_C]
        self._hotspots_d_list = [tuple(c) for c in self.HOTSPOTS_D]

        self._hotspots_a_set = set(self._hotspots_a_list)
        self._hotspots_b_set = set(self._hotspots_b_list)
        self._hotspots_c_set = set(self._hotspots_c_list)
        self._hotspots_d_set = set(self._hotspots_d_list)

        self._region_sets: Dict[str, set] = {
            "A": self._region_a_set,
            "B": self._region_b_set,
            "C": self._region_c_set,
            "D": self._region_d_set,
        }
        self._hotspots_lists: Dict[str, List[Tuple[int, int]]] = {
            "A": self._hotspots_a_list,
            "B": self._hotspots_b_list,
            "C": self._hotspots_c_list,
            "D": self._hotspots_d_list,
        }
        self._hotspots_sets: Dict[str, set] = {
            "A": self._hotspots_a_set,
            "B": self._hotspots_b_set,
            "C": self._hotspots_c_set,
            "D": self._hotspots_d_set,
        }

    def _build_density_offsets(self) -> None:
        """Pre-computes (dx, dy) offset lists for HIGH and MEDIUM zones.

        HIGH zone: Euclidean distance ≤ 3 from a hotspot.
        MEDIUM zone: 3 < distance ≤ 5 from a hotspot.

        Stores results in ``_high_offsets`` and ``_medium_only_offsets``.
        """
        high_offsets = [
            (dx, dy)
            for dx in range(-3, 4)
            for dy in range(-3, 4)
            if dx * dx + dy * dy <= 9
        ]
        medium_only_offsets = [
            (dx, dy)
            for dx in range(-5, 6)
            for dy in range(-5, 6)
            if 9 < dx * dx + dy * dy <= 25
        ]
        self._high_offsets = high_offsets
        self._medium_only_offsets = medium_only_offsets

    def _build_density_map_exact(self) -> None:
        """Assigns HIGH / MEDIUM density labels to patches near hotspots.

        For each region, first marks MEDIUM cells (ring 3 < d ≤ 5) using
        ``setdefault`` so they are not overwritten by a later HIGH mark,
        then marks HIGH cells (d ≤ 3), overwriting MEDIUM where they
        overlap. Remaining region cells are implicitly LOW.
        """
        self._density_map_by_region: Dict[str, Dict[Tuple[int, int], str]] = {
            "A": {}, "B": {}, "C": {}, "D": {}
        }

        for region_label in ("A", "B", "C", "D"):
            region_coords = self._region_sets[region_label]
            hotspots = self._hotspots_lists[region_label]
            density_map = self._density_map_by_region[region_label]

            for hx, hy in hotspots:
                for dx, dy in self._medium_only_offsets:
                    coord = (hx + dx, hy + dy)
                    if coord in region_coords:
                        density_map.setdefault(coord, self.MEDIUM)

            for hx, hy in hotspots:
                for dx, dy in self._high_offsets:
                    coord = (hx + dx, hy + dy)
                    if coord in region_coords:
                        density_map[coord] = self.HIGH

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def get_region(self, x: int, y: int) -> str:
        """Returns the region label for a grid cell.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            One of ``"A"``, ``"B"``, ``"C"``, ``"D"``, ``"LAND"``,
            or ``"NULL"``.
        """
        coord = (x, y)
        if coord in self._land_set:
            return "LAND"
        if coord in self._region_a_set:
            return "A"
        if coord in self._region_b_set:
            return "B"
        if coord in self._region_c_set:
            return "C"
        if coord in self._region_d_set:
            return "D"
        return "NULL"

    def get_density(
        self, x: int, y: int, region: str
    ) -> Optional[str]:
        """Returns the density label for a grid cell.

        Args:
            x: Column index.
            y: Row index.
            region: Pre-computed region label for the cell.

        Returns:
            ``"high"``, ``"medium"``, or ``"low"``, or None for
            LAND / NULL cells.
        """
        if region in ("LAND", "NULL"):
            return None
        return self._density_map_by_region[region].get(
            (x, y), self.LOW
        )

    def get_carrying_capacity(
        self, region: str, density: Optional[str]
    ) -> int:
        """Returns a stochastic carrying capacity for a patch.

        Draws from a normal distribution centred on the base capacity
        for the given density level, with standard deviation
        ``config.SD_CARCAP * base_capacity``.

        Args:
            region: Region label; returns 0 for LAND / NULL.
            density: Density label (``"high"``, ``"medium"``,
                ``"low"``). Returns 0 if None or unrecognised.

        Returns:
            Rounded carrying capacity (≥ 1 for fishing cells, 0 for
            non-fishing cells).
        """
        if region in ("LAND", "NULL") or density is None:
            return 0

        density_upper = (
            density.upper() if isinstance(density, str) else str(density).upper()
        )

        base_capacity_map = {
            "HIGH": self.HIGH_CARRYING_CAPACITY,
            "MEDIUM": self.MEDIUM_CARRYING_CAPACITY,
            "LOW": self.LOW_CARRYING_CAPACITY,
        }

        if density_upper not in base_capacity_map:
            print(
                f"WARNING: Unknown density '{density}'"
                f" for region {region}"
            )
            return 0

        base_capacity = base_capacity_map[density_upper]
        sd = config.SD_CARCAP * base_capacity
        random_capacity = np.random.normal(base_capacity, sd)
        return max(1, round(random_capacity))

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
                print(f"Region {region_name}:")
                print(
                    f"  HIGH:   {high_count:3d} patches"
                    f" ({high_count / total * 100:5.1f}%)"
                )
                print(
                    f"  MEDIUM: {medium_count:3d} patches"
                    f" ({medium_count / total * 100:5.1f}%)"
                )
                print(
                    f"  LOW:    {low_count:3d} patches"
                    f" ({low_count / total * 100:5.1f}%)"
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

    def get_patch_info(
        self, x: int, y: int
    ) -> Optional[Dict[str, Any]]:
        """Returns the attribute dict for a patch, or None if absent.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            Patch dict or None.
        """
        return self.patches.get((x, y))

    def reduce_stock(
        self, x: int, y: int, catch_amount: float
    ) -> float:
        """Reduces fish stock at a location due to fishing.

        Args:
            x: Column index.
            y: Row index.
            catch_amount: Desired catch quantity.

        Returns:
            Actual catch (capped at the available stock).
        """
        pos = (x, y)
        if pos in self.patches:
            current_stock = self.patches[pos]["fish_stock"]
            actual_catch = min(catch_amount, current_stock)
            self._set_patch_fish_stock(pos, current_stock - actual_catch)
            return actual_catch
        return 0

    # ------------------------------------------------------------------
    # Fish-stock dynamics
    # ------------------------------------------------------------------

    def update_fish_stock(self, time_step_days: int = 1) -> None:
        """Applies logistic growth to all fishing patches.

        Converts the annual growth rate to a per-step effective rate,
        applies density-dependent multipliers, and scales growth down
        if the regional total would exceed the regional carrying
        capacity.

        Args:
            time_step_days: Length of the time step in days.
        """
        effective_rate = self.GROWTH_RATE * (time_step_days / self.YEAR)
        density_factor: Dict[str, float] = {
            self.HIGH: 2.0,
            self.MEDIUM: 1.25,
            self.LOW: 1.0,
        }
        growth_by_region: Dict[str, float] = {
            "A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0
        }

        for patch in self.patches.values():
            region = patch["region"]
            if region in ("LAND", "NULL"):
                continue
            current_stock = patch["fish_stock"]
            carrying_capacity = patch["carrying_capacity"]
            factor = density_factor.get(patch["density"], 1.0)
            regen_amount = (
                current_stock
                * effective_rate
                * factor
                * (1 - current_stock / carrying_capacity)
            )
            patch["regen_amount"] = regen_amount
            growth_by_region[region] += regen_amount

        for region in ("A", "B", "C", "D"):
            current_regional_stock = self.get_region_stock(region)
            regional_capacity = self.get_region_carrying_capacity(region)
            proposed_stock = current_regional_stock + growth_by_region[region]

            if proposed_stock > regional_capacity:
                raw_growth = growth_by_region[region]
                scale_factor = (
                    max(
                        0.0,
                        min(
                            1.0,
                            (regional_capacity - current_regional_stock)
                            / raw_growth,
                        ),
                    )
                    if raw_growth > 0
                    else 0.0
                )
                for pos, patch in self.patches.items():
                    if patch["region"] == region:
                        patch["regen_amount"] = round(
                            patch["regen_amount"] * scale_factor
                        )
                        self._set_patch_fish_stock(
                            pos,
                            patch["fish_stock"] + patch["regen_amount"],
                        )
                        patch["patch_stock_after_regrowth"] = (
                            patch["fish_stock"]
                        )
            else:
                for pos, patch in self.patches.items():
                    if patch["region"] == region:
                        self._set_patch_fish_stock(
                            pos,
                            patch["fish_stock"] + patch["regen_amount"],
                        )
                        patch["patch_stock_after_regrowth"] = (
                            patch["fish_stock"]
                        )

    def update_fish_stock_yearly(self) -> None:
        """Applies yearly logistic regeneration (NetLogo-aligned).

        Updates each non-LAND patch with a single annual growth step.
        """
        for pos, patch in self.patches.items():
            if patch["region"] in ("LAND", "NULL"):
                continue
            current_stock = patch["fish_stock"]
            carrying_capacity = patch["carrying_capacity"]
            regen_amount = round(
                current_stock
                * self.GROWTH_RATE
                * (1 - current_stock / carrying_capacity)
            )
            patch["regen_amount"] = regen_amount
            self._set_patch_fish_stock(pos, current_stock + regen_amount)
            patch["patch_stock_after_regrowth"] = patch["fish_stock"]

    def update_patches(
        self, new_fish_stocks: Dict[Tuple[int, int], float]
    ) -> None:
        """Replaces patch fish stocks with values from a coupling update.

        Args:
            new_fish_stocks: Mapping of ``(x, y)`` to new stock values.
        """
        sum_a = 0.0
        for (x_coord, y_coord), stock in new_fish_stocks.items():
            pos = (x_coord, y_coord)
            region = self.get_region(x_coord, y_coord)
            if region == "A":
                sum_a += stock
            if pos in self.patches:
                self._set_patch_fish_stock(pos, stock)
        print(f"Total stock for region A after update: {sum_a}")

    # ------------------------------------------------------------------
    # Regional capacity recalculation
    # ------------------------------------------------------------------

    def _recalculate_regional_capacities(self) -> None:
        """Recomputes regional carrying capacities from actual patch stocks.

        Updates ``CARRYING_CAPACITY_*`` and ``MSY_STOCK_*`` attributes
        based on the current sum of fish stocks per region.
        """
        for region in ("A", "B", "C", "D"):
            total_capacity = sum(
                patch["fish_stock"]
                for patch in self.patches.values()
                if patch["region"] == region
            )
            msy = round(total_capacity / 2)

            if region == "A":
                self.CARRYING_CAPACITY_A = total_capacity
                self.MSY_STOCK_A = msy
            elif region == "B":
                self.CARRYING_CAPACITY_B = total_capacity
                self.MSY_STOCK_B = msy
            elif region == "C":
                self.CARRYING_CAPACITY_C = total_capacity
                self.MSY_STOCK_C = msy
            elif region == "D":
                self.CARRYING_CAPACITY_D = total_capacity
                self.MSY_STOCK_D = msy

        if self.verbose:
            print("Capacités régionales recalculées:")
            print(
                f"  Region A: {self.CARRYING_CAPACITY_A}"
                f" (MSY: {self.MSY_STOCK_A})"
            )
            print(
                f"  Region B: {self.CARRYING_CAPACITY_B}"
                f" (MSY: {self.MSY_STOCK_B})"
            )
            print(
                f"  Region C: {self.CARRYING_CAPACITY_C}"
                f" (MSY: {self.MSY_STOCK_C})"
            )
            print(
                f"  Region D: {self.CARRYING_CAPACITY_D}"
                f" (MSY: {self.MSY_STOCK_D})"
            )

    def validate_regional_stocks(self) -> List[Dict[str, Any]]:
        """Checks that no region exceeds its carrying capacity.

        Returns:
            List of violation dicts (empty if all regions are within
            bounds). Each dict has keys ``region``, ``current``,
            ``max``, ``excess``, and ``percentage``.
        """
        violations: List[Dict[str, Any]] = []
        for region in ("A", "B", "C", "D"):
            current_stock = self.get_region_stock(region)
            max_capacity = self.get_region_carrying_capacity(region)
            if current_stock > max_capacity:
                violations.append({
                    "region": region,
                    "current": current_stock,
                    "max": max_capacity,
                    "excess": current_stock - max_capacity,
                    "percentage": (current_stock / max_capacity) * 100,
                })
        return violations

    # ------------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------------

    def determine_weather(self) -> bool:
        """Determines whether today is a bad-weather day (stochastic).

        Returns:
            True if bad weather, False otherwise.
        """
        self.bad_weather = random.random() < self.bad_weather_probability
        return self.bad_weather

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
                    json_path="configs/config.json",
                    poll_interval=0.5,
                )
                fish = Coupling.update_biomass(self, species_maps)
                print(
                    f"stock for region A before update:"
                    f" {self.get_region_stock('A')},"
                    f" B: {self.get_region_stock('B')},"
                    f" C: {self.get_region_stock('C')},"
                    f" D: {self.get_region_stock('D')}"
                )
                self.update_patches(fish)
                print(
                    f"stock for region A after update:"
                    f" {self.get_region_stock('A')},"
                    f" B: {self.get_region_stock('B')},"
                    f" C: {self.get_region_stock('C')},"
                    f" D: {self.get_region_stock('D')}"
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
            print(
                f"Starting simulation for {steps} days"
                f" ({steps / self.YEAR:.1f} years)"
            )
            print(
                f"Agents: {self.num_archipelago} archipelago,"
                f" {self.num_coastal} coastal,"
                f" {self.num_trawler} trawler"
            )
            print("=" * 60)

        for _ in range(steps):
            self.step()
            if not self.running:
                break

        if self.verbose:
            print("=" * 60)
            print(
                f"Simulation completed after {self.current_step} days"
                f" ({self.current_step / self.YEAR:.1f} years)"
            )

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def collect_yearly_data(self) -> Dict[str, Any]:
        """Collects a detailed yearly snapshot and appends it to ``yearly_data``.

        Returns:
            Dictionary containing year, step, regional stocks, agent
            counts, catch totals, economic totals, Gini coefficients,
            and activity metrics.
        """
        year = self.current_step // self.YEAR

        stock_a = self._region_stock_cache["A"]
        stock_b = self._region_stock_cache["B"]
        stock_c = self._region_stock_cache["C"]
        stock_d = self._region_stock_cache["D"]
        total_stock = self._region_stock_cache["TOTAL"]

        by_type_count: Dict[str, int] = {
            "archipelago": 0, "coastal": 0, "trawler": 0
        }
        by_type_total_catch: Dict[str, float] = {
            "archipelago": 0.0, "coastal": 0.0, "trawler": 0.0
        }
        by_type_capitals: Dict[str, List[float]] = {
            "archipelago": [], "coastal": [], "trawler": []
        }

        capitals: List[float] = []
        wealths: List[float] = []
        catches: List[float] = []
        days_at_sea_list: List[int] = []

        total_capital = 0.0
        total_profit = 0.0
        total_revenue = 0.0
        total_costs = 0.0
        total_trips = 0
        total_profitable_trips = 0
        total_unprofitable_trips = 0
        success_rate_sum = 0.0
        success_rate_count = 0
        num_bankrupt = 0
        num_agents = 0

        for agent in self.agents:
            num_agents += 1
            ftype = agent.fisher_type

            if ftype in by_type_count:
                by_type_count[ftype] += 1
                by_type_total_catch[ftype] += agent.total_catch
                by_type_capitals[ftype].append(agent.capital)

            capitals.append(agent.capital)
            wealths.append(agent.wealth)
            catches.append(agent.total_catch)
            days_at_sea_list.append(agent.days_at_sea)

            total_capital += agent.capital
            total_profit += agent.total_profit
            total_revenue += agent.total_revenue
            total_costs += agent.total_cost

            total_profitable_trips += agent.profitable_trip
            total_unprofitable_trips += agent.unprofitable_trip
            trips = agent.profitable_trip + agent.unprofitable_trip
            total_trips += trips
            if trips > 0:
                success_rate_sum += agent.profitable_trip / trips
                success_rate_count += 1

            if agent.bankrupt:
                num_bankrupt += 1

        yearly_summary: Dict[str, Any] = {
            "year": year,
            "step": self.current_step,
            "stock_A": stock_a,
            "stock_B": stock_b,
            "stock_C": stock_c,
            "stock_D": stock_d,
            "total_stock": total_stock,
            "stock_A_pct_K": (
                stock_a / self.CARRYING_CAPACITY_A
                if self.CARRYING_CAPACITY_A > 0
                else 0
            ),
            "stock_B_pct_K": (
                stock_b / self.CARRYING_CAPACITY_B
                if self.CARRYING_CAPACITY_B > 0
                else 0
            ),
            "stock_C_pct_K": (
                stock_c / self.CARRYING_CAPACITY_C
                if self.CARRYING_CAPACITY_C > 0
                else 0
            ),
            "stock_D_pct_K": (
                stock_d / self.CARRYING_CAPACITY_D
                if self.CARRYING_CAPACITY_D > 0
                else 0
            ),
            "num_agents": num_agents,
            "num_archipelago": by_type_count["archipelago"],
            "num_coastal": by_type_count["coastal"],
            "num_trawler": by_type_count["trawler"],
            "num_bankrupt": num_bankrupt,
            "total_catch_archipelago": by_type_total_catch["archipelago"],
            "total_catch_coastal": by_type_total_catch["coastal"],
            "total_catch_trawler": by_type_total_catch["trawler"],
            "total_catch_all": sum(catches),
            "avg_catch_archipelago": (
                by_type_total_catch["archipelago"]
                / by_type_count["archipelago"]
                if by_type_count["archipelago"]
                else 0
            ),
            "avg_catch_coastal": (
                by_type_total_catch["coastal"] / by_type_count["coastal"]
                if by_type_count["coastal"]
                else 0
            ),
            "avg_catch_trawler": (
                by_type_total_catch["trawler"] / by_type_count["trawler"]
                if by_type_count["trawler"]
                else 0
            ),
            "avg_capital_archipelago": self._safe_mean(
                by_type_capitals["archipelago"]
            ),
            "avg_capital_coastal": self._safe_mean(
                by_type_capitals["coastal"]
            ),
            "avg_capital_trawler": self._safe_mean(
                by_type_capitals["trawler"]
            ),
            "total_capital": total_capital,
            "total_profit": total_profit,
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "gini_capital": self.calculate_gini(capitals) if capitals else 0,
            "gini_wealth": self.calculate_gini(wealths) if wealths else 0,
            "gini_catch": self.calculate_gini(catches) if catches else 0,
            "total_trips": total_trips,
            "total_profitable_trips": total_profitable_trips,
            "total_unprofitable_trips": total_unprofitable_trips,
            "avg_success_rate": (
                success_rate_sum / success_rate_count
                if success_rate_count
                else 0
            ),
            "avg_days_at_sea": self._safe_mean(days_at_sea_list),
        }

        self.yearly_data.append(yearly_summary)
        return yearly_summary

    def get_total_catch_all_agents(self) -> float:
        """Returns total catch since the last annual snapshot.

        Returns:
            Sum of incremental catches relative to ``last_year_catches``,
            or the raw cumulative total if no snapshot exists yet.
        """
        if not getattr(self, "last_year_catches", None):
            return sum(a.total_catch for a in self.agents)

        current_catches = {
            a.unique_id: a.total_catch for a in self.agents
        }
        return sum(
            current_catches[aid] - self.last_year_catches.get(aid, 0)
            for aid in current_catches
        )

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

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_data(
        self,
        filename_prefix: str = "fibe_output",
        directory: str = "./results/",
    ) -> None:
        """Exports collected data to timestamped CSV files.

        Writes model-level, agent-level, and yearly summary data to a
        subdirectory of ``directory`` named after the current timestamp.

        Args:
            filename_prefix: Prefix for all output filenames.
            directory: Root output directory.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = os.path.join(directory, timestamp)
        os.makedirs(export_dir, exist_ok=True)

        model_df = self.datacollector.get_model_vars_dataframe()
        model_path = os.path.join(
            export_dir, f"{filename_prefix}_model_{timestamp}.csv"
        )
        model_df.to_csv(model_path, index=False)
        if self.verbose:
            print(
                f"Exported: {os.path.basename(model_path)}"
                f" ({len(model_df)} rows)"
            )

        agent_df = self.datacollector.get_agent_vars_dataframe()
        agent_path = os.path.join(
            export_dir, f"{filename_prefix}_agent_{timestamp}.csv"
        )
        agent_df.to_csv(agent_path, index=False)
        if self.verbose:
            print(
                f"Exported: {os.path.basename(agent_path)}"
                f" ({len(agent_df)} rows)"
            )

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
                print(
                    f"Exported: {os.path.basename(yearly_path)}"
                    f" ({len(yearly_df)} rows)"
                )

        if self.verbose:
            print(f"\nAll data exported with timestamp: {timestamp}")

    def get_output_map(self) -> np.ndarray:
        """Returns a 2-D array of current fish stocks for visualisation.

        Returns:
            Integer NumPy array of shape ``(height, width)``.
        """
        stock_map = np.zeros(
            (self.grid.height, self.grid.width), dtype=int
        )
        for (x_coord, y_coord), patch in self.patches.items():
            stock_map[x_coord, y_coord] = int(patch["fish_stock"])
        return stock_map

    def save_output_map(self, directory: str, filename: str) -> None:
        """Saves the current fish-stock map to a CSV file.

        Args:
            directory: Target directory (created if it does not exist).
            filename: Output filename.
        """
        stock_map = self.get_output_map()
        os.makedirs(directory, exist_ok=True)
        np.savetxt(
            os.path.join(directory, filename),
            stock_map, fmt="%d", delimiter=",",
        )

    # ------------------------------------------------------------------
    # Summary print
    # ------------------------------------------------------------------

    def print_final_summary(self) -> None:
        """Prints a comprehensive summary at the end of the simulation."""
        print("\n" + "=" * 80)
        print("SIMULATION FINALE SUMMARY")
        print("=" * 80)

        stock_a = self._region_stock_cache.get("A", 0)
        stock_b = self._region_stock_cache.get("B", 0)
        stock_c = self._region_stock_cache.get("C", 0)
        stock_d = self._region_stock_cache.get("D", 0)
        total_stock = self._region_stock_cache.get("TOTAL", 0)
        agents_list = list(self.agents)

        print(
            f"\nDuration: {self.current_step} days"
            f" ({self.current_step / self.YEAR:.1f} years)"
        )
        print(f"Agents: {len(agents_list)} total")

        print("\n--- FISH STOCKS ---")
        for label, stock, capacity in (
            ("A", stock_a, self.CARRYING_CAPACITY_A),
            ("B", stock_b, self.CARRYING_CAPACITY_B),
            ("C", stock_c, self.CARRYING_CAPACITY_C),
            ("D", stock_d, self.CARRYING_CAPACITY_D),
        ):
            pct = stock / capacity if capacity > 0 else 0
            print(
                f"Region {label}: {stock:>10,.0f} / {capacity:,.0f}"
                f" ({pct:.1%})"
            )
        print(f"TOTAL:    {total_stock:>10,.0f}")

        print("\n--- ECONOMICS ---")
        total_catch = sum(a.total_catch for a in agents_list)
        total_capital = sum(a.capital for a in agents_list)
        total_profit = sum(a.total_profit for a in agents_list)
        print(f"Total catch:   {total_catch:>12,.0f}")
        print(f"Total capital: {total_capital:>12,.2f}")
        print(f"Total profit:  {total_profit:>12,.2f}")
        avg_cap = total_capital / len(agents_list) if agents_list else 0
        print(f"Avg capital:   {avg_cap:>12,.2f}")

        print("\n--- INEQUALITY ---")
        print(
            f"Gini capital: "
            f"{self.calculate_gini([a.capital for a in agents_list]) if agents_list else 0:.3f}"
        )
        print(
            f"Gini wealth:  "
            f"{self.calculate_gini([a.wealth for a in agents_list]) if agents_list else 0:.3f}"
        )
        print(
            f"Gini catch:   "
            f"{self.calculate_gini([a.total_catch for a in agents_list]) if agents_list else 0:.3f}"
        )

        print("\n--- BY FISHER TYPE ---")
        by_type: Dict[str, List[Any]] = {
            "archipelago": [], "coastal": [], "trawler": []
        }
        for agent in agents_list:
            if agent.fisher_type in by_type:
                by_type[agent.fisher_type].append(agent)

        for ftype in ("archipelago", "coastal", "trawler"):
            type_agents = by_type[ftype]
            if type_agents:
                avg_catch = (
                    sum(a.total_catch for a in type_agents)
                    / len(type_agents)
                )
                avg_capital = (
                    sum(a.capital for a in type_agents) / len(type_agents)
                )
                bankrupt = sum(1 for a in type_agents if a.bankrupt)
                print(
                    f"{ftype:>12}: {len(type_agents):>3} agents,"
                    f" avg catch={avg_catch:>8,.0f},"
                    f" avg capital={avg_capital:>8,.2f},"
                    f" bankrupt={bankrupt}"
                )

        print("=" * 80 + "\n")

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    def _safe_mean(self, values: List[float]) -> float:
        """Returns the arithmetic mean of a list, or 0 if empty.

        Args:
            values: Numeric list to average.

        Returns:
            Mean value, or 0.0 for an empty list.
        """
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _safe_median(self, values: List[float]) -> float:
        """Returns the median of a list, or 0 if empty.

        Args:
            values: Numeric list.

        Returns:
            Median value, or 0.0 for an empty list.
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        mid = len(sorted_values) // 2
        if len(sorted_values) % 2 == 0:
            return (sorted_values[mid - 1] + sorted_values[mid]) / 2
        return sorted_values[mid]

    def calculate_gini(self, values: List[float]) -> float:
        """Calculates the Gini coefficient for a distribution.

        Args:
            values: Non-negative numeric list (capital, wealth, catch,
                etc.). Negative values are clamped to 0.

        Returns:
            Gini coefficient in [0, 1] where 0 is perfect equality and
            1 is perfect inequality. Returns 0 for empty or all-zero
            lists.
        """
        if not values:
            return 0.0

        clamped = [max(0.0, v) for v in values]
        total = sum(clamped)
        if total == 0:
            return 0.0

        sorted_values = sorted(clamped)
        num = len(sorted_values)
        cumsum = sum((i + 1) * v for i, v in enumerate(sorted_values))
        return (2 * cumsum) / (num * total) - (num + 1) / num
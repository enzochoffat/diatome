"""Fisher agent implementation for the FIBE fishery simulation.

This module defines the FisherAgent class, which encapsulates
decision-making, memory management, economic state, and spatial behavior
for individual fishers.

Supported fisher types:
    * archipelago
    * coastal
    * trawler
"""

from collections import Counter
import logging
import random
from typing import Any, Dict, List, Optional, Tuple
import statistics

import numpy as np

from mesa import Agent

from src import config
from src.domain.agents import finance
from src.domain.agents import fishing
from src.domain.agents import memory
from src.domain.agents import movement
from src.domain.environment import restricted_areas
from src.domain.agents.behavior.archipelagos import Archipelagos
from src.domain.agents.behavior.coastal import Coastal
from src.domain.agents.behavior.trawler import Trawler

logger = logging.getLogger(__name__)


class FisherAgent(Agent):
    """Represent a fisher agent in the FIBE fishery model.

    A fisher can belong to one of three fishing strategies:
    archipelago, coastal, or trawler. Each strategy has its own
    costs, catchability values, accessible regions, and behavioral model.

    Attributes:
        fisher_type: Fishing strategy.
        unique_id: Unique identifier within the model.
        name: Optional display name.
        port: Home port coordinates.
        capital: Current financial capital in SEK.
        wealth: Reported wealth value.
        bankrupt: Whether the fisher is bankrupt.
        memory: Recent trip history.
        good_spots_memory: Learned fishing locations.
    """

    def __init__(
        self,
        unique_id: int,
        model: Any,
        fisher_type: str,
        initial_capital: float | None = None,
        name: str | None = None,
        port: tuple[int, int] | None = None,
        habitat: list[str] | None = None,
        restricted_status: str | None = None,
        distance_map: Optional[Dict[str, Any]] = None,
        effort_quotas: int | None = None,
        landing_quotas: int | np.ndarray | None = None
    ) -> None:
        """Initialize a fisher agent.

        Args:
            unique_id: Unique agent identifier.
            model: Parent FisheryModel instance.
            fisher_type: Fishing strategy.
            initial_capital: Initial capital in SEK. Uses
                config.INITIAL_CAPITAL when None.
            name: Optional display name.
            port: Home port coordinates.
            habitat: Optional restricted habitat mask.
            distance_map: Optional distance map.
        """
        super().__init__(model)

        self.fisher_type = fisher_type
        self.unique_id = unique_id
        self.name = name
        self.port = port
        self.restricted_mask = habitat
        self.restricted_status = restricted_status
        self.distance_map = distance_map
        self.effort_quotas = effort_quotas
        self.landings_quotas = landing_quotas
        self.yearly_catch_by_species: Dict[str, float] = {name: 0.0 for name in self.model.species_names}

        # Financial state.
        self.capital: float = (
            float(initial_capital)
            if initial_capital is not None
            else config.INITIAL_CAPITAL
        )
        self.wealth: float = 0.0
        self.age: int = random.randint(
            config.MIN_AGE,
            config.MAX_AGE,
        )

        # Cumulative statistics.
        self.days_at_sea = 0
        self.total_catch = 0.0
        self.total_profit = 0.0
        self.total_cost = 0.0
        self.total_revenue = 0.0
        self.yearly_catch = 0.0
        self.yearly_profit = 0.0
        self.yearly_effort = 0

        # Economic status.
        self.bankrupt = False
        self.years_active = 0
        self.profitable_trip = 0
        self.unprofitable_trip = 0

        # Trip tracking.
        self.accumulated_catch = 0.0
        self.trip_cost = 0.0
        self.days_in_current_trip = 0
        self.days_at_sea_current_trip = 0

        # Spatial state.
        self.current_location: tuple[int, int] | None = None
        self.target_location: tuple[int, int] | None = None
        self.display_location: tuple[int, int] | None = None

        # Activity flags.
        self.at_home = True
        self.at_sea = False
        self.gone_fishing = False
        self.fished_today = False
        self.lay_low = False
        self.lay_low_counter = 0

        # Decision-making.
        self.will_fish = False
        self.spot_selection_strategy = "knowledge"
        self.growth_perception = 0.0

        # Type-specific attributes.
        self._set_type_attributes()

        # Temporal memory.
        self.memory_size = config.DEFAULT_MEMORY_SIZE
        self.memory: list[dict[str, Any]] = []
        self.catch_by_species = {name: 0.0 for name in self.model.species_names}

        # Spatial memory.
        self.good_spots_memory: dict[
            tuple[int, int],
            dict[str, Any],
        ] = {}
        self.good_spots_threshold = (
            config.GOOD_SPOT_EFFICIENCY_THRESHOLD
        )

        # Decision thresholds.
        self.satisfaction_home_threshold = (
            config.SATISFACTION_HOME_THRESHOLD
        )
        self.satisfaction_growth_threshold = (
            config.SATISFACTION_GROWTH_THRESHOLD
        )
        self.scarce_perception_threshold = (
            config.SCARCE_PERCEPTION_THRESHOLD
        )

        # Trawler-specific.
        self.fish_onboard = 0.0
        self.accumulated_value = 0.0
        self.storing_capacity = (
            config.TRAWLER_STORAGE_CAPACITY
            if fisher_type == "trawler"
            else self.catchability
        )
        self.jumped = False

    def _set_type_attributes(self) -> None:
        """Set type-specific economic and behavioral attributes."""
        f_idx = self.model.flotilla_indices[self.fisher_type]
        self.catchability_vector = self.model.catchability_matrix[f_idx].copy()
        self.catchability = float(np.sum(self.catchability_vector))
        self.expected_revenue = float(
            np.sum(self.catchability_vector * self.model.price_matrix[f_idx])
        )

        if self.fisher_type == "archipelago":
            self.cost_existence = self.model.LOW_COST_EXISTENCE
            self.cost_activity = self.model.LOW_COST_ACTIVITY
            self.lifestyle_preference = "high"
            self.max_good_spots = 10
            self.good_spots_threshold = 0.05
            self.has_partner = True
            self.has_colleagues = False
            self.has_technologie = False

        elif self.fisher_type == "coastal":
            self.cost_existence = self.model.MEDIUM_COST_EXISTENCE
            self.cost_activity = self.model.MEDIUM_COST_ACTIVITY
            self.lifestyle_preference = "medium"
            self.max_good_spots = 3
            self.wanna_be_home = False
            self.has_partner = True
            self.has_colleagues = True
            self.has_technologie = False
            self.satisfaction_home = (
                1.0 - random.randint(0, 50) / 100
            )
            self.satisfaction_growth = (
                1.0 - random.randint(0, 50) / 100
            )

        elif self.fisher_type == "trawler":
            self.cost_existence = self.model.HIGH_COST_EXISTENCE
            self.cost_activity = self.model.HIGH_COST_ACTIVITY
            self.lifestyle_preference = "low"
            self.max_good_spots = 2
            self.has_partner = False
            self.has_colleagues = True
            self.has_technologie = True

    def estimate_trip_cost(
        self,
        location: tuple[int, int] | None,
    ) -> float:
        """Estimate the total cost of a trip.

        Args:
            location: Destination coordinates. If None, only fixed
                costs are considered.

        Returns:
            Estimated trip cost in SEK.
        """
        if location is None:
            return self.cost_activity + self.cost_existence

        travel_cost = (
            movement.calculate_travel_cost(
                self,
                self.current_location,
                location,
            )
            if self.current_location
            else self.cost_activity
        )

        return (
            self.cost_activity
            + self.cost_existence
            + travel_cost
        )

    def can_afford_trip(self, cost: float) -> bool:
        """Return whether the agent can afford a fishing trip.

        Trawlers are never blocked by an affordability constraint.
        Other fisher types must maintain a safety buffer.

        Args:
            cost: Estimated trip cost in SEK.

        Returns:
            True if the trip is affordable, otherwise False.
        """
        if self.fisher_type == "trawler":
            return True

        safety_buffer = config.get_safety_buffer(
            self.cost_existence,
        )
        return self.capital + safety_buffer >= cost

    def stay_home(
        self,
        pay_existence_cost: bool = False,
    ) -> None:
        """Keep the agent at home.

        Args:
            pay_existence_cost: Whether to deduct existence costs and
                record the day in memory.
        """
        existence_cost = (
            self.cost_existence
            if pay_existence_cost
            else 0.0
        )

        if pay_existence_cost:
            finance.update_finances(
                self,
                profit=-existence_cost,
                cost=existence_cost,
                revenue=0.0,
                is_trip=False,
            )

        self.at_home = True
        self.gone_fishing = False
        self.at_sea = False
        self.will_fish = False

        self.update_memory(
            {
                "location": None,
                "catch": 0,
                "cost": existence_cost,
                "profit": (
                    -existence_cost
                    if pay_existence_cost
                    else 0
                ),
                "days": 1,
                "tick": self.model.current_step,
                "went_fishing": False,
            }
        )

    def stay_home_state_only(self) -> None:
        """Update the agent state to remain at home.

        This method only updates state flags and does not perform any
        financial transaction.
        """
        self.at_home = True
        self.gone_fishing = False
        self.at_sea = False
        self.will_fish = False


    def return_home(self) -> None:
        """Return the agent to its home port after a fishing trip.

        The method pays return travel costs, moves the agent back to its
        home port, lands fish for trawlers, and resets trip-related state.
        """
        return_cost = movement.calculate_travel_cost(
            self,
            self.current_location,
            self.port,
        )

        finance.update_finances(
            self,
            profit=0.0,
            cost=return_cost,
            revenue=0.0,
            is_trip=False,
        )

        if self.port is not None:
            movement.move_to(
                self,
                self.port[0],
                self.port[1],
            )

        if self.fisher_type == "trawler":
            fishing.land_fish(self)

        self.at_sea = False
        self.gone_fishing = False
        self.at_home = True
        self.current_location = None

        if getattr(self, "pos", None) is not None:
            self.model.grid.remove_agent(self)

        self.accumulated_catch = 0.0
        self.trip_cost = 0.0
        self.days_in_current_trip = 0


    def reset_daily_flags(self) -> None:
        """Reset daily state flags."""
        self.fished_today = False


    def finalize_day(self) -> None:
        """Finalize end-of-day agent state.

        Archipelago and coastal fishers perform daily trips and return home
        after fishing.
        """
        if (
            self.fisher_type in {"archipelago", "coastal"}
            and self.fished_today
        ):
            self.return_home()


    def reset_yearly_counters(self) -> None:
        """Reset yearly performance counters."""
        self.yearly_catch = 0.0
        self.yearly_profit = 0.0
        self.yearly_effort = 0
        self.yearly_catch_by_species = {name: 0.0 for name in self.model.species_names}


    def make_decision(self) -> None:
        """Determine whether and where the agent will fish.

        The decision logic depends on the fisher type:

        * Archipelago: lifestyle satisficing.
        * Coastal: lifestyle and growth optimization.
        * Trawler: growth optimization.
        """
        logger.debug(
            "Decision start",
            extra={
                "agent_id": self.unique_id,
                "type": self.fisher_type,
                "capital": self.capital,
            },
        )
        if self.check_effort_quota():
            return "Too much days at sea this year"

        if self.check_landing_quota():
            return "Too much catch this year"

        if self.fisher_type == "archipelago":
            Archipelagos.satisfice_lifestyle(self)
        elif self.fisher_type == "coastal":
            Coastal.optimise_lifestyle_and_growth(self)
        elif self.fisher_type == "trawler":
            Trawler.optimise_growth(self)
        else:
            self.will_fish = False

        logger.debug(
            "Decision result",
            extra={
                "agent_id": self.unique_id,
                "will_fish": self.will_fish,
            },
        )


    def execute_decision(self) -> None:
        """Execute the fishing decision for the current simulation step.

        The method handles:

        * bankruptcy behavior,
        * lay-low periods,
        * trip affordability,
        * fishing activity,
        * memory updates.
        """
        if self.bankrupt:
            self.lay_low = False
            self.will_fish = True

        if self.lay_low:
            logger.info(
                "Agent laying low",
                extra={
                    "agent_id": self.unique_id,
                    "capital": self.capital,
                },
            )

            existence_cost = (
                0.5 * self.cost_existence
                if getattr(self, "has_partner", False)
                else 0.25 * self.cost_existence
            )

            finance.update_finances(
                self,
                profit=-existence_cost,
                cost=existence_cost,
                revenue=0.0,
                is_trip=False,
            )

            self.stay_home_state_only()
            return

        if not self.will_fish:
            logger.debug(
                "Agent stays home",
                extra={"agent_id": self.unique_id},
            )
            self.stay_home(pay_existence_cost=True)
            return

        target_spot = self.decide_fishSpot()

        if target_spot is None:
            logger.debug(
                "No fishing spot found",
                extra={"agent_id": self.unique_id},
            )
            self.stay_home(pay_existence_cost=True)
            return

        estimated_cost = self.estimate_trip_cost(target_spot)

        if not self.bankrupt and not self.can_afford_trip(estimated_cost):
            logger.debug(
                "Agent cannot afford trip",
                extra={
                    "agent_id": self.unique_id,
                    "capital": self.capital,
                    "estimated_cost": estimated_cost,
                },
            )
            self.stay_home(pay_existence_cost=True)
            return

        logger.info(
            "Agent going fishing",
            extra={
                "agent_id": self.unique_id,
                "target_spot": target_spot,
            },
        )

        self.at_home = False
        self.gone_fishing = True 
        self.yearly_effort += 1

        movement.move_to(
            self,
            target_spot[0],
            target_spot[1],
        )

        trip_result = fishing.go_fish(
            self,
            target_spot,
        )

        logger.debug(
            "Fishing result",
            extra={
                "agent_id": self.unique_id,
                "catch": trip_result["catch"],
                "profit": trip_result["profit"],
            },
        )

        self.fished_today = True

        self.update_memory(
            {
                "location": target_spot,
                "catch": trip_result["catch"],
                "revenue": trip_result["revenue"],
                "cost": trip_result["costs"],
                "profit": trip_result["profit"],
                "days": 1,
                "tick": self.model.current_step,
                "went_fishing": True,
            }
        )


    def select_fishing_spot(self) -> Optional[Tuple[int, int]]:
        good_spots = memory.get_good_spots(self, min_visits=1)
        if good_spots:
            spot, _ = random.choice(good_spots)
            return spot
        return self.explore_random_spot()


    def explore_random_spot(self) -> Optional[Tuple[int, int]]:
        from src import config as cfg

        water_cells = cfg.WATER_CELLS
        if water_cells:
            for _ in range(50):
                cell = random.choice(water_cells)
                if (
                    not movement.is_restricted(self, cell[0], cell[1])
                    and not restricted_areas.is_restricted_area(
                        cell[0], cell[1], self.model.current_date
                    )
                ):
                    return (cell[0], cell[1])

        hotspots = self.model.HOTSPOTS
        if hotspots:
            for _ in range(10):
                base_spot = random.choice(hotspots)
                dx = random.randint(-5, 5)
                dy = random.randint(-5, 5)
                candidate = (base_spot[0] + dx, base_spot[1] + dy)
                if (
                    not movement.is_restricted(self, candidate[0], candidate[1])
                    and not restricted_areas.is_restricted_area(
                        candidate[0], candidate[1], self.model.current_date
                    )
                ):
                    return candidate

        return None

    def decide_fishSpot(self) -> Optional[Tuple[int, int]]:
        stay_put = False
        fishing_spot = None

        if self.fisher_type == "trawler" and self.gone_fishing:
            if self.has_technologie and self.current_location:
                uphill_spot = self.get_fishSpot_uphill_climbing()
                if uphill_spot:
                    self.current_location = uphill_spot

            patch_here = (
                self.model.get_patch_info(*self.current_location)
                if self.current_location
                else None
            )
            value_here = (
                self.model.get_cell_value(
                    self.current_location[0], self.current_location[1], self.fisher_type
                )
                if self.current_location
                else 0.0
            )
            fish_wish = self.storing_capacity - self.fish_onboard
            if value_here < self.expected_revenue * (fish_wish / max(self.storing_capacity, 1)):
                stay_put = True

        if not stay_put:
            self.jumped = True
            social_strategy = getattr(
                self.model, "social_influence", "expertise"
            )
            follow_social = (
                social_strategy != "none"
                and self.has_colleagues
                and random.randint(0, 10) < 8
            )

            if follow_social:
                if social_strategy == "descriptiveNorm":
                    fishing_spot = self.get_fishSpot_descriptive_norm()
                else:
                    fishing_spot = self.get_fishSpot_expertise()
                if fishing_spot is None:
                    fishing_spot = self.get_fishSpot_knowledge()
            else:
                fishing_spot = self.get_fishSpot_knowledge()

            if fishing_spot is None:
                return self.explore_random_spot()

            if self.fisher_type == "trawler" and self.has_technologie:
                uphill_spot = self.get_fishSpot_uphill_climbing()
                if uphill_spot:
                    self.current_location = uphill_spot

            if movement.is_restricted(self, *fishing_spot):
                return self.explore_random_spot()
        
            if restricted_areas.is_restricted_area(fishing_spot[0], fishing_spot[1], self.model.current_date):
                return self.explore_random_spot()
            self.current_location = fishing_spot
        self.at_sea = True
        return self.current_location

    def get_fishSpot_knowledge(self) -> Optional[Tuple[int, int]]:
        good_spots = memory.get_good_spots(self)
        if good_spots:
            spot, _ = random.choice(list(good_spots))
            return spot
        return self.explore_random_spot()

    def get_fishSpot_expertise(self) -> Optional[Tuple[int, int]]:
        fishing_agents = [
            a
            for a in self.model.agents
            if a is not self
            and getattr(a, "gone_fishing", False)
            and getattr(a, "pos", None)
        ]
        if fishing_agents:
            expert = max(fishing_agents, key=lambda a: a.total_catch)
            if getattr(expert, "pos", None):
                return expert.pos
        return self.get_fishSpot_knowledge()

    def get_fishSpot_descriptive_norm(self) -> Optional[Tuple[int, int]]:
        spot = self.fishspot_with_most_fishers()
        return spot if spot else self.get_fishSpot_knowledge()

    def fishspot_with_most_fishers(self) -> Optional[Tuple[int, int]]:
        agent_counts: Dict[Tuple[int, int], int] = {}
        for agent in self.model.agents:
            if (
                agent is not self
                and getattr(agent, "gone_fishing", False)
                and getattr(agent, "pos", None)
            ):
                pos = agent.current_location
                nearby = self.get_agents_in_radius(pos, radius=1)
                agent_counts[pos] = (
                    agent_counts.get(pos, 0) + 1 + len(nearby)
                )

        return max(agent_counts, key=agent_counts.get) if agent_counts else None

    def get_fishSpot_uphill_climbing(self) -> Optional[Tuple[int, int]]:
        if self.current_location:
            neighbors = self.get_neighbor_positions_in_radius(
                self.current_location, radius=1
            )
            valid_neighbors = [
                (pos, self.model.get_cell_value(pos[0], pos[1], self.fisher_type))
                for pos in neighbors
            ]
            if valid_neighbors:
                best_pos, _ = max(valid_neighbors, key=lambda item: item[1])
                return best_pos

        return self.get_fishSpot_knowledge()

    # ------------------------------------------------------------------
    # Spatial helpers
    # ------------------------------------------------------------------

    def calculate_distance(
        self,
        pos1: Optional[Tuple[int, int]],
        pos2: Optional[Tuple[int, int]],
    ) -> float:
        """Returns the Euclidean distance between two grid positions.

        Args:
            pos1: First ``(x, y)`` position.
            pos2: Second ``(x, y)`` position.

        Returns:
            Euclidean distance, or 0 if either position is None.
        """
        if not pos1 or not pos2:
            return 0.0
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return (dx ** 2 + dy ** 2) ** 0.5

    def get_agents_in_radius(
        self,
        pos: Optional[Tuple[int, int]],
        radius: float = 3,
    ) -> List["FisherAgent"]:
        """Returns all agents within a given radius of a position.

        Args:
            pos: Centre ``(x, y)`` position.
            radius: Search radius in grid units.

        Returns:
            List of ``FisherAgent`` objects within ``radius``, excluding
            the calling agent.
        """
        if not pos:
            return []
        return [
            agent
            for agent in self.model.agents
            if agent is not self
            and getattr(agent, "current_location", None)
            and self.calculate_distance(pos, agent.current_location) <= radius
        ]

    def get_neighbor_positions_in_radius(
        self,
        pos: Tuple[int, int],
        radius: int = 1,
    ) -> List[Tuple[int, int]]:
        """Returns all patch positions within a Moore neighbourhood.

        Args:
            pos: Centre ``(x, y)`` position.
            radius: Chebyshev radius (1 = immediate neighbours,
                includes diagonals).

        Returns:
            List of ``(x, y)`` tuples from Mesa's grid neighbourhood.
        """
        if not pos:
            return []
        return list(
            self.model.grid.get_neighborhood(
                pos, moore=True, include_center=False, radius=radius
            )
        )

    def is_restricted(self, x: int, y: int) -> bool:
        return movement.is_restricted(self, x, y)

    def move_to(self, x: int, y: int) -> None:
        movement.move_to(self, x, y)

    def calculate_travel_cost(
        self,
        from_pos: Optional[Tuple[int, int]],
        to_pos: Optional[Tuple[int, int]],
    ) -> float:
        return movement.calculate_travel_cost(self, from_pos, to_pos)

    def update_memory_good_spots(
        self,
        location: Tuple[int, int],
        catch: float,
        expected_catch: float,
    ) -> None:
        memory.update_memory_good_spots(self, location, catch, expected_catch)

    def update_memory(self, trip_info: Dict[str, Any]) -> None:
        memory.update_memory(self, trip_info)

    def land_fish(self) -> None:
        fishing.land_fish(self)

    # ------------------------------------------------------------------
    # Perception & satisfaction
    # ------------------------------------------------------------------

    def update_growth_perception(self) -> None:
        """Updates ``growth_perception`` from recent capital changes.

        Appends +1, 0, or -1 to a running list based on whether
        capital has risen, stayed flat, or fallen. The modal value
        becomes ``growth_perception``.
        """
        if not hasattr(self, "prev_capital"):
            self.prev_capital = self.capital
            self.growth_perception = 0.0
            return

        if self.capital > self.prev_capital:
            indicator = 1
        elif self.capital < self.prev_capital:
            indicator = -1
        else:
            indicator = 0

        if not hasattr(self, "growth_perception_list"):
            self.growth_perception_list: List[int] = []

        self.growth_perception_list.append(indicator)
        if len(self.growth_perception_list) > self.memory_size:
            self.growth_perception_list.pop(0)

        if self.growth_perception_list:
            counts = Counter(self.growth_perception_list)
            mode_value = counts.most_common(1)[0][0]
            self.growth_perception = float(mode_value)

        self.prev_capital = self.capital

    def update_satisfaction(self) -> None:
        """Updates home and growth satisfaction from the last 14 trips.

        ``satisfaction_home`` reflects the proportion of recent days
        spent at home; ``satisfaction_growth`` reflects the profit trend
        between the first and second halves of the recent window.
        """
        recent_trips = list(self.memory)[-14:]

        days_at_home = sum(
            1 for t in recent_trips if not t.get("went_fishing", True)
        )
        self.satisfaction_home = (
            days_at_home / len(recent_trips) if recent_trips else 0.0
        )

        if len(recent_trips) >= 14:
            first_half = recent_trips[:7]
            second_half = recent_trips[7:]
            avg_profit_first = statistics.mean(
                t["profit"] for t in first_half
            )
            avg_profit_second = statistics.mean(
                t["profit"] for t in second_half
            )
            if avg_profit_first != 0:
                profit_growth = (
                    avg_profit_second - avg_profit_first
                ) / abs(avg_profit_first)
                self.satisfaction_growth = max(
                    0.0, min(1.0, (profit_growth + 1) / 2)
                )
            else:
                self.satisfaction_growth = 0.5
        else:
            avg_profit = (
                statistics.mean(t["profit"] for t in recent_trips)
                if recent_trips
                else 0.0
            )
            self.satisfaction_growth = (
                min(1.0, avg_profit / (self.cost_existence * 2))
                if avg_profit > 0
                else 0.0
            )

    def update_perception_scarcity(self) -> None:
        """Updates ``perceive_scarcity`` from recent catch ratios.

        Sets the flag to True when the mean recent catch falls below
        ``config.SCARCITY_CATCH_RATIO_THRESHOLD`` of the expected catch.
        Requires at least ``config.SCARCITY_MIN_MEMORY`` trips in memory.
        """
        if len(self.memory) < config.SCARCITY_MIN_MEMORY:
            self.perceive_scarcity = False
            return

        recent = list(self.memory)[-config.SCARCITY_MIN_MEMORY:]
        recent_catches = [
            t["catch"] for t in recent if t.get("went_fishing", True)
        ]

        if not recent_catches or self.catchability <= 0:
            self.perceive_scarcity = False
            return

        avg_recent_catch = statistics.mean(recent_catches)
        catch_ratio = avg_recent_catch / self.catchability
        self.perceive_scarcity = (
            catch_ratio < config.SCARCITY_CATCH_RATIO_THRESHOLD
        )

    # ------------------------------------------------------------------
    # Summaries & debug
    # ------------------------------------------------------------------

    def get_agent_summary(self) -> Dict[str, Any]:
        """Returns a comprehensive debug snapshot of the agent's state.

        Appends trawler-specific fields and memory statistics when
        applicable.

        Returns:
            Dict covering identity, financial state, activity counters,
            decision variables, and memory metrics.
        """
        summary: Dict[str, Any] = {
            "id": self.unique_id,
            "type": self.fisher_type,
            "age": self.age,
            "capital": self.capital,
            "wealth": self.wealth,
            "total_revenue": self.total_revenue,
            "total_costs": self.total_cost,
            "total_profit": self.total_profit,
            "bankrupt": self.bankrupt,
            "total_catch": self.total_catch,
            "days_at_sea": self.days_at_sea,
            "profitable_trips": self.profitable_trip,
            "unprofitable_trips": self.unprofitable_trip,
            "at_home": self.at_home,
            "at_sea": self.at_sea,
            "gone_fishing": self.gone_fishing,
            "fished_today": self.fished_today,
            "lay_low": self.lay_low,
            "will_fish": self.will_fish,
            "growth_perception": self.growth_perception,
            "memory_size": len(self.memory),
            "good_spots_count": len(self.good_spots_memory),
        }

        if self.fisher_type == "trawler":
            summary["fish_onboard"] = self.fish_onboard
            summary["storing_capacity"] = self.storing_capacity
            summary["jumped"] = self.jumped

        if self.memory:
            summary.update(memory.get_memory_statistics())

        return summary

    def print_status(self) -> None:
        """Prints a compact debug summary to stdout."""
        status = "gone fishing" if self.gone_fishing else "at home"
        print(f"{status} Agent {self.unique_id} ({self.fisher_type}):")
        print(f"    Capital: {self.capital:.2f}")
        print(f"    Total catch: {self.total_catch:.0f}")
        print(f"    At home: {self.at_home}")
        if self.memory:
            recent = self.memory[-1]
            print(
                f"    Last trip:"
                f" catch={recent['catch']:.0f},"
                f" profit={recent['profit']:.2f}"
            )

    def check_effort_quota(self) -> bool:
        return self.yearly_effort >= self.effort_quotas

    def check_landing_quota(self) -> bool:
        if self.landings_quotas is None:
            return False
        if isinstance(self.landings_quotas, np.ndarray):
            for name, quota in zip(self.model.species_names, self.landings_quotas):
                if quota > 0 and self.yearly_catch_by_species.get(name, 0) >= quota:
                    return True
            return False
        return self.yearly_catch >= self.landings_quotas
    
    # ------------------------------------------------------------------
    # Mesa step
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Executes one simulation day for the agent.

        In order: make decision → execute decision → update growth
        perception → update satisfaction → update scarcity perception →
        check bankruptcy.
        """
        self.make_decision()
        self.execute_decision()
        self.update_growth_perception()
        self.update_satisfaction()
        self.update_perception_scarcity()
        finance.check_bankruptcy(self)
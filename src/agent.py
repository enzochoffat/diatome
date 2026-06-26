"""Fisher agent for the FIBE fishery simulation.

Defines ``FisherAgent``, a Mesa-based agent encapsulating the decision
logic, memory system, economic state, and spatial behaviour of individual
fishers (archipelago, coastal, or trawler types).
"""

import logging
import random
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from mesa import Agent

from src import config
from src.Agent.archipelagos import Archipelago
from src.Agent.coastal import Coastal
from src.Agent.trawler import Trawler

logger = logging.getLogger(__name__)

class FisherAgent(Agent):
    """A fisher agent in the FIBE fishery model.

    Represents one individual fisher. Depending on ``fisher_type``,
    the agent uses different cost structures, accessible regions,
    catchability values, and decision models (``Archipelago``,
    ``Coastal``, or ``Trawler``).

    Attributes:
        fisher_type: One of ``"archipelago"``, ``"coastal"``,
            or ``"trawler"``.
        unique_id: Integer identifier unique within the model.
        name: Optional display name.
        port: Optional home-port ``(x, y)`` coordinate.
        capital: Current financial capital (SEK).
        wealth: Alias for ``capital`` (updated in sync).
        bankrupt: Whether the agent has gone bankrupt.
        memory: List of recent trip dicts (capped at ``memory_size``).
        good_spots_memory: Spatial memory dict keyed by ``(x, y)``.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        unique_id: int,
        model: Any,
        fisher_type: str,
        initial_capital: Optional[float] = None,
        name: Optional[str] = None,
        port: Optional[Tuple[int, int]] = None,
        habitat: Optional[List[str]] = None,
    ) -> None:
        """Initialises the fisher agent.

        Args:
            unique_id: Integer identifier.
            model: Parent ``FisheryModel`` instance.
            fisher_type: One of ``"archipelago"``, ``"coastal"``,
                or ``"trawler"``.
            initial_capital: Starting capital in SEK. Uses
                ``config.INITIAL_CAPITAL`` if None.
            name: Optional display name for the agent.
            port: Optional home-port ``(x, y)`` coordinate.
        """
        super().__init__(model)
        self.fisher_type = fisher_type
        self.unique_id = unique_id
        self.name = name
        self.port = port
        self.restricted_mask = habitat

        # Financial state
        self.capital = (
            float(initial_capital)
            if initial_capital is not None
            else config.INITIAL_CAPITAL
        )
        self.wealth = 0.0
        self.age = random.randint(config.MIN_AGE, config.MAX_AGE)

        # Cumulative statistics
        self.days_at_sea = 0
        self.total_catch = 0.0
        self.total_profit = 0.0
        self.total_cost = 0.0
        self.total_revenue = 0.0
        self.yearly_catch = 0.0
        self.yearly_profit = 0.0

        # Economic status
        self.bankrupt = False
        self.years_active = 0
        self.profitable_trip = 0
        self.unprofitable_trip = 0

        # Trip tracking
        self.accumulated_catch = 0.0
        self.trip_cost = 0.0
        self.days_in_current_trip = 0
        self.days_at_sea_current_trip = 0

        # Spatial state
        self.current_location: Optional[Tuple[int, int]] = None
        self.target_location: Optional[Tuple[int, int]] = None
        self.current_region: Optional[str] = None
        self.display_location: Optional[Tuple[int, int]] = None

        # Activity flags
        self.at_home = True
        self.at_sea = False
        self.gone_fishing = False
        self.fished_today = False
        self.lay_low = False
        self.lay_low_counter = 0

        # Decision-making
        self.will_fish = False
        self.region_preference: Optional[str] = None
        self.spot_selection_strategy = "knowledge"
        self.growth_perception = 0.0

        # Type-specific attributes (populated by _set_type_attributes)
        self._set_type_attributes()

        # Temporal memory
        self.memory_size = config.DEFAULT_MEMORY_SIZE
        self.memory: List[Dict[str, Any]] = []

        # Spatial memory: {(x, y): {'visits': n, 'avg_catch': f, ...}}
        self.good_spots_memory: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.good_spots_threshold = config.GOOD_SPOT_EFFICIENCY_THRESHOLD

        # Decision thresholds
        self.satisfaction_home_threshold = config.SATISFACTION_HOME_THRESHOLD
        self.satisfaction_growth_threshold = (
            config.SATISFACTION_GROWTH_THRESHOLD
        )
        self.scarce_perception_threshold = config.SCARCE_PERCEPTION_THRESHOLD

        # Trawler-specific
        self.fish_onboard = 0.0
        self.storing_capacity = (
            config.TRAWLER_STORAGE_CAPACITY
            if fisher_type == "trawler"
            else self.catchability
        )
        self.jumped = False

    def _set_type_attributes(self) -> None:
        """Sets cost, catchability, and social attributes by fisher type."""
        if self.fisher_type == "archipelago":
            self.cost_existence = self.model.LOW_COST_EXISTENCE
            self.cost_activity = self.model.LOW_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_ARCHEPELAGO
            self.accessible_regions = ["A"]
            self.lifestyle_preference = "high"
            self.max_good_spots = 5
            self.has_partner = True
            self.has_colleagues = False
            self.has_technologie = False

        elif self.fisher_type == "coastal":
            self.cost_existence = self.model.MEDIUM_COST_EXISTENCE
            self.cost_activity = self.model.MEDIUM_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_COASTAL
            self.accessible_regions = ["A", "B"]
            self.lifestyle_preference = "medium"
            self.max_good_spots = 3
            self.wanna_be_home = False
            self.has_partner = True
            self.has_colleagues = True
            self.has_technologie = False
            self.satisfaction_home = 1.0 - random.randint(0, 50) / 100
            self.satisfaction_growth = 1.0 - random.randint(0, 50) / 100

        elif self.fisher_type == "trawler":
            self.cost_existence = self.model.HIGH_COST_EXISTENCE
            self.cost_activity = self.model.HIGH_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_TRAWLER
            self.accessible_regions = ["B", "C", "D"]
            self.lifestyle_preference = "low"
            self.max_good_spots = 2
            self.has_partner = False
            self.has_colleagues = True
            self.has_technologie = True

    # ------------------------------------------------------------------
    # Memory management
    # ------------------------------------------------------------------

    def update_memory(self, trip_info: Dict[str, Any]) -> None:
        """Appends a trip record to temporal memory, capping at capacity.

        Args:
            trip_info: Dict with keys ``location``, ``catch``, ``cost``,
                ``profit``, ``days``, ``tick``, ``region``, and
                ``went_fishing``.
        """
        self.memory.append(trip_info)
        if len(self.memory) > self.memory_size:
            self.memory.pop(0)

    def update_memory_good_spots(
        self,
        location: Tuple[int, int],
        catch: float,
        expected_catch: float,
    ) -> None:
        """Updates the spatial memory record for a fishing location.

        Args:
            location: ``(x, y)`` grid position.
            catch: Actual fish caught at this location.
            expected_catch: Expected catch based on catchability.
        """
        catch_efficiency = catch / expected_catch if expected_catch > 0 else 0.0

        if location in self.good_spots_memory:
            spot = self.good_spots_memory[location]
            total_visits = spot["visits"]
            spot["avg_catch"] = (
                spot["avg_catch"] * total_visits + catch
            ) / (total_visits + 1)
            spot["visits"] += 1
            spot["last_visit"] = self.model.current_step
            spot["efficiency"] = catch_efficiency
        else:
            self.good_spots_memory[location] = {
                "avg_catch": catch,
                "visits": 1,
                "last_visit": self.model.current_step,
                "efficiency": catch_efficiency,
            }

        self.good_spots_memory[location]["is_good"] = (
            catch_efficiency >= self.good_spots_threshold
        )

    def get_good_spots(
        self,
        region: Optional[str] = None,
        min_visits: int = 1,
    ) -> List[Tuple[Tuple[int, int], Dict[str, Any]]]:
        """Returns remembered good fishing spots, sorted by average catch.

        Args:
            region: If provided, only spots in this region are returned.
            min_visits: Minimum visit count to include a spot.

        Returns:
            List of ``(location, memory_info)`` tuples, sorted by
            ``avg_catch`` descending.
        """
        good_spots = []
        for location, memory in self.good_spots_memory.items():
            if memory["visits"] < min_visits:
                continue
            if not memory.get("is_good", False):
                continue
            if region is not None:
                patch = self.model.get_patch_info(location[0], location[1])
                if patch and patch["region"] != region:
                    continue
            good_spots.append((location, memory))

        good_spots.sort(key=lambda item: item[1]["avg_catch"], reverse=True)
        return good_spots

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Computes aggregate statistics over all stored trip records.

        Returns:
            Dict with keys ``avg_catch``, ``median_catch``,
            ``avg_profit``, ``median_profit``, ``avg_cost``,
            ``success_rate``, ``recent_trend``, and ``total_trips``.
            All values are 0 when memory is empty.
        """
        if not self.memory:
            return {
                "avg_profit": 0,
                "avg_catch": 0,
                "avg_cost": 0,
                "success_rate": 0,
                "recent_trend": 0,
            }

        catches = [t["catch"] for t in self.memory]
        profits = [t["profit"] for t in self.memory]
        costs = [t["cost"] for t in self.memory]

        fishing_trips = [
            t for t in self.memory if t.get("went_fishing", True)
        ]
        if fishing_trips:
            profitable = sum(
                1 for t in fishing_trips if t["profit"] > 0
            )
            success_rate = profitable / len(fishing_trips)
        else:
            success_rate = 0.0

        trend = 0.0
        if len(profits) >= 14:
            recent_avg = statistics.mean(profits[-7:])
            older_avg = statistics.mean(profits[-14:-7])
            if older_avg != 0:
                trend = (recent_avg - older_avg) / abs(older_avg)

        return {
            "avg_catch": statistics.mean(catches),
            "median_catch": statistics.median(catches),
            "avg_profit": statistics.mean(profits),
            "median_profit": statistics.median(profits),
            "avg_cost": statistics.mean(costs),
            "success_rate": success_rate,
            "recent_trend": trend,
            "total_trips": len(self.memory),
        }

    def get_regional_memory_stats(
        self, region: str
    ) -> Dict[str, Any]:
        """Returns memory statistics filtered to a specific region.

        Args:
            region: Region identifier (``"A"``, ``"B"``, ``"C"``,
                or ``"D"``).

        Returns:
            Dict with ``trip``, ``avg_catch``, ``avg_profit``, and
            ``last_visit``. All numeric values are 0 and
            ``last_visit`` is None when no trips exist for the region.
        """
        regional_trips = [
            t for t in self.memory if t.get("region") == region
        ]
        if not regional_trips:
            return {
                "trip": 0,
                "avg_catch": 0,
                "avg_profit": 0,
                "last_visit": None,
            }

        return {
            "trip": len(regional_trips),
            "avg_catch": statistics.mean(
                t["catch"] for t in regional_trips
            ),
            "avg_profit": statistics.mean(
                t["profit"] for t in regional_trips
            ),
            "last_visit": regional_trips[-1]["tick"],
        }

    def forget_old_spots(self, max_age_ticks: int) -> None:
        """Removes spatial memory entries that have not been visited recently.

        Args:
            max_age_ticks: Age threshold in simulation ticks beyond
                which a spot is forgotten.
        """
        current_tick = self.model.current_step
        locations_to_remove = [
            loc
            for loc, mem in self.good_spots_memory.items()
            if current_tick - mem["last_visit"] > max_age_ticks
        ]
        for location in locations_to_remove:
            del self.good_spots_memory[location]

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def is_restricted(self, x: int, y: int) -> bool:
        """Checks whether a location is restricted by habitat or topology.

        Args:
            x: X-coordinate of the location.
            y: Y-coordinate of the location.
        
        Returns:
            True if the location is restricted, False otherwise.
        """
        if self.restricted_mask is None:
            return False
        return self.restricted_mask[y][x]

    def move_to(self, x: int, y: int) -> None:
        """Moves the agent to ``(x, y)`` on the Mesa grid.

        Args:
            x: Target column.
            y: Target row.
        """
        if self.is_restricted(x, y):
            return
        
        if self.pos is not None:
            self.model.grid.remove_agent(self)
        self.model.grid.place_agent(self, (x, y))
        self.current_location = (x, y)
        self.display_location = (x, y)

    # ------------------------------------------------------------------
    # Cost helpers
    # ------------------------------------------------------------------

    def calculate_travel_cost(
        self,
        from_pos: Optional[Tuple[int, int]],
        to_pos: Optional[Tuple[int, int]],
    ) -> float:
        """Calculates Euclidean distance-based travel cost.

        Args:
            from_pos: Starting ``(x, y)`` position.
            to_pos: Destination ``(x, y)`` position.

        Returns:
            Travel cost in SEK, or 0 if either position is None.
        """
        if from_pos is None or to_pos is None:
            return 0.0
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        distance = (dx ** 2 + dy ** 2) ** 0.5
        return distance * config.TRAVEL_COST_PER_UNIT

    def get_travel_cost(self, region: str) -> float:
        """Returns the fixed travel cost to a named region.

        Args:
            region: Destination region identifier.

        Returns:
            Travel cost in SEK. Returns 0 for unrecognised regions.
        """
        if region == "A":
            return self.model.LOW_COST_TRAVEL
        if region == "B":
            return (
                self.model.MEDIUM_COST_TRAVEL_BIGVESSEL
                if self.fisher_type == "trawler"
                else self.model.MEDIUM_COST_TRAVEL
            )
        if region in {"C", "D"}:
            return self.model.HIGH_COST_TRAVEL
        return 0.0

    def get_travel_cost_between_regions(
        self, from_region: str, to_region: str
    ) -> float:
        """Returns the inter-region travel cost (half the destination cost).

        Args:
            from_region: Origin region identifier (unused currently).
            to_region: Destination region identifier.

        Returns:
            Half the standard travel cost to ``to_region``.
        """
        return self.get_travel_cost(to_region) * 0.5

    def estimate_trip_cost(
        self, location: Optional[Tuple[int, int]]
    ) -> float:
        """Estimates the total cost of a trip to a given location.

        Args:
            location: Target ``(x, y)`` position. If None, only fixed
                costs are returned.

        Returns:
            Estimated cost in SEK.
        """
        if not location:
            return self.cost_activity + self.cost_existence

        travel_cost = (
            self.calculate_travel_cost(self.current_location, location)
            if self.current_location
            else self.get_travel_cost(self.accessible_regions[0])
        )
        return self.cost_activity + self.cost_existence + travel_cost

    def can_afford_trip(self, cost: float) -> bool:
        """Checks whether the agent can afford a fishing trip.

        Trawlers are never blocked by an upfront affordability gate.
        Other types must have ``capital + safety_buffer >= cost``.

        Args:
            cost: Estimated trip cost in SEK.

        Returns:
            True if the trip is affordable.
        """
        if self.fisher_type == "trawler":
            return True
        safety_buffer = config.get_safety_buffer(self.cost_existence)
        return self.capital + safety_buffer >= cost

    # ------------------------------------------------------------------
    # Financial state
    # ------------------------------------------------------------------

    def calculate_profit(
        self, catch: float, costs: float
    ) -> Dict[str, Any]:
        """Computes revenue, costs, and profit for a fishing result.

        Args:
            catch: Amount of fish caught.
            costs: Total costs incurred.

        Returns:
            Dict with ``revenue``, ``costs``, ``profit``, ``catch``,
            ``price_per_unit``, and ``location`` (always None).
        """
        revenue = catch * self.model.FISH_PRICE
        profit = revenue - costs
        return {
            "revenue": revenue,
            "costs": costs,
            "profit": profit,
            "catch": catch,
            "price_per_unit": self.model.FISH_PRICE,
            "location": None,
        }

    def update_finances(
        self,
        profit: float,
        cost: float,
        revenue: float,
        is_trip: bool = True,
    ) -> None:
        """Updates the agent's financial state.

        Args:
            profit: Net profit (may be negative).
            cost: Total costs incurred.
            revenue: Total revenue earned.
            is_trip: If True, increments profitable / unprofitable trip
                counters based on the sign of ``profit``.
        """
        self.capital += profit
        self.total_profit += profit
        self.total_cost += cost
        self.total_revenue += revenue
        self.wealth = self.capital

        if is_trip:
            if profit > 0:
                self.profitable_trip += 1
            else:
                self.unprofitable_trip += 1

        self.check_bankruptcy()

    def check_bankruptcy(self) -> None:
        """Flags the agent as bankrupt if capital falls below threshold."""
        bankruptcy_threshold = -(self.cost_existence * 7)
        if self.capital < bankruptcy_threshold:
            logger.warning(
                "Agent went bankrupt",
                extra={
                    "agent_id": self.unique_id, 
                    "capital": self.capital
                },
            )
            self.bankrupt = True

    # ------------------------------------------------------------------
    # Fishing
    # ------------------------------------------------------------------

    def go_fish(
        self, location: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Executes one day of fishing at the given location.

        Applies type-specific catch logic, deducts costs, and updates
        financial and trip state accordingly.

        Args:
            location: ``(x, y)`` target fishing position.

        Returns:
            Dict with keys ``catch``, ``costs``, ``profit``,
            ``revenue``, and ``location``.
        """
        patch = self.model.get_patch_info(location[0], location[1])

        if not patch:
            logger.error(
                "Invalid fishing location",
                extra={
                    "agent_id": self.unique_id,
                    "location": location,
                },
            )
            return {
                "catch": 0,
                "costs": 0,
                "profit": 0,
                "revenue": 0,
                "location": location,
            }

        current_region = patch["region"]

        logger.debug(
            "Fishing attempt",
            extra={
                "agent_id": self.unique_id,
                "region": current_region,
                "stock": patch["fish_stock"],
            }
        )

        # --- Catch calculation ---
        if self.fisher_type == "coastal":
            actual_catch = self._coastal_catch(location, patch, current_region)
        else:
            available_stock = patch["fish_stock"]
            potential_catch = min(self.catchability, available_stock)
            actual_catch = self.model.reduce_stock(
                location[0], location[1], potential_catch
            )

        # --- Travel cost ---
        if self.fisher_type in ("archipelago", "coastal"):
            travel_cost = self.get_travel_cost(current_region)
        elif self.fisher_type == "trawler":
            travel_cost = self._trawler_travel_cost(
                location, actual_catch, current_region
            )
        else:
            travel_cost = 0.0

        total_cost = self.cost_existence + self.cost_activity + travel_cost

        result = self.calculate_profit(actual_catch, total_cost)

        logger.debug(
            "Fishing economics",
            extra={
                "agent_id": self.unique_id,
                "catch": actual_catch,
                "costs": total_cost,
                "profit": result["profit"],
            }
        )

        # --- Financial update ---
        if self.fisher_type == "trawler":
            self.update_finances(
                profit=-total_cost, cost=total_cost, revenue=0.0,
                is_trip=False,
            )
            self.accumulated_catch += actual_catch
            self.fish_onboard += actual_catch
            self.days_at_sea += 1
        else:
            result = self.calculate_profit(actual_catch, total_cost)
            if result["profit"] > 0:
                self.profitable_trip += 1
            else:
                self.unprofitable_trip += 1
            self.update_finances(
                result["profit"], result["costs"], result["revenue"],
                is_trip=True,
            )
            self.accumulated_catch += actual_catch
            self.days_at_sea += 1
            self.total_catch += actual_catch

        self.update_memory_good_spots(location, actual_catch, self.catchability)

        if self.fisher_type == "trawler":
            profit_out = -total_cost
            revenue_out = 0.0
        else:
            profit_out = actual_catch * self.model.FISH_PRICE - total_cost
            revenue_out = actual_catch * self.model.FISH_PRICE

        return {
            "catch": actual_catch,
            "costs": total_cost,
            "profit": profit_out,
            "revenue": revenue_out,
            "location": location,
        }

    def _coastal_catch(
        self,
        location: Tuple[int, int],
        patch: Dict[str, Any],
        current_region: str,
    ) -> float:
        """Computes the coastal split-patch catch logic.

        Args:
            location: Primary fishing ``(x, y)`` position.
            patch: Patch attributes at ``location``.
            current_region: Region label of ``patch``.

        Returns:
            Total fish caught across the primary and one neighbour patch.
        """
        stock_here = patch["fish_stock"]
        neighbors = self.get_neighbor_positions_in_radius(location, radius=1)
        same_region_neighbors = [
            ((nx, ny), self.model.get_patch_info(nx, ny))
            for nx, ny in neighbors
            if (
                n_patch := self.model.get_patch_info(nx, ny)
            ) and n_patch["region"] == current_region
        ]

        if same_region_neighbors:
            other_pos, other_patch = random.choice(same_region_neighbors)
            stock_other = other_patch["fish_stock"]

            catch_here = round(0.5 * self.catchability)
            catch_other = self.catchability - catch_here

            if (stock_here < catch_here) ^ (stock_other < catch_other):
                if stock_here < catch_here:
                    catch_here = stock_here
                    catch_other = min(
                        self.catchability - catch_here, stock_other
                    )
                if stock_other < catch_other:
                    catch_other = stock_other
                    catch_here = min(
                        self.catchability - catch_other, stock_here
                    )
            else:
                if stock_here < catch_here:
                    catch_here = stock_here
                if stock_other < catch_other:
                    catch_other = stock_other

            actual_here = self.model.reduce_stock(
                location[0], location[1], catch_here
            )
            actual_other = self.model.reduce_stock(
                other_pos[0], other_pos[1], catch_other
            )
            return actual_here + actual_other

        return self.model.reduce_stock(
            location[0], location[1], min(self.catchability, stock_here)
        )

    def _trawler_travel_cost(
        self,
        location: Tuple[int, int],
        actual_catch: float,
        current_region: str,
    ) -> float:
        """Computes the trawler travel cost and updates ``gone_fishing``.

        Args:
            location: Current fishing position.
            actual_catch: Fish caught this step.
            current_region: Current region identifier.

        Returns:
            Travel cost in SEK for this day.
        """
        if not self.gone_fishing:
            travel_cost = self.get_travel_cost(current_region)
        else:
            if self.jumped:
                travel_cost = self.get_travel_cost(current_region) / 2
                self.jumped = False
            else:
                travel_cost = 0.0

        if self.fish_onboard + actual_catch >= self.storing_capacity:
            self.gone_fishing = False
        else:
            self.gone_fishing = True

        return travel_cost

    def land_fish(self) -> None:
        """Lands the trawler's fish and records the revenue.

        Costs have already been deducted daily in ``go_fish``; this
        method only adds the revenue from the accumulated catch.
        Only acts when ``fisher_type == "trawler"`` and fish are aboard.
        """
        if self.fisher_type != "trawler" or self.fish_onboard <= 0:
            return

        revenue = self.fish_onboard * self.model.FISH_PRICE
        self.capital += revenue
        self.wealth += revenue
        self.total_revenue += revenue
        self.total_catch += self.fish_onboard

        if revenue > 0:
            self.profitable_trip += 1
        else:
            self.unprofitable_trip += 1

        self.fish_onboard = 0.0
        self.accumulated_catch = 0.0
        self.days_in_current_trip = 0
        self.jumped = False
        self.gone_fishing = False
        self.at_sea = False

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def stay_home(self, pay_existence_cost: bool = False) -> None:
        """Keeps the agent at home, optionally paying existence costs.

        Args:
            pay_existence_cost: If True, deducts ``cost_existence``
                and records it in memory.
        """
        existence_cost = self.cost_existence if pay_existence_cost else 0.0

        if pay_existence_cost:
            self.update_finances(
                profit=-existence_cost,
                cost=existence_cost,
                revenue=0.0,
                is_trip=False,
            )

        self.at_home = True
        self.gone_fishing = False
        self.at_sea = False
        self.will_fish = False

        self.update_memory({
            "location": None,
            "catch": 0,
            "cost": existence_cost,
            "profit": -existence_cost if pay_existence_cost else 0,
            "days": 1,
            "tick": self.model.current_step,
            "region": None,
            "went_fishing": False,
        })

    def stay_home_state_only(self) -> None:
        """Updates state to 'at home' without any financial transaction."""
        self.at_home = True
        self.gone_fishing = False
        self.at_sea = False
        self.will_fish = False

    def return_home(self) -> None:
        """Returns the agent to home port after a fishing trip.

        Pays the return travel cost, moves to the port position, and
        for trawlers calls ``land_fish``. Resets all trip variables.
        """
        return_cost = self.calculate_travel_cost(
            self.current_location, self.port
        )
        self.update_finances(
            profit=0.0, cost=return_cost, revenue=0.0, is_trip=False
        )

        if self.port:
            self.move_to(self.port[0], self.port[1])

        if self.fisher_type == "trawler":
            self.land_fish()

        self.at_sea = False
        self.gone_fishing = False
        self.at_home = True
        self.current_region = None
        self.current_location = None

        if getattr(self, "pos", None) is not None:
            self.model.grid.remove_agent(self)

        self.accumulated_catch = 0.0
        self.trip_cost = 0.0
        self.days_in_current_trip = 0

    def reset_daily_flags(self) -> None:
        """Clears flags that must reset between simulation days."""
        self.fished_today = False

    def finalize_day(self) -> None:
        """Handles end-of-day state transitions.

        Archipelago and coastal agents make day trips and return home
        after ``fished_today`` is set.
        """
        if self.fisher_type in ("archipelago", "coastal") and self.fished_today:
            self.return_home()

    def reset_yearly_counters(self) -> None:
        """Resets yearly cumulative counters at the start of each year."""
        self.yearly_catch = 0.0
        self.yearly_profit = 0.0

    # ------------------------------------------------------------------
    # Decision-making
    # ------------------------------------------------------------------

    def make_decision(self) -> None:
        """Routes the agent's decision to the appropriate type model.

        Calls ``Archipelago.satisfice_lifestyle``,
        ``Coastal.optimise_lifestyle_and_growth``, or
        ``Trawler.optimise_growth`` depending on ``fisher_type``.
        Sets ``will_fish = False`` for unknown types.
        """
        logger.debug(
            "Decision start",
            extra={
                "agent_id": self.unique_id,
                "type": self.fisher_type,
                "capital": self.capital,
            },
        )
        if self.fisher_type == "archipelago":
            Archipelago.satisfice_lifestyle(self)
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
                "region": self.region_preference,
            }
        )

    def execute_decision(self) -> None:
        """Executes the agent's fishing decision for the current day.

        Handles bankrupt agents, lay-low periods, willingness to fish,
        and trip affordability checks.
        """
        if self.bankrupt:
            logger.warning(
                "Bankrupt agent forced to fish",
                extra={"agent_id": self.unique_id},
            )
            self.lay_low = False
            self.will_fish = True
            return

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
            self.update_finances(
                profit=-existence_cost,
                cost=existence_cost,
                revenue=0.0,
                is_trip=False,
            )
            self.stay_home_state_only()
            return

        if self.will_fish:
            target_region = (
                self.region_preference
                if self.region_preference
                else self.accessible_regions[0]
            )
            target_spot = self.decide_fishSpot(target_region)

            if target_spot:
                estimated_cost = self.estimate_trip_cost(target_spot)
                if not self.can_afford_trip(estimated_cost):
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
                        "region": target_region,
                        "target_spot": target_spot,
                    },
                )

                self.at_home = False
                self.gone_fishing = True
                self.current_region = target_region

                self.move_to(target_spot[0], target_spot[1])
                trip_result = self.go_fish(target_spot)

                logger.debug(
                    "Fishing result",
                    extra={
                        "agent_id": self.unique_id,
                        "catch": trip_result["catch"],
                        "profit": trip_result["profit"],
                    }
                )
                self.fished_today = True

                self.update_memory({
                    "location": target_spot,
                    "catch": trip_result["catch"],
                    "cost": trip_result["costs"],
                    "profit": trip_result["profit"],
                    "days": 1,
                    "tick": self.model.current_step,
                    "region": target_region,
                    "went_fishing": True,
                })
            else:
                logger.debug(
                    "No fishing spot found",
                    extra={"agent_id": self.unique_id},
                )
                self.stay_home(pay_existence_cost=True)
        else:
            logger.debug(
                "Agent stays home",
                extra={"agent_id": self.unique_id}
            )
            self.stay_home(pay_existence_cost=True)

    def _calculate_region_preference(self) -> str:
        """Selects the preferred region via cascade comparison of expected catches.

        Mirrors the NetLogo ``set-catch-expectation-and-regionPref``
        logic from ``utils.nls``.

        Returns:
            One of ``"B"``, ``"C"``, or ``"D"`` (trawler-specific).
        """
        expected_catches = {
            region: self._estimate_catch(region)
            for region in self.accessible_regions
        }

        catch_b = expected_catches.get("B", self.catchability)
        catch_c = expected_catches.get("C", self.catchability)
        catch_d = expected_catches.get("D", self.catchability)

        if catch_b >= catch_c:
            return "B" if catch_c >= catch_d or catch_b >= catch_d else "D"
        return "C" if catch_c >= catch_d else "D"

    def _estimate_catch(self, region: str) -> float:
        """Estimates the expected catch in a region from memory.

        Args:
            region: Region identifier.

        Returns:
            Mean catch over the last 10 trips to that region, or
            ``catchability`` if no memory exists.
        """
        region_memory = [
            t for t in self.memory if t.get("region") == region
        ]
        if region_memory:
            return statistics.mean(
                t["catch"] for t in region_memory[-10:]
            )
        return self.catchability

    # ------------------------------------------------------------------
    # Spot selection
    # ------------------------------------------------------------------

    def select_fishing_spot(
        self, region: Optional[str] = None
    ) -> Optional[Tuple[int, int]]:
        """Selects a fishing spot from spatial memory.

        Args:
            region: Target region. Defaults to the first accessible
                region if None.

        Returns:
            ``(x, y)`` tuple of the chosen spot, or None.
        """
        if region is None:
            region = (
                self.accessible_regions[0]
                if self.accessible_regions
                else None
            )
        if not region:
            return None

        good_spots = self.get_good_spots(region=region, min_visits=1)
        if good_spots:
            spot, _ = random.choice(good_spots)
            return spot

        return self.explore_random_spot(region)

    def explore_random_spot(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Picks a random patch near a hotspot in the given region.

        Args:
            region: Region to explore.

        Returns:
            A valid ``(x, y)`` position in ``region``, or the centre of
            a random hotspot as a fallback. Returns None if no hotspots
            exist.
        """
        hotspot_map = {
            "A": self.model.HOTSPOTS_A,
            "B": self.model.HOTSPOTS_B,
            "C": self.model.HOTSPOTS_C,
            "D": self.model.HOTSPOTS_D,
        }
        hotspots = hotspot_map.get(region)
        if not hotspots:
            return None

        base_spot = random.choice(hotspots)
        exploration_radius = 3

        for _ in range(10):
            dx = random.randint(-exploration_radius, exploration_radius)
            dy = random.randint(-exploration_radius, exploration_radius)
            candidate = (base_spot[0] + dx, base_spot[1] + dy)
            patch = self.model.get_patch_info(candidate[0], candidate[1])
            if patch and patch["region"] == region and not self.is_restricted(candidate[0], candidate[1]):
                return candidate

        return tuple(base_spot)

    def decide_fishSpot(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Selects a fishing spot using NetLogo-aligned spot-selection logic.

        For trawlers already at sea with technology, an uphill-climb
        scan is performed first. Social influence (expertise or
        descriptive norm) is then applied when the agent has colleagues.
        A second uphill pass follows movement for trawlers.

        Args:
            region: Target region identifier.

        Returns:
            ``(x, y)`` position selected for the next fishing step,
            or None if no region is provided.
        """
        if not region:
            return None

        stay_put = False
        fishing_spot = None

        if self.fisher_type == "trawler" and self.gone_fishing:
            if self.has_technologie and self.current_location:
                uphill_spot = self.get_fishSpot_uphill_climbing(region)
                if uphill_spot:
                    uphill_patch = self.model.get_patch_info(*uphill_spot)
                    current_patch = self.model.get_patch_info(
                        *self.current_location
                    )
                    if (
                        uphill_patch
                        and current_patch
                        and uphill_patch["region"] == current_patch["region"]
                    ):
                        self.current_location = uphill_spot

            patch_here = (
                self.model.get_patch_info(*self.current_location)
                if self.current_location
                else None
            )
            fish_here = patch_here["fish_stock"] if patch_here else 0
            fish_wish = self.storing_capacity - self.fish_onboard
            if fish_here < fish_wish:
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
                    fishing_spot = self.get_fishSpot_descriptive_norm(region)
                else:
                    fishing_spot = self.get_fishSpot_expertise(region)
                if fishing_spot is None:
                    fishing_spot = self.get_fishSpot_knowledge(region)
            else:
                fishing_spot = self.get_fishSpot_knowledge(region)

            if fishing_spot is None:
                return self.explore_random_spot(region)

            if self.is_restricted(*fishing_spot):
                return self.explore_random_spot(region)
            self.current_location = fishing_spot

            if self.fisher_type == "trawler" and self.has_technologie:
                uphill_spot = self.get_fishSpot_uphill_climbing(region)
                if uphill_spot:
                    uphill_patch = self.model.get_patch_info(*uphill_spot)
                    current_patch = self.model.get_patch_info(
                        *self.current_location
                    )
                    if (
                        uphill_patch
                        and current_patch
                        and uphill_patch["region"] == current_patch["region"]
                    ):
                        self.current_location = uphill_spot

        self.at_sea = True
        return self.current_location

    def get_fishSpot_knowledge(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Selects a fishing spot from spatial memory (knowledge-based).

        Args:
            region: Target region.

        Returns:
            A remembered good spot in ``region``, or a random
            exploration spot if memory is empty.
        """
        good_spots = self.get_good_spots(region)
        if good_spots:
            spot, _ = random.choice(list(good_spots))
            return spot
        return self.explore_random_spot(region)

    def get_fishSpot_expertise(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Follows the most successful fishing agent in the region.

        Args:
            region: Target region.

        Returns:
            Position of the highest-catch agent currently in
            ``region``, or falls back to knowledge-based selection.
        """
        fishing_agents = [
            a
            for a in self.model.agents
            if a is not self
            and getattr(a, "gone_fishing", False)
            and getattr(a, "current_region", None) == region
        ]
        if fishing_agents:
            expert = max(fishing_agents, key=lambda a: a.total_catch)
            if getattr(expert, "pos", None):
                return expert.pos
        return self.get_fishSpot_knowledge(region)

    def get_fishSpot_descriptive_norm(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Goes where the most other fishers are (descriptive norm).

        Args:
            region: Target region.

        Returns:
            The position with the highest local fisher density in
            ``region``, or falls back to knowledge-based selection.
        """
        spot = self.fishspot_with_most_fishers(region)
        return spot if spot else self.get_fishSpot_knowledge(region)

    def fishspot_with_most_fishers(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Finds the patch with the most fishers in a region.

        Args:
            region: Target region.

        Returns:
            ``(x, y)`` position with the highest local density of
            fishing agents, or None if no agents are present.
        """
        agent_counts: Dict[Tuple[int, int], int] = {}
        for agent in self.model.agents:
            if (
                agent is not self
                and getattr(agent, "gone_fishing", False)
                and getattr(agent, "current_region", None) == region
                and getattr(agent, "pos", None)
            ):
                pos = agent.current_location
                nearby = self.get_agents_in_radius(pos, radius=1)
                nearby_in_region = sum(
                    1
                    for a in nearby
                    if getattr(a, "current_region", None) == region
                )
                agent_counts[pos] = (
                    agent_counts.get(pos, 0) + 1 + nearby_in_region
                )

        return max(agent_counts, key=agent_counts.get) if agent_counts else None

    def get_fishSpot_uphill_climbing(
        self, region: str
    ) -> Optional[Tuple[int, int]]:
        """Moves to the neighbouring patch with the highest fish stock.

        Args:
            region: Must match the neighbour's region to be eligible.

        Returns:
            ``(x, y)`` of the best-stocked eligible neighbour, or the
            result of knowledge-based selection as a fallback.
        """
        if self.current_location:
            neighbors = self.get_neighbor_positions_in_radius(
                self.current_location, radius=1
            )
            valid_neighbors = [
                (pos, self.model.get_patch_info(pos[0], pos[1])["fish_stock"])
                for pos in neighbors
                if (
                    patch := self.model.get_patch_info(pos[0], pos[1])
                ) and patch["region"] == region
            ]
            if valid_neighbors:
                best_pos, _ = max(valid_neighbors, key=lambda item: item[1])
                return best_pos

        return self.get_fishSpot_knowledge(region)

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

    def get_financial_summary(self) -> Dict[str, Any]:
        """Returns a snapshot of the agent's financial state.

        Returns:
            Dict with ``capital``, ``wealth``, ``total_revenue``,
            ``total_costs``, ``total_profit``, ``total_catch``,
            ``profitable_trips``, ``unprofitable_trips``,
            ``total_trips``, ``success_rate``, ``avg_profit_per_trip``,
            and ``bankrupt``.
        """
        total_trips = self.profitable_trip + self.unprofitable_trip
        return {
            "capital": self.capital,
            "wealth": self.wealth,
            "total_revenue": self.total_revenue,
            "total_costs": self.total_cost,
            "total_profit": self.total_profit,
            "total_catch": self.total_catch,
            "profitable_trips": self.profitable_trip,
            "unprofitable_trips": self.unprofitable_trip,
            "total_trips": total_trips,
            "success_rate": (
                self.profitable_trip / total_trips if total_trips > 0 else 0
            ),
            "avg_profit_per_trip": (
                self.total_profit / total_trips if total_trips > 0 else 0
            ),
            "bankrupt": self.bankrupt,
        }

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
            "current_region": self.current_region,
            "will_fish": self.will_fish,
            "region_preference": self.region_preference,
            "growth_perception": self.growth_perception,
            "memory_size": len(self.memory),
            "good_spots_count": len(self.good_spots_memory),
        }

        if self.fisher_type == "trawler":
            summary["fish_onboard"] = self.fish_onboard
            summary["storing_capacity"] = self.storing_capacity
            summary["jumped"] = self.jumped

        if self.memory:
            summary.update(self.get_memory_statistics())

        return summary

    def print_status(self) -> None:
        """Prints a compact debug summary to stdout."""
        status = "gone fishing" if self.gone_fishing else "at home"
        print(f"{status} Agent {self.unique_id} ({self.fisher_type}):")
        print(f"    Capital: {self.capital:.2f}")
        print(f"    Total catch: {self.total_catch:.0f}")
        print(f"    At home: {self.at_home}")
        print(f"    Region: {self.current_region}")
        if self.memory:
            recent = self.memory[-1]
            print(
                f"    Last trip:"
                f" catch={recent['catch']:.0f},"
                f" profit={recent['profit']:.2f}"
            )
    
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
        self.check_bankruptcy()
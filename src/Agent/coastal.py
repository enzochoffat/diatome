import statistics

from src import config


class Coastal:
    """Coastal decision model balancing lifestyle and profit."""

    def __init__(self, coastal: object) -> None:
        """Initializes the coastal agent.

        Args:
            coastal: The object representing the coastal agent.
        """
        self.coastal = coastal

    def optimise_lifestyle_and_growth(self) -> None:
        """Optimizes the fishing decision based on lifestyle and growth.

        Coastal decision model: trade-off between staying home and
        maximizing catch. Does not fish in bad weather. During the
        exploration phase, always fishes in the first accessible region.
        Afterwards, selects the region and fishing decision based on
        satisfaction levels and expected profitability.
        """
        if self.model.bad_weather:
            self.will_fish = False
            return

        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            self.will_fish = True
            self.region_preference = self.accessible_regions[0]
            return

        self.update_satisfaction()

        expected_catches = Coastal._compute_expected_catches(self)

        if expected_catches.get("A", 0) >= expected_catches.get("B", 0):
            self.region_preference = "A"
        else:
            self.region_preference = "B"

        expected_catch = expected_catches.get(
            self.region_preference, self.catchability
        )
        travel_cost = self.get_travel_cost(self.region_preference)
        expected_cost = (
            self.cost_existence + self.cost_activity + travel_cost
        )
        expected_income = expected_catch * self.model.FISH_PRICE

        expected_profit_stay = -self.cost_existence
        expected_profit_go = expected_income - expected_cost

        if self.capital < 0:
            self.will_fish = expected_profit_go > expected_profit_stay
            self.wanna_be_home = False
            return

        if expected_profit_go > expected_profit_stay:
            Coastal._decide_when_profitable(self)
        else:
            self.will_fish = False
            self.wanna_be_home = False
            self.expect_no_profit = True

    def _compute_expected_catches(self) -> dict[str, float]:
        """Computes expected catches per region based on memory.

        For each accessible region, calculates the mean of the last 30
        remembered catches. If no memory exists for a region, falls back
        to catchability as a conservative estimate.

        Returns:
            A dictionary mapping each region to its expected catch value.
        """
        expected_catches: dict[str, float] = {}
        for region in self.accessible_regions:
            region_memory = [
                trip for trip in self.memory
                if trip.get("region") == region
            ]
            if region_memory:
                expected_catches[region] = statistics.mean(
                    trip["catch"] for trip in region_memory[-30:]
                )
            else:
                expected_catches[region] = self.catchability
        return expected_catches

    def _decide_when_profitable(self) -> None:
        """Decides whether to fish based on satisfaction, when profitable.

        When going fishing is more profitable than staying home, arbitrates
        between home-time satisfaction and growth satisfaction to determine
        the final fishing decision.
        """
        home_sat = getattr(self, "satisfaction_home", 0.5)
        growth_sat = getattr(self, "satisfaction_growth", 0.5)
        threshold = self.satisfaction_home_threshold

        if growth_sat >= threshold and home_sat >= threshold:
            self.will_fish = True
            self.wanna_be_home = False
        elif home_sat < threshold:
            self.will_fish = False
            self.wanna_be_home = True
        else:
            self.will_fish = True
            self.wanna_be_home = False
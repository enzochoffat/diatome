from src import config


class Archipelago:
    """Represents an archipelago agent with configurable fishing behavior."""

    def __init__(self, agent) -> None:
        """Initialises the Archipelago with a reference to itself.

        Args:
            agent: The archipelago data or identifier passed at construction.
        """
        self.agent = agent

    def satisfice_lifestyle(self) -> None:
        """Apply the satisficing decision model for fishing behavior.

        This method implements a satisficing strategy: the agent fishes
        only when necessary to meet its basic weekly needs. During the
        exploration phase it always fishes (weather permitting). After
        that phase it evaluates recent revenue against weekly costs,
        checks for scarcity signals, and may enter a lay-low period.
        """
        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            Archipelago._handle_exploration_phase(self)
            return

        catches_last_period = Archipelago._compute_recent_catches(self)
        revenue_last_period = catches_last_period * config.FISH_PRICE
        weekly_needs = Archipelago._compute_weekly_needs(self)
        fish_is_scarce = Archipelago._assess_scarcity(self)

        if self.lay_low:
            Archipelago._tick_lay_low(self)
            return

        done_enough = revenue_last_period >= weekly_needs
        needs_money = not done_enough or self.capital < 0
        can_fish = not self.model.bad_weather

        if fish_is_scarce and self.capital >= 0:
            self.lay_low = True
            self.lay_low_counter = config.NEGATIVE_CAPITAL_LAYLOW_DAYS
            return

        self.will_fish = needs_money and can_fish

        if self.will_fish:
            self.region_preference = "A"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _handle_exploration_phase(self) -> None:
        """Set fishing intent during the initial exploration phase."""
        can_fish = not self.model.bad_weather
        self.will_fish = can_fish
        if self.will_fish:
            self.region_preference = "A"

    def _compute_recent_catches(self) -> float:
        """Sum catches over the most recent observation window.

        Returns:
            Total catch quantity across the last 5 remembered days
            (or fewer if memory is shorter). Days without fishing
            contribute 0.
        """
        last_days_count = min(len(self.memory), 5)
        recent_days = self.memory[-last_days_count:]
        return sum(day["catch"] for day in recent_days)

    def _compute_weekly_needs(self) -> float:
        """Estimate the agent's weekly financial needs.

        Returns:
            Minimum weekly revenue required to cover existence costs,
            travel costs, and activity costs.
        """
        return (
            7 * self.cost_existence
            + 5 * self.get_travel_cost("A")
            + 5 * self.cost_activity
        )

    def _assess_scarcity(self) -> bool:
        """Determine whether fish are perceived as scarce.

        Scarcity is detected when more than 75 % of recent fishing
        trips recorded catches below the agent's catchability threshold.

        Returns:
            True if scarcity conditions are met, False otherwise.
        """
        if len(self.memory) < config.SCARCITY_MIN_MEMORY:
            return False

        fishing_trips = [
            trip for trip in self.memory if trip.get("went_fishing", False)
        ]
        if len(fishing_trips) < config.SCARCITY_MIN_MEMORY:
            return False

        recent_trips = fishing_trips[-config.SCARCITY_MIN_MEMORY:]
        low_catch_count = sum(
            1 for trip in recent_trips if trip["catch"] < self.catchability
        )
        return low_catch_count > 0.75 * self.max_good_spots

    def _tick_lay_low(self) -> None:
        """Decrement the lay-low counter and clear the flag when expired."""
        self.lay_low_counter -= 1
        if self.lay_low_counter <= 0:
            self.lay_low = False
        self.will_fish = False
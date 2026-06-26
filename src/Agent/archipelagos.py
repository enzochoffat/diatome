import logging

from src import config

logger = logging.getLogger(__name__)

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


        logger.debug(
                    "Archipelago decision start",
                    extra={
                        "agent_id": getattr(self, "unique_id", None),
                        "capital": self.capital,
                        "memory_size": len(self.memory),
                        "lay_low": self.lay_low,
                    },
                )


        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            logger.debug(
                "Exploration phase",
                extra={"agent_id": getattr(self, "unique_id", None)},
            )

            Archipelago._handle_exploration_phase(self)
            return

        catches_last_period = Archipelago._compute_recent_catches(self)
        revenue_last_period = catches_last_period * config.FISH_PRICE
        weekly_needs = Archipelago._compute_weekly_needs(self)


        logger.debug(
            "Recent performance",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "recent_catches": catches_last_period,
                "recent_revenue": revenue_last_period,
                "weekly_needs": weekly_needs,
            },
        )
        
        fish_is_scarce = Archipelago._assess_scarcity(self)


        logger.debug(
            "Scarcity assessment",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "scarcity": fish_is_scarce,
            },
        )


        if self.lay_low:

            logger.info(
                "Agent in lay-low phase",
                extra={
                    "agent_id": getattr(self, "unique_id", None),
                    "remaining_days": self.lay_low_counter,
                },
            )

            Archipelago._tick_lay_low(self)
            return

        done_enough = revenue_last_period >= weekly_needs
        needs_money = not done_enough or self.capital < 0
        can_fish = not self.model.bad_weather


        logger.debug(
            "Satisficing evaluation",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "done_enough": done_enough,
                "needs_money": needs_money,
                "can_fish": can_fish,
            },
        )


        if fish_is_scarce and self.capital >= 0:

            logger.warning(
                "Entering lay-low due to perceived scarcity",
                extra={
                    "agent_id": getattr(self, "unique_id", None),
                    "capital": self.capital,
                },
            )

            self.lay_low = True
            self.lay_low_counter = config.NEGATIVE_CAPITAL_LAYLOW_DAYS
            return

        self.will_fish = needs_money and can_fish

        if self.will_fish:
            self.region_preference = "A"
        

        logger.info(
            "Archipelago decision",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "will_fish": self.will_fish,
                "reason": "needs_money" if needs_money else "enough_resources",
                "weather_ok": can_fish,
            },
        )


    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _handle_exploration_phase(self) -> None:
        """Set fishing intent during the initial exploration phase."""
        can_fish = not self.model.bad_weather

        logger.debug(
            "Exploration phase decision",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "can_fish": can_fish,
            },
        )

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

        total = sum(day["catch"] for day in recent_days)

        logger.debug(
            "Recent catches computed",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "days": last_days_count,
                "total": total,
            },
        )

        return total

    def _compute_weekly_needs(self) -> float:
        """Estimate the agent's weekly financial needs.

        Returns:
            Minimum weekly revenue required to cover existence costs,
            travel costs, and activity costs.
        """
        needs = (
            7 * self.cost_existence
            + 5 * self.get_travel_cost("A")
            + 5 * self.cost_activity
        )

        logger.debug(
            "Weekly needs computed",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "needs": needs,
            },
        )

        return needs
    

    def _assess_scarcity(self) -> bool:
        """Determine whether fish are perceived as scarce.

        Scarcity is detected when more than 75 % of recent fishing
        trips recorded catches below the agent's catchability threshold.

        Returns:
            True if scarcity conditions are met, False otherwise.
        """
        if len(self.memory) < config.SCARCITY_MIN_MEMORY:
            logger.debug(
                "Scarcity skipped (not enough memory)",
                extra={"agent_id": getattr(self, "unique_id", None)},
            )

            return False

        fishing_trips = [
            trip for trip in self.memory if trip.get("went_fishing", False)
        ]
        if len(fishing_trips) < config.SCARCITY_MIN_MEMORY:
            logger.debug(
                "Scarcity skipped (not enough fishing trips)",
                extra={"agent_id": getattr(self, "unique_id", None)},
            )
            return False

        recent_trips = fishing_trips[-config.SCARCITY_MIN_MEMORY:]
        low_catch_count = sum(
            1 for trip in recent_trips if trip["catch"] < self.catchability
        )
        return low_catch_count > 0.75 * self.max_good_spots

    def _tick_lay_low(self) -> None:
        """Decrement the lay-low counter and clear the flag when expired."""
        self.lay_low_counter -= 1

        logger.debug(
            "Lay-low counter decremented",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "remaining_days": self.lay_low_counter,
            },
        )

        if self.lay_low_counter <= 0:
            logger.info(
                "Lay-low period ended",
                extra={"agent_id": getattr(self, "unique_id", None)},
            )
            self.lay_low = False
        self.will_fish = False
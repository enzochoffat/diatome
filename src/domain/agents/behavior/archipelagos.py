import logging

from src import config
from src.core.config import get_fisher_config
from src.domain.environment.weather import get_wave_height

logger = logging.getLogger(__name__)


class Archipelagos:
    """Represents an archipelago agent with configurable fishing behavior."""

    def __init__(self, agent) -> None:
        self.agent = agent

    def satisfice_lifestyle(self) -> None:
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
            Archipelagos._handle_exploration_phase(self)
            return

        fish_is_scarce = Archipelagos._assess_scarcity(self)

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
            Archipelagos._tick_lay_low(self)
            return

        date, wave_height = get_wave_height(self.model)
        max_heigth = get_fisher_config(fisher_type="archipelago")["wave_height_threshold"]
        if wave_height > max_heigth:
            logger.debug(
                "Decision blocked by wave height",
                extra={
                    "agent_id": getattr(self, "unique_id", None),
                    "wave_height": wave_height,
                    "threshold": max_heigth,
                },
            )
            self.will_fish = False
            return

        days_in_weekly_window = min(len(self.memory), config.MEMORY_WEEKLY_WINDOW)
        recent_days = self.memory[-days_in_weekly_window:]
        fishing_days = sum(1 for t in recent_days if t.get("went_fishing", False))
        avg_daily_revenue = sum(t.get("revenue", 0.0) for t in recent_days) / max(days_in_weekly_window, 1)
        daily_cost = self.cost_existence + self.cost_activity
        needs_fishing = fishing_days < 4 or avg_daily_revenue < daily_cost or self.capital < 0
        can_fish = not self.model.bad_weather

        if fish_is_scarce and self.capital >= self.cost_existence * 30:
            self.lay_low = True
            self.lay_low_counter = config.NEGATIVE_CAPITAL_LAYLOW_DAYS
            return

        self.will_fish = needs_fishing and can_fish

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _handle_exploration_phase(self) -> None:
        can_fish = not self.model.bad_weather
        logger.debug(
            "Exploration phase decision",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "can_fish": can_fish,
            },
        )
        self.will_fish = can_fish

    def _compute_recent_revenue(self) -> float:
        last_days_count = min(len(self.memory), 5)
        recent_days = self.memory[-last_days_count:]

        total = sum(day.get("revenue", 0.0) for day in recent_days)

        logger.debug(
            "Recent revenues computed",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "days": last_days_count,
                "total": total,
            },
        )

        return total

    def _compute_weekly_needs(self) -> float:
        needs = (
            7 * self.cost_existence
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

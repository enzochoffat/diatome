import logging

from src import config
from src.core.config import get_fisher_config
from src.domain.environment.weather import get_wave_height

logger = logging.getLogger(__name__)


class Coastal:
    """Coastal decision model balancing lifestyle and profit."""

    def __init__(self, coastal: object) -> None:
        self.coastal = coastal

    def optimise_lifestyle_and_growth(self) -> None:
        logger.debug(
            "Coastal decision start",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "capital": getattr(self, "capital", None),
                "memory_size": len(self.memory) if hasattr(self, "memory") else None,
            }
        )

        if self.model.bad_weather:
            logger.debug(
                "Decision blocked by weather",
                extra={"agent_id": getattr(self, "unique_id", None)},
            )
            self.will_fish = False
            return

        date, wave_height = get_wave_height(self.model)
        max_heigth = get_fisher_config(fisher_type="coastal")["wave_height_threshold"]
        if wave_height > max_heigth:
            logger.debug(
                "Decision blocked by wave height",
                extra={
                    "agent_id": getattr(self, "unique_id", None),
                    "wave_height": wave_height,
                    "threshold": max_heigth,
                }
            )
            self.will_fish = False
            return

        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            self.will_fish = True
            return

        self.update_satisfaction()

        expected_revenue = self.expected_revenue
        expected_cost = self.cost_existence + self.cost_activity

        logger.debug(
            "Economic estimation",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "expected_revenue": expected_revenue,
                "expected_cost": expected_cost,
            }
        )

        expected_profit_stay = -self.cost_existence
        expected_profit_go = expected_revenue - expected_cost

        logger.debug(
            "Profit comparison",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "expected_profit_go": expected_profit_go,
                "expected_profit_stay": expected_profit_stay,
            }
        )

        if expected_profit_go > expected_profit_stay:
            self.will_fish = True
        else:
            self.will_fish = False

        logger.debug(
            "Decision final",
            extra={
                "agent_id": getattr(self, "unique_id", None),
                "will_fish": self.will_fish,
            }
        )

"""Trawler agent decision module for fishing simulation."""

from src import config
from src.core.config import get_fisher_config
from src.domain.environment.weather import get_wave_height


class Trawler:
    """Represents a fishing trawler agent in the simulation."""

    def __init__(self, trawler) -> None:
        self.trawler = trawler

    def optimise_growth(self) -> None:
        date, wave_height = get_wave_height(self.model)
        max_wave_height = get_fisher_config(fisher_type="trawler")["wave_height_threshold"]
        if wave_height > max_wave_height:
            self.will_fish = False
            return

        if self.gone_fishing:
            Trawler._decide_while_at_sea(self)
            return

        expected_cost = self.cost_activity + self.cost_existence
        expected_profit_go = self.expected_revenue - expected_cost
        expected_profit_stay = -self.cost_existence

        self.will_fish = expected_profit_go > expected_profit_stay
        if self.will_fish:
            self.fish_onboard = 0
            self.days_at_sea_current_trip = 0
            self.jumped = False

    def _decide_while_at_sea(self) -> None:
        if self.fish_onboard >= self.storing_capacity:
            self.will_fish = False
            self.land_fish()
            return

        fish_wish = self.storing_capacity - self.fish_onboard

        vicinity_value = 0
        if self.current_location:
            vicinity_value = self.model.get_vicinity_value(
                self.current_location[0], self.current_location[1],
                self.fisher_type, radius=1
            )

        expected_cost = self.cost_activity + self.cost_existence
        expected_revenue = (
            vicinity_value
            if vicinity_value >= self.expected_revenue * (fish_wish / max(self.storing_capacity, 1))
            else self.expected_revenue
        )
        expected_profit_go = expected_revenue - expected_cost
        expected_profit_stay = -self.cost_existence

        if expected_profit_go > expected_profit_stay:
            self.will_fish = True
        else:
            self.will_fish = False
            self.land_fish()

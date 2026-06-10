import random

from src import config

class Trawler:
    def __init__(self, trawler):
        self.trawler = trawler

    def _is_beginning_season(self):
        """
        NetLogo equivalent of beginning-season:
        True during first month of the current year.
        """
        first_month_of_year = self.model.current_step % self.model.YEAR
        return first_month_of_year < self.model.MONTH
        
    def optimise_growth(self):
        """
        Trawler decision model aligned with NetLogo timing:
        - At home: memory-based expectations only after first week
        and outside beginning-season.
        - Otherwise: random exploration over B/C/D.
        - At sea: use _decide_while_at_sea().
        """
        if self.gone_fishing:
            Trawler._decide_while_at_sea(self)
            return

        # Not at sea (NetLogo branch: not(goneFishing))
        use_memory_expectations = (
            (self.model.current_step > self.model.WEEK)
            and (not Trawler._is_beginning_season(self))
        )

        if use_memory_expectations:
            Trawler._decide_while_at_home(self)
        else:
            # NetLogo random region choice at beginning of run/year
            self.region_preference = random.choice(self.accessible_regions)

            expected_catch = self.catchability
            expected_income = expected_catch * config.FISH_PRICE
            expected_cost = (
                self.cost_activity
                + self.cost_existence
                + self.get_travel_cost(self.region_preference)
            )

            expected_profit_go = expected_income - expected_cost
            expected_profit_stay = -self.cost_existence

            self.will_fish = expected_profit_go > expected_profit_stay
            if self.will_fish:
                self.fish_onboard = 0
                self.days_at_sea_current_trip = 0
                self.jumped = False

    def _decide_while_at_sea(self):
        """Decision logic when trawler is already at sea (NetLogo-aligned)."""
        current_region = self.current_region if self.current_region else self.region_preference
        fish_wish = self.storing_capacity - self.fish_onboard

        # NetLogo: fish at current patch + patches in radius 1
        fish_vicinity = 0
        if self.current_location:
            patch = self.model.get_patch_info(*self.current_location)
            fish_vicinity = patch['fish_stock'] if patch else 0

            neighbors = self.get_neighbor_positions_in_radius(self.current_location, radius=1)
            for neighbor_pos in neighbors:
                neighbor_patch = self.model.get_patch_info(*neighbor_pos)
                if neighbor_patch and neighbor_patch['region'] == current_region:
                    fish_vicinity += neighbor_patch['fish_stock']

        expected_travel_cost = 0

        # NetLogo branch 1: enough fish nearby
        if fish_vicinity >= fish_wish:
            expected_catch = fish_wish
            self.region_preference = current_region

        else:
            # Compute expected catches in other regions from memory
            other_regions = [r for r in self.accessible_regions if r != current_region]
            expected_catches = {}
            travel_costs = {}

            for region in other_regions:
                expected_catches[region] = self._estimate_catch(region)
                travel_costs[region] = self.get_travel_cost_between_regions(current_region, region)

            # NetLogo equivalent:
            # if max(expected catches) < fishWish:
            #   expected-catch = fishVicinity
            #   expected-travel-cost = getTravelCost(currentRegion)/2
            #   regionPref = currentRegion
            best_expected_other = max(expected_catches.values()) if expected_catches else 0

            if best_expected_other < fish_wish:
                expected_catch = fish_vicinity
                expected_travel_cost = self.get_travel_cost(current_region) / 2
                self.region_preference = current_region

            else:
                # NetLogo equivalent:
                # expected-catch = fishWish, then choose region via expected travel cost/profit tradeoff
                expected_catch = fish_wish

                best_switch_profit = float('-inf')
                best_switch_region = None

                for region in other_regions:
                    revenue = expected_catches[region] * config.FISH_PRICE
                    profit = revenue - self.cost_activity - travel_costs[region]
                    if profit > best_switch_profit:
                        best_switch_profit = profit
                        best_switch_region = region

                stay_profit = fish_vicinity * config.FISH_PRICE - self.cost_activity

                if best_switch_region is not None and best_switch_profit > stay_profit:
                    self.region_preference = best_switch_region
                    expected_travel_cost = travel_costs[best_switch_region]
                    self.jumped = True
                else:
                    self.region_preference = current_region
                    expected_travel_cost = self.get_travel_cost(current_region) / 2

        expected_cost = self.cost_activity + self.cost_existence + expected_travel_cost
        expected_income = expected_catch * config.FISH_PRICE
        expected_profit_go = expected_income - expected_cost
        expected_profit_stay = -self.cost_existence

        if expected_profit_go > expected_profit_stay:
            self.will_fish = True
        else:
            self.will_fish = False
            self.land_fish()
        

    def _decide_while_at_home(self):
        """Decision logic when trawler is at home"""
        # Use cascade comparison instead of simple max
        best_region = self._calculate_region_preference()

        # Still check profitability
        expected_catch = self._estimate_catch(best_region)
        travel_cost = self.get_travel_cost(best_region)
        total_cost = self.cost_existence + self.cost_activity + travel_cost
        expected_revenue = expected_catch * config.FISH_PRICE
        expected_profit = expected_revenue - total_cost

        expected_profit_stay = -self.cost_existence

        if expected_profit > expected_profit_stay:
            self.will_fish = True
            self.region_preference = best_region
            self.fish_onboard = 0
            self.days_at_sea_current_trip = 0
            self.jumped = False
        else:
            self.will_fish = False
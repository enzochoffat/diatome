import statistics

from src import config

class Coastal:
    def __init__(self, coastal):
        self.coastal = coastal

    def optimise_lifestyle_and_growth(self):
        """
        Coastal decision model: Balance between lifestyle and profit
        Trade-off between staying home and maximizing catch
        """
        if self.model.bad_weather:
            self.will_fish = False
            return
        
        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            self.will_fish = True
            self.region_preference = self.accessible_regions[0]
            return
        
        self.update_satisfaction()
        
        # Calculate expected catches per region
        expected_catches = {}
        for region in self.accessible_regions:
            region_memory = [trip for trip in self.memory if trip.get('region') == region]
            if region_memory:
                expected_catches[region] = statistics.mean(t['catch'] for t in region_memory[-30:])
            else:
                # Conservative estimate if no memory for this region
                expected_catches[region] = self.catchability
        
        if expected_catches.get("A", 0) >= expected_catches.get("B", 0):
            self.region_preference = "A"
        else:
            self.region_preference = "B"
            
        expected_catch = expected_catches.get(self.region_preference, self.catchability)
        travel_cost = self.get_travel_cost(self.region_preference)
        expected_cost = self.cost_existence + self.cost_activity + travel_cost
        expected_income = expected_catch * self.model.FISH_PRICE
        
        expected_profit_stay = -self.cost_existence
        expected_profit_go = expected_income - expected_cost
        
        if self.capital < 0:
            self.will_fish = expected_profit_go > expected_profit_stay
            self.wanna_be_home = False
            return
        
        if expected_profit_go > expected_profit_stay:
            home_sat = getattr(self, 'homeTime_satisfaction', 0.5)
            growth_sat = getattr(self, 'growth_satisfaction', 0.5)
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
        else:
            self.will_fish = False
            self.wanna_be_home = False
            self.expect_no_profit = True
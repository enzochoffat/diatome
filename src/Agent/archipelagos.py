from src import config

class Archipelagos:
    def __init__(self, archipelagos):
        self.archipelagos = archipelagos

    def satisfice_lifestyle(self):
        """
        Archipelago decision model: Satisficing behavior
        Fish only when necessary to meet basic needs
        """
        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            can_fish = not self.model.bad_weather
            self.will_fish = can_fish
            #if self.model.current_step < 5:
                #print(f"[Day {self.model.current_step}] Archipelago #{self.unique_id} EXPLORATION: "
                #   f"will_fish={self.will_fish}, bad_weather={self.model.bad_weather}")
            if self.will_fish:
                self.region_preference = "A"
            return
        
        # Calculate catches from last week
        last_days_count = min(len(self.memory), 5)
        recent_days = self.memory[-last_days_count:]  # Tous les jours (fishing ou non)
        
        # Somme des captures sur ces jours (0 si pas de pêche)
        catches_last_period = sum(day['catch'] for day in recent_days)
        revenue_last_period = catches_last_period * config.FISH_PRICE
        
        # Calculate weekly needs
        weekly_needs = (7 * self.cost_existence +
                        5 * self.get_travel_cost('A') +
                        5 * self.cost_activity)
        
        #if self.model.current_step < 30:
        #    print(f"[Day {self.model.current_step}] Archipelago #{self.unique_id} POST-EXPLORATION:")
        #    print(f"  Last {last_days_count} days catches: {[t['catch'] for t in recent_days]}")
        #    print(f"  Revenue: {revenue_last_period:.2f} SEK")
        #    print(f"  Weekly needs: {weekly_needs:.2f} SEK")
        #    print(f"  Done enough: {revenue_last_period >= weekly_needs}")
            
        # Scarcity perception (basé sur les trips de pêche uniquement)
        if len(self.memory) >= config.SCARCITY_MIN_MEMORY:
            fishing_trips = [t for t in self.memory if t.get('went_fishing', False)]
            if len(fishing_trips) >= config.SCARCITY_MIN_MEMORY:
                low_catch_count = sum(1 for t in fishing_trips[-config.SCARCITY_MIN_MEMORY:]
                                    if t['catch'] < self.catchability)
                fish_is_scarce = low_catch_count > 0.75 * self.max_good_spots
            else:
                fish_is_scarce = False
        else:
            fish_is_scarce = False
            
        if self.lay_low:
            self.lay_low_counter -= 1
            if self.lay_low_counter <= 0:
                self.lay_low = False
            self.will_fish = False
            return
        
        done_enough = revenue_last_period >= weekly_needs
        needs_money = not done_enough or self.capital < 0
        can_fish = not self.model.bad_weather
        
        if fish_is_scarce and not (self.capital < 0):
            #self.will_fish = False
            self.lay_low = True
            self.lay_low_counter = config.NEGATIVE_CAPITAL_LAYLOW_DAYS
            return
        
        self.will_fish = needs_money and can_fish
        
        
        if self.will_fish:
            self.region_preference = "A"
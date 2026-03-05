from mesa import Agent
from . import config
import random
import statistics
from collections import Counter


class FisherAgent(Agent):
    
    def __init__(self, unique_id, model, fisher_type):
        super().__init__(model)
        self.fisher_type = fisher_type # "archipelago", "coastal", "trawler"
        self.unique_id = unique_id
        
        # Basic attributes
        self.wealth = 0
        self.capital = config.INITIAL_CAPITAL
        self.age = random.randint(config.MIN_AGE, config.MAX_AGE)
        self.days_at_sea = 0
        self.total_catch = 0
        self.total_profit = 0
        self.total_cost = 0
        self.total_revenue = 0
        self.yearly_catch = 0
        self.yearly_profit = 0
        
        # Economic 
        self.bankrupt = False
        self.years_active = 0
        self.profitable_trip = 0
        self.unprofitable_trip = 0
        
        # Trip tracking
        self.accumulated_catch = 0
        self.trip_cost = 0
        self.days_in_current_trip = 0
        self.days_at_sea_current_trip = 0
        
        
        # Decision variable
        self.current_location = None
        self.target_location = None
        self.current_region = None
        self.at_home = True
        self.at_sea = False
        self.gone_fishing = False
        self.lay_low = False
        self.lay_low_counter = 0
        
        # Decision-making attributes
        self.region_preference = None
        self.spot_selection_strategy = "knowledge"
        
        # Perception 
        self.growth_perception = 0.0  # Perception croissance poissons
        
        # Type-specific attribute
        self._set_type_attributes()
        
        # Memory system
        self.memory_size = config.DEFAULT_MEMORY_SIZE
        self.memory = []
        
        # Spatial memory
        self.good_spots_memory = {} # {(x,y): {'visits': n, 'avg_catch': x, 'last_visit': tick}}
        self.good_spots_threshold = config.GOOD_SPOT_EFFICIENCY_THRESHOLD
        
        # Decision-making attributes
        self.will_fish = False
        self.region_preference = None
        self.spot_selection_strategy = "knowledge"      
        
        # Threshold
        self.satisfaction_home_threshold = config.SATISFACTION_HOME_THRESHOLD
        self.satisfaction_growth_threshold = config.SATISFACTION_GROWTH_THRESHOLD
        self.scarce_perception_threshold = config.SCARCE_PERCEPTION_THRESHOLD
        
        # Trawler specific
        self.fish_onboard = 0
        self.storing_capacity = config.TRAWLER_STORAGE_CAPACITY if fisher_type == "trawler" else 0
        self.jumped = False # Changed region while at sea  
        
        # interface
        self.display_location = None
        
    def _set_type_attributes(self):
        """Set attributes specific to fisher type"""
        if self.fisher_type == "archipelago":
            self.cost_existence = self.model.LOW_COST_EXISTENCE
            self.cost_activity = self.model.LOW_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_ARCHEPELAGO
            self.accessible_regions = ["A"]
            self.lifestyle_preference = "high"
            self.max_good_spots = 5
            
        elif self.fisher_type == "coastal":
            self.cost_existence = self.model.MEDIUM_COST_EXISTENCE
            self.cost_activity = self.model.MEDIUM_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_COASTAL
            self.accessible_regions = ["B"]
            self.lifestyle_preference = "medium"
            self.max_good_spots = 3
            self.wanna_be_home = False
            
        elif self.fisher_type == "trawler":
            self.cost_existence = self.model.HIGH_COST_EXISTENCE
            self.cost_activity = self.model.HIGH_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_TRAWLER
            self.accessible_regions = ["C", "D"]
            self.lifestyle_preference = "low"
            self.max_good_spots = 2
            
    def update_memory(self, trip_info):
        """
        Update temporal memory with new fishing trip information
        
        Args:
            trip_info (dict): Dictionary containing:
                - 'location': (x,y) tupple
                - 'catch': amount caught
                - 'cost': total cost of trip
                - 'profit': net profit
                - 'days': days spent fishing
                - 'tick': model tick when trip occurred                              
        """
        
        # Add new trip to memory
        self.memory.append(trip_info)
        
        # Keep only the last N trip
        if len(self.memory) > self.memory_size:
            self.memory.pop(0)
    
    def update_memory_good_spots(self, location, catch, expected_catch):
        """
        Update spatial memory of good fishing spots.
        
        Args:
            location (tuple): (x, y) coordonates
            catch (float): Actual catch at this location
            expected_catch (float): Expected catch based on effort
        """
        # Calculate catch efficiency
        if expected_catch > 0:
            catch_efficiency = catch / expected_catch
        else:
            catch_efficiency = 0
            
        # Update or create spot memory
        if location in self.good_spots_memory:
            spot = self.good_spots_memory[location]
            total_visits = spot['visits']
            spot['avg_catch'] = (spot['avg_catch'] * total_visits + catch) / (total_visits + 1)
            spot['visits'] += 1
            spot['last_visit'] = self.model.current_step
            spot['efficiency'] = catch_efficiency
        else:
            self.good_spots_memory[location] = {
                'avg_catch': catch,
                'visits': 1,
                'last_visit': self.model.current_step,
                'efficiency': catch_efficiency
            }
        
        # Mark as "good" if efficiency exceeds threshold
        if catch_efficiency >= self.good_spots_threshold:
            self.good_spots_memory[location]['is_good'] = True
        else:
            self.good_spots_memory[location]['is_good'] = False
            
    def get_good_spots(self, region=None, min_visits=1):
        """
        Get list of remembered good fishing spots.
    
        Args:
            region (str): Filter by region (optional)
            min_visits (int): Minimum number of visits to consider
        
        Returns:
            list: List of (location, memory_info) tuples sorted by avg_catch
        """
        good_spots = []
        
        for location, memory in self.good_spots_memory.items():
            if memory['visits'] < min_visits:
                continue
            if not memory.get('is_good', False):
                continue
            if region:
                patch = self.model.get_patch_info(location[0], location[1])
                if patch and patch['region'] != region:
                    continue
                
            good_spots.append((location, memory))
            
        good_spots.sort(key=lambda x: x[1]['avg_catch'], reverse=True)
        
        return good_spots
    
    def get_memory_statistics(self):
        """
        Calculate statistics from memory
        
        Returns:
            dict: Memory-based statistics
        """
        
        if not self.memory:
            return {
                'avg_profit': 0,
                'avg_catch': 0,
                'avg_cost': 0,
                'success_rate': 0,
                'recent_trend': 0
            }
            
        catches = [t['catch'] for t in self.memory]
        profits = [t['profit'] for t in self.memory]
        costs = [t['cost'] for t in self.memory]
        
        fishing_trips = [t for t in self.memory if t.get('went_fishing', True)]
        if fishing_trips:
            profitable = sum(1 for t in fishing_trips if t['profit'] > 0)
            success_rate = profitable / len(fishing_trips)
        else:
            success_rate = 0
        
        trend = 0
        
        if len(profits) >= 14:
            recent_avg = statistics.mean(profits[-7:])
            older_avg = statistics.mean(profits[-14:-7])
            if older_avg != 0:
                trend = (recent_avg - older_avg) / abs(older_avg)
            else:
                trend = 0
        
        return {
            'avg_catch': statistics.mean(catches),
            'median_catch': statistics.median(catches),
            'avg_profit': statistics.mean(profits),
            'median_profit': statistics.median(profits),
            'avg_cost': statistics.mean(costs),
            'success_rate': success_rate,
            'recent_trend': trend,
            'total_trips': len(self.memory)
        }
        
    def get_regional_memory_stats(self, region):
        """
        Get memory statistics for a specific region
        
        Args:
            region: Region name (A, B, C, or D)
            
        Returns:
            dict: Regional statistics
        """
        regional_trips = [t for t in self.memory if t.get('region') == region]
        
        if not regional_trips:
            return {
                'trip': 0,
                'avg_catch': 0,
                'avg_profit': 0,
                'last_visit': None
            }
            
        return {
            'trip': len(regional_trips),
            'avg_catch': statistics.mean(t['catch'] for t in regional_trips),
            'avg_profit': statistics.mean(t['profit'] for t in regional_trips),
            'last_visit': regional_trips[-1]['tick']
        }
                
    def forget_old_spots(self, max_age_ticks):
        """
        Remove spots from spatial memory that haven't been visited recently.
        
        Args:
            max_age_ticks (int): Maximum age in ticks before forgetting
        """
        current_tick = self.model.current_step
        location_to_remove = []
        
        for location, memory in self.good_spots_memory.items():
            age = current_tick - memory['last_visit']
            if age > max_age_ticks:
                location_to_remove.append(location)
        
        for location in location_to_remove:
            del self.good_spots_memory[location]
    
    def move_to(self, x, y):
        """
        Move agent to a specific location on the grid
        
        Args:
            x, y: Target coordinates
        """
        
        # Remove from current position if exists
        if self.current_location:
            self.model.grid.remove_agent(self)
        
        # Place at new position
        self.model.grid.place_agent(self, (x, y))
        self.current_location = (x, y)
        self.display_location = (x, y)
        
    def calculate_travel_cost(self, from_pos, to_pos):
        """
        Calculate travel cost between two positions.
        For now, simple distance-based cost.
        
        Args:
            from_pos: (x, y) starting position
            to_pos: (x, y) destination position
            
        Returns:
            float: Travel cost
        """
        if from_pos is None or to_pos is None:
            return 0
        
        # Euclidean distance
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        distance = (dx**2 + dy**2)**0.5
        
        return distance * config.TRAVEL_COST_PER_UNIT
    
    def go_fish(self, location):
        """
        Execute fishing at a specific location (single day trip for archipelago).
        
        Args:
            location: (x, y) tuple of fishing spot
            
        Returns:
            dict: Trip results with catch, costs, profit
        """
        # Get patch info
        patch = self.model.get_patch_info(location[0], location[1])
        
        if not patch:
            return {
                'catch': 0,
                'costs': 0,
                'profit': 0,
                'revenue': 0,
                'location': location
            }
        
        # Calculate potential catch (min of catchability and available stock)
        available_stock = patch['fish_stock']
        potential_catch = min(self.catchability, available_stock)
        
        # Reduce stock in the model
        actual_catch = self.model.reduce_stock(location[0], location[1], potential_catch)
        
        current_region = patch['region']
        
        if self.fisher_type == "archipelago":
            self.cost_existence = self.model.LOW_COST_EXISTENCE
            travel_cost = self.get_travel_cost(current_region)
            
        elif self.fisher_type == "coastal":
            self.cost_existence = self.model.MEDIUM_COST_EXISTENCE
            travel_cost = self.get_travel_cost(current_region)
            
        elif self.fisher_type == "trawler":
            if not self.gone_fishing:
                travel_cost = self.get_travel_cost(current_region)
            else:
                if self.jumped:
                    travel_cost = self.get_travel_cost(current_region) / 2
                    self.jumped = False
                else:
                    travel_cost = 0
                    
            if self.fish_onboard + actual_catch >= self.storing_capacity:
                self.gone_fishing = False
            elif self.gone_fishing:
                self.gone_fishing = True
            else:
                self.gone_fishing = True
        
        else:
            travel_cost = 0
        
        total_cost = self.cost_existence + self.cost_activity + travel_cost
        
        profit_calc = self.calculate_profit(actual_catch, total_cost)
        
        if profit_calc['profit'] > 0:
            self.profitable_trip += 1
        else:
            self.unprofitable_trip += 1
        
        # === DEBUG (first year only) ===
     #   if self.model.current_step < 365 and self.model.current_step % 30 == 0:
     #       print(f"[{self.fisher_type} #{self.unique_id}] Catch={actual_catch}, "
     #           f"Profit={profit_calc['profit']:.2f}, "
     #           f"Cost={total_cost:.2f}, Revenue={profit_calc['revenue']:.2f}")
        
        self.update_finances(
            profit_calc['profit'],
            profit_calc['costs'],
            profit_calc['revenue'],
            is_trip=True
        )
        
        self.accumulated_catch += actual_catch
        self.days_at_sea += 1
        
        if self.fisher_type == "trawler":
            self.fish_onboard += actual_catch
            
        expected_catch = self.catchability
        self.update_memory_good_spots(location, actual_catch, expected_catch)
        
      #  if self.model.current_step < 10:
      #      print(f"[Day {self.model.current_step}] {self.fisher_type} #{self.unique_id} fishing:")
      #      print(f"  Location: {location}, Region: {current_region}")
      #      print(f"  Catch: {actual_catch} / {potential_catch}")
      #      print(f"  Costs: existence={self.cost_existence}, activity={self.cost_activity}, travel={travel_cost}")
      #      print(f"  Total cost: {total_cost:.2f}, Revenue: {profit_calc['revenue']:.2f}, Profit: {profit_calc['profit']:.2f}")
            
        return profit_calc
        
    def select_fishing_spot(self, region=None):
        """
        Select a fishing spot based on memory (knowledge-based).
        For archipelago: simple selection from good spots.
        
        Args:
            region: Region to fish in (default: first accessible region)
            
        Returns:
            (x, y) tuple or None
        """
        
        if region is None:
            region = self.accessible_regions[0] if self.accessible_regions else None
            
        if not region:
            return None
        
        # Get good spots from memory
        good_spots = self.get_good_spots(region=region, min_visits=1)
        
        if good_spots:
            # Choose randomly among good spots
            spot, memory = random.choice(good_spots)
            return spot
        else:
            if self.model.current_step < 10:
                print(f"    Archipelago #{self.unique_id} EXPLORING (no good spots in memory)")
            # Exploration
            spot = self.explore_random_spot(region)
            
            # DEBUG
            if self.model.current_step < 10:
                print(f"    → Exploration returned: {spot}")
            return spot

            
        
   
    def explore_random_spot(self, region):
        if region == "A":
            hotspots = self.model.HOTSPOTS_A
        elif region == "B":
            hotspots = self.model.HOTSPOTS_B
        elif region == "C":
            hotspots = self.model.HOTSPOTS_C
        elif region == "D":
            hotspots = self.model.HOTSPOTS_D
        else:
            return None

        if not hotspots:
            return None

        # Choisir un hotspot de base
        base_spot = random.choice(hotspots)
        
        # Explorer autour avec un rayon aléatoire
        exploration_radius = 3
        attempts = 10
        
        for _ in range(attempts):
            dx = random.randint(-exploration_radius, exploration_radius)
            dy = random.randint(-exploration_radius, exploration_radius)
            
            candidate = (base_spot[0] + dx, base_spot[1] + dy)
            
            # Vérifier que le patch est dans la bonne région
            patch = self.model.get_patch_info(candidate[0], candidate[1])
            if patch and patch['region'] == region:
                return candidate
        
        # Fallback : retourner le centre du hotspot
        return tuple(base_spot)
    
    def execute_decision(self):
        """
        Execute the agent's fishing decision (NetLogo-aligned)
        """
        if self.bankrupt:
            self.lay_low = True
            self.will_fish = False
            self.stay_home(pay_existence_cost=True)
            return
        
        if self.lay_low:
            if hasattr(self, 'has_partner') and self.has_partner:
                existence_cost = 0.5 * self.cost_existence
            else:
                existence_cost = 0.25 * self.cost_existence
            
            self.update_finances(
                profit=-existence_cost,
                cost=existence_cost,
                revenue=0,
                is_trip=False
            )
            self.stay_home_state_only()  # Update state without paying again
            return
        
        if self.will_fish:
            target_region = self.region_preference if self.region_preference else self.accessible_regions[0]
            target_spot = self.select_fishing_spot(region=target_region)
            
            if target_spot:
                estimated_cost = self.estimate_trip_cost(target_spot)
                
                if not self.can_afford_trip(estimated_cost):
                    self.stay_home(pay_existence_cost=True)
                    return
                
                self.at_home = False
                self.gone_fishing = True
                
                # Go fishing
                self.move_to(target_spot[0], target_spot[1])
                trip_result = self.go_fish(target_spot)
                
                # DEBUG: Résultat du trip
               # if self.model.current_step < 100:
                #    print(f"    → Catch={trip_result['catch']}, Profit={trip_result['profit']:.2f}, Memory size now={len(self.memory)}")
        
                
                # Memory
                trip_info = {
                    'location': target_spot,
                    'catch': trip_result['catch'],
                    'cost': trip_result['costs'],
                    'profit': trip_result['profit'],
                    'days': 1,
                    'tick': self.model.current_step,
                    'region': target_region,
                    'went_fishing': True
                }
                self.update_memory(trip_info)
                
                # Return home (unless trawler multi-day)
                if not (self.fisher_type == "trawler" and self.gone_fishing):
                    self.return_home()
            else:
                self.stay_home(pay_existence_cost=True)
        else:
            self.stay_home(pay_existence_cost=True)

    def stay_home_state_only(self):
        """Update state without financial transaction"""
        self.at_home = True
        self.gone_fishing = False
        self.at_sea = False
        self.will_fish = False
            
    def get_financial_summary(self):
        """
        Get summary of agent's financial state.
        
        Returns:
            dict: Financial statistics
        """
        total_trips = self.profitable_trip + self.unprofitable_trip
        
        return {
            'capital': self.capital,
            'wealth': self.wealth,
            'total_revenue': self.total_revenue,
            'total_costs': self.total_cost,
            'total_profit': self.total_profit,
            'total_catch': self.total_catch,
            'profitable_trips': self.profitable_trip,
            'unprofitable_trips': self.unprofitable_trip,
            'total_tripd': total_trips,
            'success_rate': self.profitable_trip / total_trips if total_trips > 0 else 0,
            'avg_profit_per_trip': self.total_profit / total_trips if total_trips > 0 else 0,
            'bankrupt': self.b
        }
    
    def stay_home(self, pay_existence_cost=False):
        """
        Agent stays home, pays only existence costs.
        """
        # Pay existence costs
        if pay_existence_cost:
            existence_cost = self.cost_existence
            self.update_finances(
                profit=-existence_cost,
                cost=existence_cost,
                revenue=0,
                is_trip=False
            )
        else:
            existence_cost = 0
            
        self.at_home = True
        self.gone_fishing = False
        self.at_sea = False
        self.will_fish = False
        
        trip_info = {
            'location': None,
            'catch': 0,
            'cost': existence_cost,
            'profit': -existence_cost if pay_existence_cost else 0,
            'days': 1,
            'tick': self.model.current_step,
            'region': None,
            'went_fishing': False
        }
        self.update_memory(trip_info)
        
    def return_home(self):
        """
        Agent returns home after fishing trip.
        Handles state updates and fish landing (for trawlers)
        """
        if self.fisher_type in ["archipelago", "coastal"]:
            self.total_catch += self.accumulated_catch
        if self.fisher_type == "trawler":
            self.land_fish()
            
        # Reset trip variables
        self.at_sea = False
        self.gone_fishing = False
        self.at_home = True
        self.current_region = None
        
        self.current_location = None
        if hasattr(self, 'pos') and self.pos:
            self.model.grid.remove_agent(self)
            self.pos = None
            
        self.accumulated_catch = 0
        self.trip_cost = 0
        self.days_in_current_trip = 0
    
    def calculate_profit(self, catch, costs):
        """
        Calculate profit from a fishing trip.
        
        Args:
            catch (float): Amount of fish caught
            costs (float): Total costs incurred
            
        Returns:
            dict: Breakdown of profit calculation
        """
        price_per_unit = self.model.FISH_PRICE
        
        revenue = catch * price_per_unit
        profit = revenue - costs
        
        return {
            'revenue': revenue,
            'costs': costs,
            'profit': profit,
            'catch': catch,
            'price_per_unit': price_per_unit,
            'location': None,
        }
    
    def update_finances(self, profit, cost, revenue, is_trip=True):
        """
        Update agent's financial state.
        
        Args:
            profit (float): Net profit from trip
            costs (float): Total costs
            revenue (float): Total revenue
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
            
    def check_bankruptcy(self):
        """
        Check if agent should declare bankruptcy.
        
        Returns:
            bool: True if bankrupt
        """
        
        bankruptcy_threshold = -(self.cost_existence * 365)
        
        if self.capital <  bankruptcy_threshold:
            self.bankrupt = True
            self.lay_low = True
            self.lay_low_counter = config.BANKRUPTCY_LAYLOW_DAYS
            #print(f"Agent {self.unique_id} ({self.fisher_type}) is bankrupt!")
        elif self.capital < 0:
            if not self.lay_low:
                if random.random() < config.NEGATIVE_CAPITAL_LAYLOW_PROBABILITY:
                    self.lay_low = True
                    self.lay_low_counter = config.NEGATIVE_CAPITAL_LAYLOW_DAYS
    
    def can_afford_trip(self, cost):
        """
        Check if agent can afford a fishing trip.
        
        Args:
            estimated_cost (float): Estimated cost of trip
            
        Returns:
            bool: True if agent can afford
        """
        safety_buffer = config.get_safety_buffer(self.cost_existence)
        
        return self.capital + safety_buffer >= cost
    
    def estimate_trip_cost( self, location):
        """
        Estimate the cost of a fishing trip.
        
        Args:
            location (tuple): Target location (optional)
            
        Returns:
            float: Estimated cost
        """
        if not location:
            return self.cost_activity + self.cost_existence
        
        if self.current_location:
            travel_cost = self.calculate_travel_cost(self.current_location, location)
        else:
            travel_cost = self.get_travel_cost(self.accessible_regions[0])
            
        total_cost = self.cost_activity + self.cost_existence + travel_cost
        
        return total_cost

          
# ==================== ARCHIPELAGO DECISION ====================

    def satisfice_lifestyle(self):
        """
        Archipelago decision model: Satisficing behavior
        Fish only when necessary to meet basic needs
        """
        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            can_fish = not self.model.bad_weather
            self.will_fish = can_fish
            if self.model.current_step < 5:
                print(f"[Day {self.model.current_step}] Archipelago #{self.unique_id} EXPLORATION: "
                    f"will_fish={self.will_fish}, bad_weather={self.model.bad_weather}")
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
        
        if self.model.current_step < 30:
            print(f"[Day {self.model.current_step}] Archipelago #{self.unique_id} POST-EXPLORATION:")
            print(f"  Last {last_days_count} days catches: {[t['catch'] for t in recent_days]}")
            print(f"  Revenue: {revenue_last_period:.2f} SEK")
            print(f"  Weekly needs: {weekly_needs:.2f} SEK")
            print(f"  Done enough: {revenue_last_period >= weekly_needs}")
            
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
        if self.model.current_step < 100:
            print(f"[Day {self.model.current_step}] Archipelago #{self.unique_id} EXPLORATION: "
                    f"will_fish={self.will_fish}, bad_weather={self.model.bad_weather}")
        
        if self.will_fish:
            self.region_preference = "A"
            
    def update_growth_perception(self):
        """
        Update perception of fish growth based on recent catches
        """
        if not hasattr(self, 'prev_capital'):
            self.prev_capital = self.capital
            self.growth_perception = 0
            return
        
        if self.capital > self.prev_capital:
            indicator = 1
        elif self.capital < self.prev_capital:
            indicator = -1
        else:
            indicator = 0
            
        if not hasattr(self, 'growth_perception_list'):
            self.growth_perception_list = []
            
        self.growth_perception_list.append(indicator)
        
        if len(self.growth_perception_list) > self.memory_size:
            self.growth_perception_list.pop(0)
            
        if self.growth_perception_list:
            counts = Counter(self.growth_perception_list)
            mode_value = counts.most_common(1)[0][0]
            self.growth_perception = mode_value / 1.0
            
        self.prev_capital = self.capital
            
                
# ==================== COASTAL DECISION ====================

    def optimise_lifestyle_and_growth(self):
        """
        Coastal decision model: Balance between lifestyle and profit
        Trade-off between staying home and maximizing catch
        """
        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            can_fish = not self.model.bad_weather
            self.will_fish = can_fish
            if self.will_fish:
                self.region_preference = self.accessible_regions[0]
            return
        # Calculate expected catches per region
        expected_catches = {}
        for region in self.accessible_regions:
            region_memory = [trip for trip in self.memory if trip.get('region') == region]
            if region_memory:
                # Weight recent trips more heavily
                recent = region_memory[-30:] if len(region_memory) >= 30 else region_memory
                expected_catches[region] = statistics.mean(trip['catch'] for trip in recent)
            else:
                # Conservative estimate if no memory for this region
                expected_catches[region] = self.catchability * 0.8
        
        # Calculate expected costs per region
        expected_costs = {}
        for region in self.accessible_regions:
            travel_cost = self.get_travel_cost(region)
            expected_costs[region] = self.cost_existence + self.cost_activity + travel_cost    
        
        # Calculate expected profits
        expected_profits = {}
        for region in self.accessible_regions:
            expected_revenue = expected_catches[region] * self.model.FISH_PRICE
            expected_profits[region] = expected_revenue - expected_costs[region]
        
        # Determine best region
        if expected_profits:
            self.region_preference = max(expected_profits, key=expected_profits.get)
            max_profit = expected_profits[self.region_preference]
        else:
            self.region_preference = self.accessible_regions[0]
            max_profit = 0
        
        # Calculate satisfactions
        # Home satisfaction: how much time spent at home recently
        recent_trips = list(self.memory)[-14:] if len(self.memory) >= 14 else list(self.memory)
        if recent_trips:
            fishing_trips = [t for t in recent_trips if t.get('went_fishing', False)]
            satisfaction_home = 1.0 - (len(fishing_trips) / len(recent_trips))
        else:
            satisfaction_home = 0.5
        
        expected_profit_stay = -self.cost_existence
        expected_profit_go = max_profit
        
        can_fish = not self.model.bad_weather
        # Growth satisfaction: potential profit vs needs
        if self.capital < 0:
            self.will_fish = can_fish
            self.wanna_be_home = False
            
        # 2. Si fishing est profitable ET satisfaction_home est basse → Pêcher
        elif expected_profit_go > expected_profit_stay:
            if satisfaction_home < self.satisfaction_home_threshold:
                # Satisfaction home trop basse → Rester à la maison
                self.will_fish = False
                self.wanna_be_home = True
            else:
                # Satisfaction home OK ET fishing profitable → Pêcher
                self.will_fish = can_fish
                self.wanna_be_home = False
        
        # 3. Sinon → Rester à la maison
        else:
            self.will_fish = False
            self.wanna_be_home = True

        
# ==================== TRAWLER DECISION ====================

    def optimise_growth(self):
        """
       Trawler decision model: Pure profit maximization
       Multi-day trips with storage capacity
       """
        if len(self.memory) < config.EXPLORATION_PHASE_TRIPS:
            self.will_fish = not self.model.bad_weather
            if self.will_fish:
                self.region_preference = self.accessible_regions[0]
                self.fish_onboard = 0
                self.days_at_sea_current_trip = 0
                self.jumped = False
            return
        
        if self.gone_fishing:
            self._decide_while_at_sea()
        else:
            self._decide_while_at_home()

            
    def _decide_while_at_sea(self):
        """Decision logic when trawler is already at sea"""
        current_region = self.current_region if self.current_region else self.region_preference
        
        fish_wish = self.storing_capacity - self.fish_onboard
        
        if self.current_location:
            patch = self.model.get_patch_info(*self.current_location)
            fish_vicinity = patch['fish_stock'] if patch else 0
            
            neighbors = self.get_neighbor_positions_in_radius(self.current_location, radius=1)
            for neighbor_pos in neighbors:
                neighbor_patch = self.model.get_patch_info(*neighbor_pos)
                if neighbor_patch and neighbor_patch['region'] == current_region:
                    fish_vicinity += neighbor_patch['fish_stock']
                    
        else:
            fish_vicinity = 0
            
        if fish_vicinity >= fish_wish:
            expected_catch = fish_wish
            self.region_preference = current_region
            expected_travel_cost = 0
        else:
            expected_catch = fish_wish
            
            other_regions = [r for r in self.accessible_regions if r != current_region]
            expected_catches = {}
            travel_costs = {}
            
            for region in other_regions:
                expected_catches[region] = self._estimate_catch(region)
                travel_costs[region] = self.get_travel_cost_between_regions(current_region, region)
                
            best_switch_profit = float('-inf')
            best_switch_region = None
            
            for region in other_regions:
                revenue = expected_catches[region] * config.FISH_PRICE
                profit = revenue - self.cost_activity - travel_costs[region]
                if profit > best_switch_profit:
                    best_switch_profit = profit
                    best_switch_region = region
                    
            stay_profit = fish_vicinity * config.FISH_PRICE - self.cost_activity
            
            if best_switch_profit > stay_profit:
                self.region_preference = best_switch_region
                expected_travel_cost = travel_costs[best_switch_region]
                self.jumped = True
            else:
                self.region_preference = current_region
                expected_travel_cost = self.get_travel_cost(current_region) / 8
                
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
        # Calculate expected profits per region
        expected_profits = {}
        for region in self.accessible_regions:
            expected_catch = self._estimate_catch(region)
            travel_cost = self.get_travel_cost(region)
            total_cost = self.cost_existence + self.cost_activity + travel_cost
            expected_revenue = expected_catch * self.model.FISH_PRICE
            expected_profits[region] = expected_revenue - total_cost
        
        # Find best region
        if expected_profits:
            best_region = max(expected_profits, key=expected_profits.get)
            max_profit = expected_profits[best_region]
            
            # Decide to go if profit exceeds threshold
            profit_threshold = self.cost_existence * config.TRAWLER_PROFIT_THRESHOLD_DAYS  # Must be worth at least 3 days of existence
            expected_profit_stay = -self.cost_existence
            
            if max_profit > expected_profit_stay:
                self.will_fish = True
                self.region_preference = best_region
                self.fish_onboard = 0
                self.days_at_sea_current_trip = 0
                self.jumped = False
            else:
                self.will_fish = False
        else:
            self.will_fish = False
            
    def _estimate_catch(self, region):
        """Estimate expected catch in a region based on memory"""
        region_memory = [trip for trip in self.memory if trip.get('region') == region]
        if region_memory:
            # Weight recent trips more
            recent = region_memory[-10:]
            return statistics.mean(trip['catch'] for trip in recent)
        else:
            return self.catchability * 0.8
        
    def land_fish(self):
        """Land fish when returning home (trawler only)"""
        if self.fisher_type == "trawler" and self.fish_onboard > 0:
            revenue = self.fish_onboard * self.model.FISH_PRICE
            self.capital += revenue
            self.wealth += revenue
            self.total_revenue += revenue
            self.total_catch += self.fish_onboard
            
            # Reset
            self.fish_onboard = 0
            self.days_in_current_trip = 0
            self.jumped = False
            
# ==================== SPOT SELECTION ====================

    def decide_fishSpot(self, region):
        """
        Main spot selection method
        Routes to different strategies based on agent type and strategy
        """
        if not region:
            return None
        
        # Trawler with technology uses uphill climbing
        if self.fisher_type == "trawler" and hasattr(self, 'has_technology') and self.has_technology:
            return self.get_fishSpot_uphill_climbing(region)
        
        # Route to strategy
        if self.spot_selection_strategy == "knowledge":
            return self.get_fishSpot_knowledge(region)
        elif self.spot_selection_strategy == "expertise":
            return self.get_fishSpot_expertise(region)
        elif self.spot_selection_strategy == "descrpitive_norm":
            return self.get_fishSpot_descriptive_norm(region)
        else:
            return self.get_fishSpot_knowledge(region)
        
    def get_fishSpot_knowledge(self, region):
        """Select spot from memory (knowledge-based)"""
        good_spots = self.get_good_spots(region)
        
        if good_spots:
            spot, memory = random.choice(list(good_spots))
            return spot
        else:
            return self.explore_random_spot(region)
        
    def get_fishSpot_expertise(self, region):
        """Follow the most successful fisher (expertise-based)"""
        # Find agents currently fishing in this region
        fishing_agents = [a for a in self.model.agents 
                        if a != self 
                        and hasattr(a, 'gone_fishing') 
                        and a.gone_fishing 
                        and hasattr(a, 'current_region')
                        and a.current_region == region]
        
        if fishing_agents:
            # Find agent with highest total catch
            expert = max(fishing_agents, key=lambda a: a.total_catch)
            if hasattr(expert, 'pos') and expert.pos:
                return expert.pos
        
        # Fallback to knowledge
        return self.get_fishSpot_knowledge(region)

    
    def get_fishSpot_descriptive_norm(self, region):
        """Go where most fishers are (descriptive norm)"""
        spot_with_most = self.fishspot_with_most_fishers(region)
        
        if spot_with_most:
            return spot_with_most
        else:
            # Fallback to knowledge
            return self.get_fishSpot_knowledge(region)
        
    def fishspot_with_most_fishers(self, region):
        """Find the spot with the most fishers in a region"""
        # Count agents per position
        agent_counts = {}
        for agent in self.model.agents:
            if (agent != self 
                and hasattr(agent, 'gone_fishing') 
                and agent.gone_fishing
                and hasattr(agent, 'current_region')
                and agent.current_region == region 
                and hasattr(agent, 'current_location')
                and agent.pos):
                
                pos = agent.current_location
                
                nearby_agents = self.get_agents_in_radius(pos, radius=1)
                nearby_in_region = sum(1 for a in nearby_agents if a.current_region == region)
                
                agent_counts[pos] = agent_counts.get(pos, 0) + 1 + nearby_in_region
        
        if agent_counts:
            return max(agent_counts, key=agent_counts.get)
        else:
            return None
        
    def get_fishSpot_uphill_climbing(self, region):
        """
        Trawler with technology: move to neighboring patch with highest stock
        """
        if self.current_location:
            neighbors = self.get_neighbor_positions_in_radius(
                self.current_location,
                radius=1
            )
            
            valid_neighbors = []
            for pos in neighbors:
                patch = self.model.get_patch_info(pos[0], pos[1])
                if patch and patch['region'] == region:
                    valid_neighbors.append((pos, patch['fish_stock']))
                    
            if valid_neighbors:
                best_spot = max(valid_neighbors, key=lambda x: x[1])
                return best_spot[0]
            
        return self.get_fishSpot_knowledge(region)
    
# ==================== HELPER METHODS ====================

    def get_travel_cost(self, region):
        """Calculate travel cost to a region"""
        if region == "A":
            return self.model.LOW_COST_TRAVEL
        elif region == "B":
            if self.fisher_type == "trawler":
                return self.model.MEDIUM_COST_TRAVEL_BIGVESSEL
            else:
                return self.model.MEDIUM_COST_TRAVEL
        elif region in ["C", "D"]:
            return self.model.HIGH_COST_TRAVEL
        else:
            return 0
        
    def get_travel_cost_between_regions(self, from_region, to_region):
        """Calculate cost to travel between two regions"""
        return self.get_travel_cost(to_region) * 0.5
    
    def calculate_distance(self, pos1, pos2):
        """
        Calculate Euclidean distance between two positions
        
        Args:
            pos1: (x, y) tuple
            pos2: (x, y) tuple
            
        Returns:
            float: Distance
        """
        if not pos1 or not pos2:
            return 0
        
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        
        return (dx**2 + dy**2)**0.5
    
    def get_agents_in_radius(self, pos, radius=3):
        """
        Get all AGENTS within a radius
        
        Args:
            pos: Center position (x, y)
            radius: Search radius
            
        Returns:
            list: List of FisherAgent objects within radius
        """
        if not pos:
            return []
        
        agents_nearby = []
        for agent in self.model.agents:
            if agent == self:
                continue
            
            if hasattr(agent, 'current_location') and agent.current_location:
                distance = self.calculate_distance(pos, agent.current_location)
                if distance <= radius:
                    agents_nearby.append(agent)
                    
        return agents_nearby

    def get_neighbor_positions_in_radius(self, pos, radius=1):
        """
        Get all PATCH POSITIONS within a radius (NetLogo: neighbors)
        
        Args:
            pos: Center position (x, y)
            radius: Search radius (1 = immediate neighbors)
            
        Returns:
            list: List of (x, y) tuples
        """
        if not pos:
            return []
        
        # Use Mesa's built-in grid method
        neighbors = self.model.grid.get_neighborhood(
            pos,
            moore=True,  # Include diagonals
            include_center=False,
            radius=radius
        )
        
        return list(neighbors)
    
    def print_status(self):
        """
        Print agentstatus for debugging
        """
        status = 'gone fishing' if self.gone_fishing else "at home"
        print(f"{status} Agent {self.unique_id} ({self.fisher_type}):")
        print(f"    Capital: {self.capital:.2f}")
        print(f"    Total catch: {self.total_catch:.0f}")
        print(f"    At home: {self.at_home}")
        print(f"    Region: {self.current_region}")
        
        if len(self.memory) > 0:
            recent = list(self.memory)[-1]
            print(f"    Last trip: catch={recent['catch']:.0f}, profit={recent['profit']:.2f}")
            
    
# ==================== PERCEPTION & SATISFACTION ====================

    def update_satisfaction(self):
        """ 
        Update agent's satisfaction levels based on recentexperience
        """
        if len(self.memory) < 7:
            self.satisfaction_home = 0.5
            self.satisfaction_growth = 0.5
            return
        
        recent_trips = list(self.memory)[-14:]
        
        days_at_home = sum(1 for trip in recent_trips if not trip.get('went_fishing', True))
        self.satisfaction_home = days_at_home / len(recent_trips)
        
        if len(recent_trips) >= 14:
            first_half = recent_trips[:7]
            second_half = recent_trips[7:]
            
            avg_profit_first = statistics.mean(t['profit'] for t in first_half)
            avg_profit_second = statistics.mean(t['profit'] for t in second_half)
            
            if avg_profit_first != 0:
                profit_growth = (avg_profit_second - avg_profit_first) / abs(avg_profit_first)
                self.satisfaction_growth = max(0, min(1, (profit_growth + 1) / 2))
            else:
                self.satisfaction_growth = 0.5
        else:
            avg_profit = statistics.mean(t['profit'] for t in recent_trips)
            if avg_profit > 0:
                self.satisfaction_growth = min(1.0, avg_profit / (self.cost_existence * 2))
            else:
                self.satisfaction_growth = 0.0
    
    def update_perception_scarcity(self):
        """
        Update agent's perception of fish scarcity
        Based on catch trends and memory
        """
        if len(self.memory) < config.SCARCITY_MIN_MEMORY:
            self.perceive_scarcity = False
            return
        
        recent = list(self.memory)[-config.SCARCITY_MIN_MEMORY:]
        recent_catches = [t['catch'] for t in recent if t.get('went_fishing', True)]
        
        if not recent_catches:
            self.perceive_scarcity = False
            return
        
        avg_recent_catch = statistics.mean(recent_catches)
        
        expected_catch = self.catchability
        
        if expected_catch > 0:
            catch_ratio = avg_recent_catch / expected_catch
            
            self.perceive_scarcity = catch_ratio < config.SCARCITY_CATCH_RATIO_THRESHOLD
        else:
            self.perceive_scarcity = False
            
# ==================== STATISTICS & SUMMARY ====================

    def get_agent_summary(self):
        """
        Get comprehensive summary of agent state
        Useful for debugging and analysis
        
        Returns:
            dict: Agent statistics and state
        """
        summary = {
            # Identity
            'id': self.unique_id,
            'type': self.fisher_type,
            'age': self.age,
            
            # Financial
            'capital': self.capital,
            'wealth': self.wealth,
            'total_revenue': self.total_revenue,
            'total_costs': self.total_cost,
            'total_profit': self.total_profit,
            'bankrupt': self.bankrupt,
            
            # Fishing activity
            'total_catch': self.total_catch,
            'days_at_sea': self.days_at_sea,
            'profitable_trips': self.profitable_trip,
            'unprofitable_trips': self.unprofitable_trip,
            
            # Current state
            'at_home': self.at_home,
            'at_sea': self.at_sea,
            'gone_fishing': self.gone_fishing,
            'lay_low': self.lay_low,
            'current_region': self.current_region,
            
            # Decision-making
            'will_fish': self.will_fish,
            'region_preference': self.region_preference,
            'growth_perception': self.growth_perception,
            
            # Memory
            'memory_size': len(self.memory),
            'good_spots_count': len(self.good_spots_memory),
        }
        
        if self.fisher_type == "trawler":
            summary['fish_onboard'] = self.fish_onboard
            summary['storing_capacity'] = self.storing_capacity
            summary['jumped'] = self.jumped
            
        if len(self.memory) > 0:
            mem_stats = self.get_memory_statistics()
            summary.update(mem_stats)
            
        return summary

# ==================== MAIN DECISION METHOD ====================

    def make_decision(self):
        """
        Main decision-making method
        Routes to appropriate decision model based on fisher type
        """
        if self.fisher_type == "archipelago":
            self.satisfice_lifestyle()
        elif self.fisher_type == "coastal":
            self.optimise_lifestyle_and_growth()
        elif self.fisher_type == "trawler":
            self.optimise_growth()
        else:
            self.will_fish = False
    
    def reset_yearly_counters(self):
        self.yearly_catch = 0
        self.yearly_profit = 0
        
    def step(self):
        """Execute one step of the agent"""
        self.make_decision()
        self.execute_decision()      
        self.update_growth_perception()
        self.update_satisfaction()
        self.update_perception_scarcity()
        self.check_bankruptcy()
from mesa import Agent
from model import *
import random
import statistics


class FisherAgent(Agent):
    
    def __init__(self, unique_id, model, fisher_type):
        super().__init__(model)
        self.fisher_type = fisher_type # "archipelago", "coastal", "trawler"
        self.unique_id = unique_id
        
        # Basic attributes
        self.wealth = 0
        self.capital = 1000
        self.age = random.randint(18, 65)
        self.days_at_sea = 0
        self.total_catch = 0
        self.total_profit = 0
        self.total_cost = 0
        self.total_revenue = 0
        
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
        self.memory_size = 10 # Remenber last 10 fishing trips
        self.memory = []
        
        # Spatial memory
        self.good_spots_memory = {} # {(x,y): {'visits': n, 'avg_catch': x, 'last_visit': tick}}
        self.good_spots_threshold = 0.7
        
        # Decision-making attributes
        self.will_fish = False
        self.region_preference = None
        self.spot_selection_strategy = "knowledge"      
        
        # Threshold
        self.satisfaction_home_threshold = 0.5
        self.satisfaction_growth_threshold = 0.6
        self.scarce_perception_threshold = -0.05
        
        # Trawler specific
        self.fish_onboard = 0
        self.storing_capacity = 5000 if fisher_type == "trawler" else 0
        self.jumped = False # Changed region while at sea  
        
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
            self.accessible_regions = ["A", "B"]
            self.lifestyle_preference = "medium"
            self.max_good_spots = 3
            
        elif self.fisher_type == "trawler":
            self.cost_existence = self.model.HIGH_COST_EXISTENCE
            self.cost_activity = self.model.HIGH_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_TRAWLER
            self.accessible_regions = ["A", "B", "C", "D"]
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
        
        # Base travel cost per unit distance
        travel_cost_per_unit = 1.0
        
        return distance * travel_cost_per_unit
    
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
            costs = self.cost_existence + self.cost_activity
            self.update_finances( -costs, costs, 0)
            return {
                'catch': 0,
                'costs': costs,
                'profit': -costs,
                'revenue': 0,
                'location': location
            }
        
        # Calculate potential catch (min of catchability and available stock)
        available_stock = patch['fish_stock']
        potential_catch = min(self.catchability, available_stock)
        
        # Reduce stock in the model
        actual_catch = self.model.reduce_stock(location[0], location[1], potential_catch)
        
        # Calculate costs
        travel_cost = self.calculate_travel_cost(self.current_location, location)
        total_cost = self.cost_existence + self. cost_activity + travel_cost
        
        # Calculate profit
        profit_calc = self.calculate_profit(actual_catch, total_cost)
        
        # Update agent finances
        self.update_finances(
            profit_calc['profit'],
            profit_calc['costs'],
            profit_calc['revenue']
        )
        
        # Updating agent state
        self.accumulated_catch += actual_catch
        self.total_catch += actual_catch
        self.trip_cost += total_cost
        self.days_at_sea += 1
        
        # Update memory for this spot
        expected_catch = self.catchability
        self.update_memory_good_spots(location, actual_catch, expected_catch)
        
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
            # Exploration
            return self.explore_random_spot(region)
        
    def explore_random_spot(self, region):
        """
        Choose a random hotspot for exploration.
        
        Args:
            region: Region to explore
            
        Returns:
            (x, y) tuple or None
        """
        # Get hotspots for this region
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
        
        if hotspots:
            spot = random.choice(hotspots)
            return tuple(spot)
        
        return None
    
    def execute_decision(self):
        """
        Execute the agent's fishing decision.
        For archipelago (Step 4): simple single-day trip.
        """
        
        if self.bankrupt:
            self.lay_low = True
            self.will_fish = False
            return
        
        if self.will_fish and not self.lay_low:
            
            target_region = self.region_preference if self.region_preference else self.accessible_regions[0]
            target_spot = self.select_fishing_spot(region=self.accessible_regions[0])
            
            if target_spot:
                estimated_cost = self.estimate_trip_cost(target_spot)
                
                if not self.can_afford_trip(estimated_cost):
                    print(f" Agent {self.unique_id} cannot afford trip (capital: {self.capital:.2f}, cost: {estimated_cost:.2f})")
                    self.stay_home()
                    return
                
                self.move_to(target_spot[0], target_spot[1])
                
                trip_result = self.go_fish(target_spot)
                
                
                trip_info = {
                    'location': target_spot,
                    'catch': trip_result['catch'],
                    'cost': trip_result['costs'],
                    'profit': trip_result['profit'],
                    'days': 1,
                    'tick': self.model.current_step,
                    'region': target_region
                }
                self.update_memory(trip_info)
                
                # Update state
                self.at_home = False
                self.gone_fishing = True
                
                # Return home
                self.return_home()
            else:
                self.stay_home()
        else:
            self.stay_home()
            
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
    
    def stay_home(self):
        """
        Agent stays home, pays only existence costs.
        """
        # Pay existence costs
        existence_cost = self.cost_existence
        
        self.update_finances(
            profit=-existence_cost,
            cost=existence_cost,
            revenue=0
        )
        
        self.at_home = True
        self.gone_fishing = False
        self.at_sea = False
        self.will_fish = False
        
        trip_info = {
            'location': None,
            'catch': 0,
            'cost': existence_cost,
            'profit': -existence_cost,
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
        
    def decide_to_fish_simple(self):
        """
        Simple decision: fish with 70% probability (for testing Step 4).
        Will be replaced by satisfice_lifestyle() in Step 6.
        """
        self.will_fish = random.random() < 0.7
    
    def calculate_profit(self, catch, costs):
        """
        Calculate profit from a fishing trip.
        
        Args:
            catch (float): Amount of fish caught
            costs (float): Total costs incurred
            
        Returns:
            dict: Breakdown of profit calculation
        """
        price_per_unit = 1.0
        
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
    
    def update_finances(self, profit, cost, revenue):
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
            self.lay_low_counter = 30
            print(f"Agent {self.unique_id} ({self.fisher_type}) is bankrupt!")
        elif self.capital < 0:
            if not self.lay_low:
                if random.random() < 0.3:
                    self.lay_low = True
                    self.lay_low_counter = 7
    
    def can_afford_trip(self, cost):
        """
        Check if agent can afford a fishing trip.
        
        Args:
            estimated_cost (float): Estimated cost of trip
            
        Returns:
            bool: True if agent can afford
        """
        safety_buffer = self.cost_existence * 7
        
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
        
        return travel_cost

          
# ==================== ARCHIPELAGO DECISION ====================

    def satisfice_lifestyle(self):
        """
        Archipelago decision model: Satisficing behavior
        Fish only when necessary to meet basic needs
        """
        
        # Calculate catches from last week
        recent_memory = list(self.memory)[-7:] if len(self.memory) >= 7 else list(self.memory)
        catches_last_week = sum(trip['catch'] for trip in recent_memory)
        
        # Calculate weekly needs
        weekly_needs = self.cost_existence * 7
        
        # Check if fish is perceived as scarce
        if len(self.memory) >= 10:
            fish_is_scarce = self.growth_perception < (self.scarce_perception_threshold * 2)
        else:
            fish_is_scarce = False
            
        # Check if in laylow mode
        if self.lay_low:
            self.lay_low_counter -= 1
            if self.lay_low_counter <= 0:
                self.lay_low = False
            self.will_fish = False
            return
        
        # Decision logic
        needs_money = catches_last_week < weekly_needs or self.capital < 0
        desperate = self.capital < 0
        can_fish = not self.model.bad_weather and (not fish_is_scarce or desperate)
        
        self.will_fish = needs_money and can_fish
        
        # Set region (archipelago only access A)
        if self.will_fish:
            self.region_preference = "A"
            
    def update_growth_perception(self):
        """
        Update perception of fish growth based on recent catches
        """
        if len(self.memory) >= 10:
            # Compare recent catches (last 5) vs older catches (5 before that)
            recent_catches = [trip['catch'] for trip in list(self.memory)[-5:]]
            avg_recent = sum(recent_catches) / len(recent_catches)
            
            older_catches = [trip['catch'] for trip in list(self.memory)[-10:-5]]
            avg_older = sum(older_catches) / len(older_catches) if older_catches else avg_recent
            
            if avg_older > 0:
                self.growth_perception = (avg_recent - avg_older) / avg_older
            else:
                self.growth_perception = 0
        else:
            # Pas assez d'historique : perception neutre
            self.growth_perception = 0 
                
# ==================== COASTAL DECISION ====================

    def optimise_lifestyle_and_growth(self):
        """
        Coastal decision model: Balance between lifestyle and profit
        Trade-off between staying home and maximizing catch
        """
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
            expected_profits[region] = expected_catches[region] - expected_costs[region]
        
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
            went_fishing_count = sum(1 for trip in recent_trips if trip.get('profit', 0) != 0)
            satisfaction_home = 1.0 - (went_fishing_count / len(recent_trips))
        else:
            satisfaction_home = 0.5
        
        # Growth satisfaction: potential profit vs needs
        if max_profit > 0:
            satisfaction_growth = max_profit / (self.cost_existence * 2)
            satisfaction_growth = min(satisfaction_growth, 1.0)  # Cap at 1.0
        else:
            satisfaction_growth = 0
        
        # Decision logic
        profit_worthwhile = max_profit > self.cost_existence
        growth_desire = satisfaction_growth > self.satisfaction_growth_threshold
        home_desire = satisfaction_home < self.satisfaction_home_threshold
        desperate = self.capital < 0
        can_fish = not self.model.bad_weather
        
        if len(self.memory) < 5:
            # Phase d'exploration initiale
            self.will_fish = can_fish and profit_worthwhile
        else:
            # Phase normale
            self.will_fish = can_fish and profit_worthwhile and (growth_desire or home_desire or desperate)


        
# ==================== TRAWLER DECISION ====================

    def optimise_growth(self):
        """
       Trawler decision model: Pure profit maximization
       Multi-day trips with storage capacity
       """
        if self.at_sea:
            self._decide_while_at_sea()
        else:
            self._decide_while_at_home()
            
    def _decide_while_at_sea(self):
        """Decision logic when trawler is already at sea"""
        current_region = self.region_preference
        
        # Check if storage is full
        if self.fish_onboard >= self.storing_capacity:
            # Must return home
            self.will_fish = False
            self.region_preference = None
            return
        
        # Calculate profit if staying
        expected_catch_stay = self._estimate_catch(current_region)
        profit_stay = expected_catch_stay - self.cost_activity
        
        # Calculate profit if switching region
        other_regions = [r for r in self.accessible_regions if r != current_region]
        best_switch_profit = 0
        best_switch_region = None
        
        for region in other_regions:
            expected_catch = self._estimate_catch(region)
            travel_cost = self.get_travel_cost_between_regions(current_region, region)
            profit = expected_catch - self.cost_activity - travel_cost
            if profit > best_switch_profit:
                best_switch_profit = profit
                best_switch_region = region
        
        # Calculate profit if returning home
        days_at_sea = self.days_at_sea_current_trip
        avg_daily_profit = self.fish_onboard / days_at_sea if days_at_sea > 0 else 0
        profit_return = avg_daily_profit - self.cost_existence
        
        # Make decision
        if best_switch_profit > profit_stay and best_switch_profit > profit_return:
            # Switch region
            self.region_preference = best_switch_region
            self.jumped = True
            self.will_fish = True
        elif profit_stay > profit_return:
            # Stay in current region
            self.will_fish = True
        else:
            # Return home
            self.will_fish = False
            self.region_preference = None
            
    def _decide_while_at_home(self):
        """Decision logic when trawler is at home"""
        # Calculate expected profits per region
        expected_profits = {}
        for region in self.accessible_regions:
            expected_catch = self._estimate_catch(region)
            travel_cost = self.get_travel_cost(region)
            total_cost = self.cost_existence + self.cost_activity + travel_cost
            expected_profits[region] = expected_catch - total_cost
        
        # Find best region
        if expected_profits:
            best_region = max(expected_profits, key=expected_profits.get)
            max_profit = expected_profits[best_region]
            
            # Decide to go if profit exceeds threshold
            profit_threshold = self.cost_existence * 3  # Must be worth at least 3 days of existence
            
            if max_profit > profit_threshold or self.capital < 0:
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
            return self.catchability * 0.6
        
    def land_fish(self):
        """Land fish when returning home (trawler only)"""
        if self.fisher_type == "trawler" and self.fish_onboard > 0:
            revenue = self.fish_onboard
            self.capital += revenue
            self.wealth += revenue
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
                and hasattr(agent, 'pos')
                and agent.pos):
                
                pos = agent.pos
                agent_counts[pos] = agent_counts.get(pos, 0) + 1
        
        if agent_counts:
            return max(agent_counts, key=agent_counts.get)
        else:
            return None
        
    def get_fishSpot_uphill_climbing(self, region):
        """
        Trawler with technology: move to neighboring patch with highest stock
        """
        if self.pos:
            neighbors = self.model.grid.get_neighborhood(
                self.pos, more=True, include_center=True, radius=1
            )
            
            valid_neighbors = []
            for pos in neighbors:
                patch = self.model.get_patch_info(pos[0], pos[1])
                if patch and patch['region'] == region:
                    valid_neighbors.append((pos, patch['fish_stock']))
                    
            if valid_neighbors:
                best_spot = max(valid_neighbors, key=lambda x: x[1])
                return best_spot[0]
            
        return self.get_fishSpot_knowledge(region)##
    
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
    
    def get_neighbors_in_radius(self, pos, radius=3):
        """
        Get all agents within a radius
        
        Args:
            pos: Center position (x, y)
            radius: Search radius
            
        Returns:
            list: List of agents within radius
        """
        if not pos:
            return []
        
        neighbors = []
        for agent in self.model.agents:
            if agent == self:
                continue
            
            if hasattr(agent, 'pos') and agent.pos:
                distance = self.calculate_distance(pos, agent.pos)
                if distance <= radius:
                    neighbors.append(agent)
                    
        return neighbors
    
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
        if len(self.memory) < 10:
            self.perceive_scarcity = False
            return
        
        recent = list(self.memory)[-10:]
        recent_catches = [t['catch'] for t in recent if t.get('went_fishing', True)]
        
        if not recent_catches:
            self.perceive_scarcity = False
            return
        
        avg_recent_catch = statistics.mean(recent_catches)
        
        expected_catch = self.catchability
        
        if expected_catch > 0:
            catch_ratio = avg_recent_catch / expected_catch
            
            self.perceive_scarcity = catch_ratio < 0.5
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
            
    def step(self):
        """Execute one step of the agent"""
        self.make_decision()
        self.execute_decision()      
        self.update_growth_perception()
        self.update_satisfaction()
        self.update_perception_scarcity()
        self.check_bankruptcy()
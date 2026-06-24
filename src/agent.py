from mesa import Agent
from . import config
import random
import statistics
from collections import Counter

from src.Agent.archipelagos import Archipelago
from src.Agent.coastal import Coastal
from src.Agent.trawler import Trawler


class FisherAgent(Agent):
    
    def __init__(self, unique_id, model, fisher_type, initial_capital=None, name=None, port=None):
        super().__init__(model)
        self.fisher_type = fisher_type # "archipelago", "coastal", "trawler"
        self.unique_id = unique_id
        self.name = name
        self.port = port
        
        # Basic attributes
        self.wealth = 0
        self.capital = config.INITIAL_CAPITAL if initial_capital is None else float(initial_capital)
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
        self.fished_today = False
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
        self.storing_capacity = config.TRAWLER_STORAGE_CAPACITY if fisher_type == "trawler" else self.catchability
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
            self.has_partner = True
            self.has_colleagues = False
            self.has_technologie = False
            
        elif self.fisher_type == "coastal":
            self.cost_existence = self.model.MEDIUM_COST_EXISTENCE
            self.cost_activity = self.model.MEDIUM_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_COASTAL
            self.accessible_regions = ["A", "B"]
            self.lifestyle_preference = "medium"
            self.max_good_spots = 3
            self.wanna_be_home = False
            self.has_partner = True
            self.has_colleagues = True
            self.has_technologie = False
            self.satisfaction_home = 1.0 - (random.randint(0, 50) / 100)
            self.satisfaction_growth = 1.0 - (random.randint(0, 50) / 100)
            
        elif self.fisher_type == "trawler":
            self.cost_existence = self.model.HIGH_COST_EXISTENCE
            self.cost_activity = self.model.HIGH_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_TRAWLER
            self.accessible_regions = ["B", "C", "D"]
            self.lifestyle_preference = "low"
            self.max_good_spots = 2
            self.has_partner = False
            self.has_colleagues = True
            self.has_technologie = True
            
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
        #if self.current_location:
        #    self.model.grid.remove_agent(self)
        
        # Place at new position
        if self.pos is not None:
            self.model.grid.remove_agent(self)
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
        
        current_region = patch['region']

        if self.fisher_type == "coastal":
            stock_here = patch['fish_stock']

            neighbors = self.get_neighbor_positions_in_radius(location, radius=1)
            same_region_neighbors = []
            for nx, ny in neighbors:
                n_patch = self.model.get_patch_info(nx, ny)
                if n_patch and n_patch['region'] == current_region:
                    same_region_neighbors.append(((nx, ny), n_patch))

            if same_region_neighbors:
                other_pos, other_patch = random.choice(same_region_neighbors)
                stock_other = other_patch['fish_stock']

                catch_here = round(0.5 * self.catchability)
                catch_other = self.catchability - catch_here

                # NetLogo xor adjustment
                if (stock_here < catch_here) ^ (stock_other < catch_other):
                    if stock_here < catch_here:
                        catch_here = stock_here
                        catch_other = min(self.catchability - catch_here, stock_other)
                    if stock_other < catch_other:
                        catch_other = stock_other
                        catch_here = min(self.catchability - catch_other, stock_here)
                else:
                    if stock_here < catch_here:
                        catch_here = stock_here
                    if stock_other < catch_other:
                        catch_other = stock_other

                actual_here = self.model.reduce_stock(location[0], location[1], catch_here)
                actual_other = self.model.reduce_stock(other_pos[0], other_pos[1], catch_other)
                actual_catch = actual_here + actual_other
            else:
                # Fallback (should be rare)
                actual_catch = self.model.reduce_stock(
                    location[0], location[1], min(self.catchability, stock_here)
                )
        else:
            available_stock = patch['fish_stock']
            potential_catch = min(self.catchability, available_stock)
            actual_catch = self.model.reduce_stock(location[0], location[1], potential_catch)
        
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
        
        if self.fisher_type == "trawler":
            # Trawler: only deduct costs daily, revenue comes at landing
            self.update_finances(
                profit=-total_cost,   # Only costs, no revenue yet
                cost=total_cost,
                revenue=0,            # Revenue deferred to land_fish()
                is_trip=False         # Don't count as trip yet
            )
            self.accumulated_catch += actual_catch
            self.fish_onboard += actual_catch
            self.days_at_sea += 1
        else:
            # Archipelago/Coastal: immediate profit calculation
            profit_calc = self.calculate_profit(actual_catch, total_cost)
            
            if profit_calc['profit'] > 0:
                self.profitable_trip += 1
            else:
                self.unprofitable_trip += 1
            
            self.update_finances(
                profit_calc['profit'],
                profit_calc['costs'],
                profit_calc['revenue'],
                is_trip=True
            )
            self.accumulated_catch += actual_catch
            self.days_at_sea += 1
            self.total_catch += actual_catch
        
        expected_catch = self.catchability
        self.update_memory_good_spots(location, actual_catch, expected_catch)
        
        return {
            'catch': actual_catch,
            'costs': total_cost,
            'profit': -total_cost if self.fisher_type == "trawler" else (actual_catch * self.model.FISH_PRICE - total_cost),
            'revenue': 0 if self.fisher_type == "trawler" else actual_catch * self.model.FISH_PRICE,
            'location': location
        }
        
    def _calculate_region_preference(self):
        """
        Determine region preference based on cascade comparison of expected catches.
        Mirrors NetLogo logic from set-catch-expectation-and-regionPref (utils.nls)

        NetLogo logic for trawler:
        - If expected-catchB >= expected-catchC
        - If expected-catchC >= expected-catchD → B
        - Else if expected-catchB >= expected-catchD → B
        - Else → D
        - Else (expected-catchB < expected-catchC)
        - If expected-catchC >= expected-catchD → C
        - Else → D
        """
        # Estimate catches for each accessible region
        expected_catches = {}
        for region in self.accessible_regions:  # ["B", "C", "D"]
            expected_catches[region] = self._estimate_catch(region)

        # Cascade comparison logic (matching NetLogo)
        catchB = expected_catches.get("B", self.catchability)
        catchC = expected_catches.get("C", self.catchability)
        catchD = expected_catches.get("D", self.catchability)

        if catchB >= catchC:
            if catchC >= catchD:
                return "B"
            elif catchB >= catchD:
                return "B"
            else:
                return "D"
        else:  # catchB < catchC
            if catchC >= catchD:
                return "C"
            else:
                return "D"
        
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
                #print(f"    Archipelago #{self.unique_id} EXPLORING (no good spots in memory)")
            # Exploration
                spot = self.explore_random_spot(region)
            
            # DEBUG
            if self.model.current_step < 10:
                #print(f"    → Exploration returned: {spot}")
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
            self.lay_low = False
            self.will_fish = True
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
            self.stay_home_state_only()  
            return
        
        if self.will_fish:
            target_region = self.region_preference if self.region_preference else self.accessible_regions[0]
            target_spot = self.decide_fishSpot(target_region)
            
            if target_spot:
                estimated_cost = self.estimate_trip_cost(target_spot)
                
                if not self.can_afford_trip(estimated_cost):
                    self.stay_home(pay_existence_cost=True)
                    return
                
                self.at_home = False
                self.gone_fishing = True
                self.current_region = target_region
                
                # Go fishing
                self.move_to(target_spot[0], target_spot[1])
                trip_result = self.go_fish(target_spot)
                self.fished_today = True
                
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
    
    def reset_daily_flags(self):
        """Reset flags that should be cleared at the end of the day"""
        self.fished_today = False
    
    def finalize_day(self):
        """
        End-of-day state transition.
        Archipelago and coastal trips are day trips: return home after midday snapshot.
        """
        if self.fisher_type in ("archipelago", "coastal") and self.fished_today:
            self.return_home()
       
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
            'total_trips': total_trips,
            'success_rate': self.profitable_trip / total_trips if total_trips > 0 else 0,
            'avg_profit_per_trip': self.total_profit / total_trips if total_trips > 0 else 0,
            'bankrupt': self.bankrupt,
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
        self.calculate_travel_cost(self.current_location, self.port)  # Calculate cost to return home
        self.update_finances(
            profit=0,  # No profit on return
            cost=self.calculate_travel_cost(self.current_location, self.port),
            revenue=0,
            is_trip=False
        )
        
        self.move_to(self.port[0], self.port[1])  # Return to home port
        if self.fisher_type == "trawler":
            self.land_fish()
            
        # Reset trip variables
        self.at_sea = False
        self.gone_fishing = False
        self.at_home = True
        self.current_region = None
        self.current_location = None
        
        if getattr(self, 'pos', None) is not None:
            self.model.grid.remove_agent(self)
            
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
        
        bankruptcy_threshold = -(self.cost_existence * 7)
        
        if self.capital <  bankruptcy_threshold:
            self.bankrupt = True
            #print(f"Agent {self.unique_id} ({self.fisher_type}) is bankrupt!")
     
    def can_afford_trip(self, cost):
        """
        Check if agent can afford a fishing trip.

        NetLogo alignment:
        - Trawlers are not blocked by an upfront affordability gate.
        - Other fisher types keep the safety buffer check.
        """
        if self.fisher_type == "trawler":
            return True

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

        
# ==================== TRAWLER DECISION ====================
            
    def _estimate_catch(self, region):
        """Estimate expected catch in a region based on memory"""
        region_memory = [trip for trip in self.memory if trip.get('region') == region]
        if region_memory:
            # Weight recent trips more
            recent = region_memory[-10:]
            return statistics.mean(trip['catch'] for trip in recent)
        else:
            return self.catchability
        
    def land_fish(self):
        """
        Land fish when returning home (trawler only).
        NetLogo aligned: profit = fish-onboard * fish-price - accumulated_trip_cost
        Costs already deducted daily in go_fish(), so only add revenue here.
        """
        if self.fisher_type == "trawler" and self.fish_onboard > 0:
            revenue = self.fish_onboard * self.model.FISH_PRICE
            
            # Only add revenue (costs already deducted in go_fish each day)
            self.capital += revenue
            self.wealth += revenue
            self.total_revenue += revenue
            self.total_catch += self.fish_onboard
            
            # Count trip as profitable or not
            # Approximate: compare revenue to accumulated cost of the trip
            if revenue > 0:
                self.profitable_trip += 1
            else:
                self.unprofitable_trip += 1
            
            # Reset
            self.fish_onboard = 0
            self.accumulated_catch = 0
            self.days_in_current_trip = 0
            self.jumped = False
            self.gone_fishing = False
            self.at_sea = False
            
# ==================== SPOT SELECTION ====================

    def decide_fishSpot(self, region):
        """
        NetLogo-aligned spot selection.
        - Multi-day trawler at sea: evaluate stayPut after local technology scan.
        - Otherwise choose spot via social rule or knowledge, then optional uphill.
        """
        if not region:
            return None

        stay_put = False
        fishing_spot = None

        # NetLogo multi-day branch (gonefishing)
        if self.fisher_type == "trawler" and self.gone_fishing:
            if self.has_technologie and self.current_location:
                current_spot = self.current_location
                uphill_spot = self.get_fishSpot_uphill_climbing(region)

                # Keep current spot if uphill crosses to another region
                if uphill_spot:
                    uphill_patch = self.model.get_patch_info(*uphill_spot)
                    current_patch = self.model.get_patch_info(*current_spot)
                    if (uphill_patch and current_patch
                            and uphill_patch['region'] == current_patch['region']):
                        self.current_location = uphill_spot

            # NetLogo literal condition:
            # if fish-stock < (storingcapacity - fish-onboard) then stayPut = true
            patch_here = self.model.get_patch_info(*self.current_location) if self.current_location else None
            fish_here = patch_here['fish_stock'] if patch_here else 0
            fish_wish = self.storing_capacity - self.fish_onboard
            if fish_here < fish_wish:
                stay_put = True

        # NetLogo: if not stayPut, select/move
        if not stay_put:
            self.jumped = True

            social_strategy = getattr(self.model, 'social_influence', 'expertise')
            follow_social = (
                social_strategy != "none"
                and self.has_colleagues
                and random.randint(0, 10) < 8
            )

            if follow_social:
                if social_strategy == "descriptiveNorm":
                    fishing_spot = self.get_fishSpot_descriptive_norm(region)
                else:
                    fishing_spot = self.get_fishSpot_expertise(region)

                if fishing_spot is None:
                    fishing_spot = self.get_fishSpot_knowledge(region)
            else:
                fishing_spot = self.get_fishSpot_knowledge(region)

            if fishing_spot is None:
                return self.explore_random_spot(region)

            # Move to chosen spot
            self.current_location = fishing_spot

            # NetLogo second uphill pass after moving
            if self.fisher_type == "trawler" and self.has_technologie:
                current_spot = self.current_location
                uphill_spot = self.get_fishSpot_uphill_climbing(region)
                if uphill_spot:
                    uphill_patch = self.model.get_patch_info(*uphill_spot)
                    current_patch = self.model.get_patch_info(*current_spot)
                    if (uphill_patch and current_patch
                            and uphill_patch['region'] == current_patch['region']):
                        self.current_location = uphill_spot

        self.at_sea = True
        return self.current_location
        
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
        #if len(self.memory) < 7:
        #    self.satisfaction_home = 0.5
        #    self.satisfaction_growth = 0.5
        #    return
        
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
            'fished_today': self.fished_today,
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
            Archipelago.satisfice_lifestyle(self)
        elif self.fisher_type == "coastal":
            Coastal.optimise_lifestyle_and_growth(self)
        elif self.fisher_type == "trawler":
            Trawler.optimise_growth(self)
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
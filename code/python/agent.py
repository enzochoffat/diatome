from mesa import Agent
from model import *
import random



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
        
        
        # Decision variable
        self.current_location = None
        self.target_location = None
        self.at_home = True
        self.gone_fishing = False
        self.will_fish = False
        self.lay_low = False
               
        # Type-specific attribute
        self._set_type_attributes()
        
        # Memory system
        self.memory_size = 10 # Remenber last 10 fishing trips
        self.memory = []
        
        # Spatial memory
        self.good_spots_memory = {} # {(x,y): {'visits': n, 'avg_catch': x, 'last_visit': tick}}
        self.good_spots_threshold = 0.7
        
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
            spot['last_visit'] = self.model.steps
            spot['efficiency'] = catch_efficiency
        else:
            self.good_spots_memory[location] = {
                'avg_catch': catch,
                'visits': 1,
                'last_visit': self.model.steps,
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
        Calculate statistics from temporal memory.
    
        Returns:
            dict: Statistics including avg_profit, avg_catch, success_rate
        """
        
        if not self.memory:
            return {
                'avg_profit': 0,
                'avg_catch': 0,
                'total_trips': 0,
                'success_rate': 0,
                'best_location': None
            }
            
        total_profit = sum(trip['profit'] for trip in self.memory)
        total_catch = sum(trip['catch'] for trip in self.memory)
        profitable_trip = sum (1 for trip in self.memory if trip['profit'] > 0)
        
        best_trip = max(self.memory, key=lambda x: x['profit'])
        
        return {
            'avg_profit': total_profit / len(self.memory),
            'avg_catch': total_catch / len(self.memory),
            'total_trips': len(self.memory),
            'success_rate': profitable_trip / len(self.memory),
            'best_location': best_trip['location']
        }
    
    def forget_old_spots(self, max_age_ticks):
        """
        Remove spots from spatial memory that haven't been visited recently.
        
        Args:
            max_age_ticks (int): Maximum age in ticks before forgetting
        """
        current_tick = self.model.steps
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
            return {
                'catch': 0,
                'cost': self.cost_existence + self.cost_activity,
                'profit': -(self.cost_activity + self.cost_existence),
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
        price_per_catch = 1.0
        revenue = actual_catch * price_per_catch
        profit = revenue - total_cost
        
        # Updating agent state
        self.accumulated_catch += actual_catch
        self.total_catch += actual_catch
        self.trip_cost += total_cost
        self.days_at_sea += 1
        
        # Update memory for this spot
        expected_catch = self.catchability
        self.update_memory_good_spots(location, actual_catch, expected_catch)
        
        return {
            'catch': actual_catch,
            'costs': total_cost,
            'profit': profit,
            'location': location,
            'revenue': revenue
        }
        
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
        
        if self.will_fish and not self.lay_low:
            
            target_spot = self.select_fishing_spot(region="A")
            
            if target_spot:
                self.move_to(target_spot[0], target_spot[1])
                
                trip_result = self.go_fish(target_spot)
                
                self.capital += trip_result['profit']
                self.wealth += trip_result['profit']
                
                trip_info = {
                    'location': target_spot,
                    'catch': trip_result['catch'],
                    'cost': trip_result['costs'],
                    'profit': trip_result['profit'],
                    'days': 1,
                    'tick': self.model.steps
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
    
    def stay_home(self):
        """
        Agent stays home, pays only existence costs.
        """
        # Pay existence costs
        daily_cost = self.cost_existence
        self.capital -= daily_cost
        self.wealth -= daily_cost
        
        # Update state
        self.at_home = True
        self.gone_fishing = False
        
    def return_home(self):
        """
        Agent returns home after fishing trip.
        """
        # Reset trip variables
        self.accumulated_catch = 0
        self.trip_cost = 0
        self.days_in_current_trip = 0
        
        # Update state
        self.at_home = True
        self.gone_fishing = False
        self.current_location = None
        
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
            'cost': costs,
            'profit': profit,
            'catch': catch,
            'price_per_unit': price_per_unit
        }
    
    def update_finances(self, profit, costs, revenue):
        """
        Update agent's financial state.
        
        Args:
            profit (float): Net profit from trip
            costs (float): Total costs
            revenue (float): Total revenue
        """
        
        self.capital += profit
        
        self.total_profit += profit
        self.total_cost += costs
        self.total_revenue += revenue
        self.wealth = self.capital
        
        if profit > 0:
            self.profitable_trip += 1
        else:
            self.unprofitable_trip += 1
            
        if self.capital < 0 and not self.bankrupt:
            self.bankrupt = True
            print(f" Agent {self.unique_id} ({self.fisher_type}) est en faillite! Capital: {self.capital:.2f}")
            
    def check_bankrupt(self):
        """
        Check if agent should declare bankruptcy.
        
        Returns:
            bool: True if bankrupt
        """
        
        if self.capital < 0:
            self.bankrupt = True
            
        return self.bankrupt
    
    def can_afford_trip(self)
        
    def step(self):
        """Execute one step of the agent"""
        self.decide_to_fish_simple()
        self.execute_decision()      
            
    
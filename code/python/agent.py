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
        self.age = random.randint(18, 65)
        self.days_at_sea = 0
        self.total_catch = 0
        self.total_profit = 0
        
        # Type-specific attribute
        self._set_type_attributes()
        
        # Memory system
        self.memory_size = 10 # Remenber last 10 fishing trips
        self.memory = []
        
        # Spatial memory
        self.good_spots_memory = {} # {(x,y): {'visits': n, 'avg_catch': x, 'last_visit': tick}}
        self.good_spots_threshold = 0.7
        
        # Decision variable
        self.current_location = None
        self.target_location = None
        self.days_in_current_trip = 0
        
    def _set_type_attributes(self):
        """Set attributes specific to fisher type"""
        if self.fisher_type == "archipelago":
            self.cost_existence = self.model.LOW_COST_EXISTENCE
            self.cost_activity = self.model.LOW_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_ARCHEPELAGO
            self.accessible_regions = ["A"]
            self.lifestyle_preference = "high"
            
        elif self.fisher_type == "coastal":
            self.cost_existence = self.model.MEDIUM_COST_EXISTENCE
            self.cost_activity = self.model.MEDIUM_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_COASTAL
            self.accessible_regions = ["A", "B"]
            self.lifestyle_preference = "medium"
            
        elif self.fisher_type == "trawler":
            self.cost_existence = self.model.HIGH_COST_EXISTENCE
            self.cost_activity = self.model.HIGH_COST_ACTIVITY
            self.catchability = self.model.CATCHABILITY_TRAWLER
            self.accessible_regions = ["A", "B", "C", "D"]
            self.lifestyle_preference = "low"
            
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
            
    def step(self):
        """Execute one step of the agent"""
        # to be implemented in step 4
        pass      
            
        
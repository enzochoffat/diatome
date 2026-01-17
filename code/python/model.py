from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from agent import FisherAgent

class FisheryModel(Model):
    def __init__(self, end_of_sim, num_archipelago, num_coastal, num_trawler):
        super().__init__()
        
        self.steps = 0
        
        self.num_archipelago = num_archipelago
        self.num_coastal = num_coastal
        self.num_trawler = num_trawler

        # Define time constants
        self.WEEK = 7
        self.MONTH = 28
        self.SEASON = 84
        self.HALFYEAR = 168
        self.YEAR = 365
        self.end_of_sim = end_of_sim

        # Define spatial constants
        self.REGION_A = [[0, 25], [0, 8]]
        self.REGION_B = [[0, 25], [8, 24]]
        self.REGION_C = [[0, 25], [24, 56]]
        self.REGION_D = [[25, 50], [24, 56]]
        self.LAND = [[25, 50], [0, 24]]

        # Define level labels
        self.LOW = "low"
        self.MEDIUM = "medium"
        self.HIGH = "high"
        self.MEDIUM_HIGH = "medium_high"
        self.LOW_MEDIUM = "low_medium"

        # Define cost existence values
        self.LOW_COST_EXISTENCE = 0.5 # archepelago
        self.MEDIUM_COST_EXISTENCE = 1.0 # coastal
        self.HIGH_COST_EXISTENCE = 5.0 # trawler

        # Define activity cost
        self.LOW_COST_ACTIVITY = 0.5 # small equipment
        self.MEDIUM_COST_ACTIVITY = 1.0 # medium equipment
        self.HIGH_COST_ACTIVITY = 5.0 # industrial equipment

        # Define travel cost
        self.LOW_COST_TRAVEL = 2.5 # go to region A
        self.MEDIUM_COST_TRAVEL = 5.0 # go to region B
        self.MEDIUM_COST_TRAVEL_BIGVESSEL = 8 # go to region B with trawler
        self.HIGH_COST_TRAVEL = 15.0 # go to region C or D
        # self.COST_TRAVEL_B2C = 10.0 # go from region B to C
        # self.COST_TRAVEL_C2D = 10.0 # go from region C to D
        # self.COST_TRAVEL_B2D = 15.0 # go from region B to D

        # Define carring capacity
        self.LOW_CARRYING_CAPACITY = 4 # poor patch
        self.MEDIUM_CARRYING_CAPACITY = 3276 # medium patch
        self.HIGH_CARRYING_CAPACITY = 8736 # rich patch
        self.CARRYING_CAPACITY_A = 219000 # capacity region A
        self.CARRYING_CAPACITY_B = 438000 # capacity region B
        self.CARRYING_CAPACITY_C = 876000 # capacity region C
        self.CARRYING_CAPACITY_D = 876000 # capacity region D

        # Define MSY (Maximum Sustainable Yield)
        self.MSY_STOCK_A = round(self.CARRYING_CAPACITY_A / 2) # MSY region A
        self.MSY_STOCK_B = round(self.CARRYING_CAPACITY_B / 2) # MSY region B
        self.MSY_STOCK_C = round(self.CARRYING_CAPACITY_C / 2) # MSY region C
        self.MSY_STOCK_D = round(self.CARRYING_CAPACITY_D / 2) # MSY region D

        # Define daily catchability
        self.CATCHABILITY_ARCHEPELAGO = 5 # archepelago
        self.CATCHABILITY_COASTAL = 10 # coastal
        self.CATCHABILITY_TRAWLER = 50 # trawler

        # Define patchs 
        self.HOTSPOTS_A = [[7, 3], [16, 3]] # high density spots in region A
        self.HOTSPOTS_B = [[3, 19], [8, 11], [19, 11], [15, 19]] # high density spots in region B
        self.HOTSPOTS_C = [[4, 51], [21, 51], [13, 45], [3, 39], [12, 36], [22, 40], [7, 27], [19, 27]] # high density spots in region C
        self.HOTSPOTS_D = [[30, 51], [47, 51], [37, 45], [29, 39], [46, 39], [37, 33], [31, 27], [44, 27]] # high density spots in region D

        # Define growth rate
        self.GROWTH_RATE = 0.1 # 10% per year
        
        # Initialize spatial grid(50x56)
        self.grid = MultiGrid(50, 56, torus=False)

        # Initialize patches with fish stocks
        self.init_patches()
        
        self._recalculate_regional_capacities()
        
        self._create_agents()
        # Data collector
        self.datacollector = DataCollector(
            model_reporters={
                "stock_A": lambda m: m.get_region_stock("A"),
                "stock_B": lambda m: m.get_region_stock("B"),
                "stock_C": lambda m: m.get_region_stock("C"),
                "stock_D": lambda m: m.get_region_stock("D"),
                "total_stock": lambda m: m.get_total_stock()
            }
        )
    
    def _create_agents(self):
        """Create fisher agents of different types"""
        
        agent_id = 0
        
        for _ in range(self.num_archipelago):
            agent = FisherAgent(agent_id, self, "archipelago")
            agent_id += 1
            
        for _ in range(self.num_coastal):
            agent = FisherAgent(agent_id, self, "coastal")
            agent_id += 1
            
        for _ in range(self.num_trawler):
            agent = FisherAgent(agent_id, self, "trawler")
            agent_id += 1
       
    def init_patches(self):
        """Initialize all patches with region, density, and fish stock information"""
        # Dictionary to store patch attributes
        self.patches = {}
        
        # Initialize all patches in the grid
        for x in range(self.grid.width):
            for y in range(self.grid.height):
                region = self.get_region(x, y)
                density = self.get_density(x, y, region)
                fish_stock = self.get_initial_fish_stock(x, y, region, density)
                carrying_capacity = self.get_carrying_capacity(region, density)
                
                # Store patch attributes
                self.patches[(x, y)] = {
                    'region' : region,
                    'density' : density,
                    'fish_stock' : fish_stock,
                    'carrying_capacity' : carrying_capacity,
                    'growth_rate' : self.GROWTH_RATE,
                    'regen_amount' : 0,
                    'patch_stock_after_regrowth' : fish_stock
            
        }
    
    def get_region(self, x, y):
        """Determine which region a coordinate belongs to"""
        # Region A: x[0,25], y[0,8]
        if 0 <= x < 25 and 0 <= y < 8:
            return 'A'
        # Region B: x[0,25], y[8,24]
        elif 0 <= x < 25 and 8 <= y < 24:
            return 'B'
        # Region C: x[0,25], y[24,56]
        elif 0 <= x < 25 and 24 <= y < 56:
            return 'C'
        # Region D: x[25,50], y[24,56]
        elif 25 <= x < 50 and 24 <= y < 56:
            return 'D'
        # Land: x[25,50], y[0,24]
        elif 25 <= x < 50 and 0 <= y < 24:
            return 'LAND'
        else:
            return 'NULL'
    
    def get_density(self, x, y, region):
        if region == 'LAND' or region == 'NULL':
            return None
        
        coord = [x, y]
        
        # Check if coordinate is a hotspot center
        hotspots = []
        if region == 'A':
            hotspots = self.HOTSPOTS_A
        elif region == 'B':
            hotspots = self.HOTSPOTS_B
        elif region == 'C':
            hotspots = self.HOTSPOTS_C
        elif region == 'D':
            hotspots = self.HOTSPOTS_D
            
        # if this is a hotspot center, it's high density
        if coord in hotspots:
            return self.HIGH
        
        # Check the proxinmity to hotspots (within radius 3 for example)
        for hs in hotspots:
            distance = ((x - hs[0])**2 + (y - hs[1])**2)**0.5
            if distance <= 1.5:
                return self.HIGH
            elif distance <= 3:
                return self.MEDIUM
            
        # Default to LOW density
        return self.LOW
    
    def get_carrying_capacity(self, region, density):
        """Get carrying capacity based on region and density"""
        if region == "LAND" or region == "NULL":
            return 0
    
        # Normaliser la densité pour la comparaison (case-insensitive)
        if density is None:
            return 0
    
        density_upper = density.upper() if isinstance(density, str) else str(density).upper()
    
        if density_upper == "HIGH":
            return self.HIGH_CARRYING_CAPACITY
        elif density_upper == "MEDIUM":
            return self.MEDIUM_CARRYING_CAPACITY
        elif density_upper == "LOW":
            return self.LOW_CARRYING_CAPACITY
        else:
            print(f"WARNING: Unknown density '{density}' for region {region}")
            return 0

        
    def get_initial_fish_stock(self, x, y, region, density):
        """Calculate initial fish stock for a patch"(half of carrying capacity MSY)"""
        if region == "LAND" or region == "NULL":
            return 0
        
        carrying_capacity = self.get_carrying_capacity(region, density)
        return round(carrying_capacity / 2)
    
    def get_region_stock(self, region_name):
        """Calculate total fish stock in a specific region"""
        total = 0
        for pos, patch in self.patches.items():
            if patch['region'] == region_name:
                total += patch['fish_stock']
        return total
    
    def get_total_stock(self):
        """Calculate total fish stock across all regions"""
        return sum(patch['fish_stock'] for patch in self.patches.values() if patch['region'] not in ["LAND", "NULL"])
    
    def update_fish_stock(self):
        """Update fish stocks with yearly regrowth (logistic growth)"""
        
        growth_by_region = {"A": 0, "B": 0, "C": 0, "D": 0}
        
        for pos, patch in self.patches.items():
            region = patch['region']
            if patch['region'] not in ["LAND", "NULL"]:
                current_stock = patch['fish_stock']
                carrying_capacity = patch['carrying_capacity']
                growth_rate = patch['growth_rate']
                
                regen_amount = round(
                    current_stock * growth_rate * (1 - current_stock/carrying_capacity)
                )
                
                patch['regen_amount'] = regen_amount
                growth_by_region[region] += regen_amount
        
        # Check regional constraints before applying growth
        for region in ["A", "B", "C", "D"]:
            current_regional_stock = self.get_region_stock(region)
            regional_capacity = self.get_region_carrying_capacity(region)
            proposed_stock = current_regional_stock + growth_by_region[region]
            
            if proposed_stock > regional_capacity:
                if growth_by_region[region] > 0:
                    scale_factor = (regional_capacity - current_regional_stock) / growth_by_region[region]
                    scale_factor = max(0, min(1, scale_factor))
                else:
                    scale_factor = 0
                    
                for pos, patch in self.patches.items():
                    if patch['region'] == region:
                        patch['regen_amount'] = round(patch['regen_amount'] * scale_factor)
                        patch['fish_stock'] = patch['fish_stock'] + patch['regen_amount']
                        patch['patch_stock_after_regrowth'] = patch['fish_stock']
            
            else:
                for pos, patch in self.patches.items():
                    if patch['region'] == region:
                        patch['fish_stock'] = patch['fish_stock'] + patch['regen_amount']
                        patch['patch_stock_after_regrowth'] = patch['fish_stock']
                
    def get_patch_info(self, x, y):
        """Get information about a specific patch"""
        return self.patches.get((x, y), None)
    
    def reduce_stock(self, x, y, catch_amount):
        "Reduce fish stock at a specific location due to fishing"
        if (x, y) in self.patches:
            patch = self.patches[(x, y)]
            patch['fish_stock'] = max(0, patch['fish_stock'] - catch_amount)
    
    def step(self):
        """Advance the model by one step"""
        
        for agent in self.agents:
            agent.step()
            
        self.steps += 1
        
        # Check if it's time for yearly update (every 365 ticks)       
        if self.schedule.steps % self.YEAR == 0:
            self.update_fish_stock()
            
        # Collect data
        self.datacollector.collect(self)
    
    def get_region_carrying_capacity(self, region_name):
        """Get total carrying capacity for a region"""
        capacities = {
            "A": self.CARRYING_CAPACITY_A,
            "B": self.CARRYING_CAPACITY_B,
            "C": self.CARRYING_CAPACITY_C,
            "D": self.CARRYING_CAPACITY_D,
            "LAND": 0,
            "NULL": 0
        }
        return capacities.get(region_name, 0)
    
    def reduce_stock(self, x, y, catch_amount):
        """
        Reduce fish stock at a specific locationdue to fishing.
        Returns the actual amount caught.
        """
        if (x, y) in self.patches:
            patch = self.patches[(x, y)]
            current_stock = patch['fish_stock']
            
            # Can't catch more than available
            actual_catch = min(catch_amount, current_stock)
            
            # Update stock
            patch['fish_stock'] = max(0, current_stock - actual_catch)
            
            return actual_catch
        
        return 0
    
    def validate_regional_stocks(self):
        """
        Validate that regional stocks don't exceed their carrying capacities.
        Returns a list of violations (empty if all OK)
        """
        
        violation = []
        
        for region in ["A", "B", "C", "D"]:
            current_stock = self.get_region_stock(region)
            max_capacity = self.get_region_carrying_capacity(region)
            
            if current_stock > max_capacity:
                violation.append({
                    "region" : region,
                    "current" : current_stock,
                    "max": max_capacity,
                    "excess": current_stock - max_capacity,
                    "percentage": ((current_stock / max_capacity)*100)
                })
        return violation
    
    def _recalculate_regional_capacities(self):
        """Recalculate regional carrying capacities based on actual patch distribution"""
        for region in ["A", "B", "C", "D"]:
            total_capacity = 0
            for pos, patch in self.patches.items():
                if patch['region'] == region:
                    total_capacity += patch['carrying_capacity']
            
            # Update the capacity constants with actual values
            if region == "A":
                self.CARRYING_CAPACITY_A = total_capacity
                self.MSY_STOCK_A = round(total_capacity / 2)
            elif region == "B":
                self.CARRYING_CAPACITY_B = total_capacity
                self.MSY_STOCK_B = round(total_capacity / 2)
            elif region == "C":
                self.CARRYING_CAPACITY_C = total_capacity
                self.MSY_STOCK_C = round(total_capacity / 2)
            elif region == "D":
                self.CARRYING_CAPACITY_D = total_capacity
                self.MSY_STOCK_D = round(total_capacity / 2)
        
        print(f"Capacités régionales recalculées:")
        print(f"  Region A: {self.CARRYING_CAPACITY_A} (MSY: {self.MSY_STOCK_A})")
        print(f"  Region B: {self.CARRYING_CAPACITY_B} (MSY: {self.MSY_STOCK_B})")
        print(f"  Region C: {self.CARRYING_CAPACITY_C} (MSY: {self.MSY_STOCK_C})")
        print(f"  Region D: {self.CARRYING_CAPACITY_D} (MSY: {self.MSY_STOCK_D})")

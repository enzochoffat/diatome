from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

class FisheryModel(Model):
    def __init__(self, end_of_sim, num_archipelago, num_coastal, num_trawler):
        super().__init__()
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
        
        if density == self.HIGH:
            return self.HIGH_CARRYING_CAPACITY
        elif density == self.MEDIUM:
            return self.MEDIUM_CARRYING_CAPACITY
        elif density == self.LOW:
            return self.LOW
        else:
            return 0
        
    def get_initial_fish_stock(self, x, y, region, density):
        """Calculate initial fish stock for a patch"(half of carrying capacity MSY)"""
        if region == "LAND" or region == "NULL":
            return 0
        
        carrying_capacity = self.get_carrying_capacity(region, density)
        return round(carrying_capacity /2)
    
    def get_region_stock(self, region_name):
        """Calculate total fish stock in a specific region"""
        total = 0
        for pos, patch in self.patches.item():
            if patch['region'] == region_name:
                total += patch['fish_stock']
        return total
    
    def get_total_stock(self):
        """Calculate total fish stock across all regions"""
        return sum(patch['fish_stock'] for patch in self.patches.values() if patch['region'] not in ["LAND", "NULL"])
    
    def update_fish_stock(self):
        """Update fish stocks with yearly regrowth (logistic growth)"""
        for pos, patch in self.patches.items():
            if patch['region'] not in ["LAND", "NULL"]:
                current_stock = patch['fish_stock']
                carrying_capacity = patch['carrying_capacity']
                growth_rate = patch['growth_rate']
                
                regen_amount = round(
                    current_stock * growth_rate * (1 - current_stock/carrying_capacity)
                )
                
                patch['regen_amount'] = regen_amount
                patch['fish_stock'] = current_stock + regen_amount
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
        # Check if it's time for yearly update (every 365 ticks)
        if self.schedule.steps % self.YEAR == 0:
            self.update_fish_stock()
            
        # Collect data
        self.datacollector.collect(self)       
from mesa import Model

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

        
    

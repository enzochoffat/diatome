from mesa import Agent
from model import *
import random



class FisherAgent(Agent):
    def __init__(self, model, style):
        super().__init__(model)
        self.style = style
        self.willFish = True
        self.layLow = False # to not fishing for reduce costs
        self.atHome = True
        self.currentCapital = 0
        self.previousCapital = 0 # to track capital from previous step
        self.satisfaction = random.random() # initial satisfaction level between 0 and 1
        self.catch = 0 # amount of fish caught in the current step
        self.accumulatedCatch = 0 # total amount of fish caught over time
        self.accumulatedCatchThisYear = 0 # total amount of fish caught in the current year
        self.profit = 0 # profit made in the current step
        self.accumulatedProfit = 0 # total profit made over time
        self.accumulatedProfitThisYear = 0 # total profit made in the current year
        self.lowCatchCounter = 0 # counter for consecutive low catch periods
        self.notAtSeaCounter = 0 # counter for consecutive periods not at sea
        self.atSea = False
        self.goneFishing = False
        self.jumped = False # change spot during a multi-day fishing trip
        self.thinkFishIsScarce = False # think fish is rarely available
        self.fishOnboard = 0 # fish currently on board
        self.memoryCatchTicks = [] # memory of catch over past time ticks
        self.memoryCatch = [] # history of capture
        self.memoryCatchA = [] # history of capture in region A
        self.memoryCatchB = [] # history of capture in region B
        self.memoryCatchC = [] # history of capture in region C
        self.memoryCatchD = [] # history of capture in region D
        self.memoryProfit = [] # history of profit
        self.growthPerception = [] # perception of fish stock growth
        self.goodSpotToday = False # whether the fishing spot was good today
        self.counterWentFishing = 0 # counter for fishing trips
        self.counterFishingPeriod = 0 # counter for fishing periods
        self.regionPreference = None # preferred fishing region
        self.expectedCatchA = 0 # expected catch in region A
        self.expectedCatchB = 0 # expected catch in region B
        self.expectedCatchC = 0 # expected catch in region C
        self.expectedCatchD = 0 # expected catch in region D
        self.memoryGoodSpotsA = [] # memory of good spots in region A
        self.memoryGoodSpotsB = [] # memory of good spots in region B
        self.memoryGoodSpotsC = [] # memory of good spots in region C
        self.memoryGoodSpotsD = [] # memory of good spots in region D
        self.memoryFishAtSpot = [] # memory of fish at specific spots
        self.memoryVisitedSpots = [] # memory of visited spots
        self.fFindingKnowledge = 0 # knowledge about fish finding
        self.movedToday = False # whether the agent moved today
        self.myLastFishSpot = None # last fishing spot used
        self.atSeaCounter = 0 # counter for days at sea
        self.hitGoodSpotCounter = 0 # counter for hitting good spots
        self.storingCapacity = 0 # capacity to store fish onboard
        self.homeSatisfaction = random.uniform(0.5, 1) # satisfaction related to home conditions
        self.growthSatisfaction = random.uniform(0.5, 1) # satisfaction related to growth conditions
        self.expectedProfit = 0 # expected profit from fishing
        self.wannaBeHome = False # desire to be at home


    def step(self):
        if self.style == "archipelago":
            self.archipelago()

        elif self.style == "coastal":
            self.coastal()

        elif self.style == "trawler":
            self.trawler()

    def archipelago(self):
        # constants
        ZONE = [self.model.REGION_A]
        CATCHABILITY = self.model.CATCHABILITY_ARCHEPELAGO
        COST_EXISTENCE = self.model.LOW_COST_EXISTENCE
        COST_ACTIVITY = self.model.LOW_COST_ACTIVITY
        COST_TRAVEL = self.model.LOW_COST_TRAVEL
        technology = False
        collegue = False
        partner = True
        fFindingKnowledge = random.uniform(0.67, 1)

        # dynamic
        regionPreference = self.model.REGION_A
        self.memoryGoodSpotsA = init_memory_good_spots(self.model.HOTSPOTS_A,
                                                       low_dens_spots=[],
                                                         finding_ability=fFindingKnowledge,
                                                            memory_spatial_length=5) # un peu annecdotique je sais pas trop comment sont défini les paramètres de cette fonction
        myLastFishSpot = random.choice(self.memoryGoodSpotsA) if self.memoryGoodSpotsA else None
        self.memoryGoodSpotsB = []
        self.memoryGoodSpotsC = []
        self.memoryGoodSpotsD = []
        self.memoryVisitedSpots = sorted(self.memoryGoodSpotsA)
        self.memoryFishAtSpot = []
        for fish_spot in self.memoryVisitedSpots:
            patch_stock = fish_spot.fish_stock
            self.memoryFishAtSpot.append(patch_stock)

    def coastal(self):
        ZONE = [self.model.REGION_A, self.model.REGION_B]
        CATCHABILITY = self.model.CATCHABILITY_COASTAL
        COST_EXISTENCE = self.model.MEDIUM_COST_EXISTENCE
        COST_ACTIVITY = self.model.MEDIUM_COST_ACTIVITY
        COST_TRAVEL = self.model.MEDIUM_COST_TRAVEL
        technology = False
        collegue = True
        partner = True
        self.fFindingKnowledge = random.uniform(0.34, 0.67)
        self.regionPreference = None
        self.myLastFishSpot = random.choice(ZONE)
        self.memoryGoodSpotsA = init_memory_good_spots(self.model.HOTSPOTS_A,
                                                       low_dens_spots=[],
                                                        finding_ability=self.fFindingKnowledge,
                                                        memory_spatial_length=3)
        self.memoryGoodSpotsB = init_memory_good_spots(self.model.HOTSPOTS_B,
                                                       low_dens_spots=[],
                                                        finding_ability=self.fFindingKnowledge,
                                                        memory_spatial_length=3)
        self.memoryGoodSpotsC = []
        self.memoryGoodSpotsD = []
        self.homeSatisfaction = random.uniform(0.5, 1)
        self.growthSatisfaction = random.uniform(0.5, 1)

    def trawler(self):
        ZONE = [self.model.REGION_B, self.model.REGION_C, self.model.REGION_D]
        CATCHABILITY = self.model.CATCHABILITY_COASTAL
        COST_EXISTENCE = self.model.HIGH_COST_EXISTENCE
        COST_ACTIVITY = self.model.HIGH_COST_ACTIVITY
        COST_TRAVEL = self.model.HIGH_COST_TRAVEL
        technology = True
        collegue = True
        partner = False
        self.fFindingKnowledge = random.uniform(0.34, 0.67)
        self.regionPreference = None
        self.myLastFishSpot = random.choice(ZONE)
        self.memoryGoodSpotsA = []
        self.memoryGoodSpotsB = init_memory_good_spots(self.model.HOTSPOTS_B,
                                                        low_dens_spots=[],
                                                        finding_ability=self.fFindingKnowledge,
                                                        memory_spatial_length=2)
        self.memoryGoodSpotsC = init_memory_good_spots(self.model.HOTSPOTS_C,
                                                        low_dens_spots=[],
                                                        finding_ability=self.fFindingKnowledge,
                                                        memory_spatial_length=2)
        self.memoryGoodSpotsD = init_memory_good_spots(self.model.HOTSPOTS_D,
                                                        low_dens_spots=[],
                                                        finding_ability=self.fFindingKnowledge,
                                                        memory_spatial_length=2)


def init_memory_good_spots(med_high_dens_spots, low_dens_spots, finding_ability, memory_spatial_length):
    
    # Calculate how many spots to remember based on available good spots and memory capacity
    fillcnt = min(len(med_high_dens_spots), memory_spatial_length)
    # Adjust based on finding ability (e.g., 0.8 ability = remember 80% of spots)
    fillcnt = min(fillcnt, round(fillcnt * finding_ability))
    
    # Select random good spots to remember
    memory_good_spots = random.sample(med_high_dens_spots, fillcnt) if fillcnt > 0 else []
    
    # Calculate remaining memory slots
    cnt = memory_spatial_length - len(memory_good_spots)
    
    # If memory not full AND finding ability is low (<0.67), fill with "false positives"
    # This simulates imperfect knowledge: fisher thinks some poor spots are good
    if cnt > 0 and finding_ability < 0.67:
        # Add poor spots to fill remaining memory
        additionals = random.sample(low_dens_spots, min(cnt, len(low_dens_spots)))
        memory_good_spots.extend(additionals)
    
    return memory_good_spots
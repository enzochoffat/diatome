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

    def step(self):
        if self.style == "archipelago":
            self.archipelago()

        elif self.style == "coastal":
            self.coastal()

        elif self.style == "trawler":
            self.trawler()

    def archipelago(self):
        ZONE = [self.model.REGION_A]
        CATCHABILITY = self.model.CATCHABILITY_ARCHEPELAGO
        COST_EXISTENCE = self.model.LOW_COST_EXISTENCE
        COST_ACTIVITY = self.model.LOW_COST_ACTIVITY
        COST_TRAVEL = self.model.LOW_COST_TRAVEL
        technology = False
        collegue = False
        partner = True

    def coastal(self):
        ZONE = [self.model.REGION_A, self.model.REGION_B]
        CATCHABILITY = self.model.CATCHABILITY_COASTAL
        COST_EXISTENCE = self.model.MEDIUM_COST_EXISTENCE
        COST_ACTIVITY = self.model.MEDIUM_COST_ACTIVITY
        COST_TRAVEL = self.model.MEDIUM_COST_TRAVEL
        technology = False
        collegue = True
        partner = True

    def trawler(self):
        ZONE = [self.model.REGION_B, self.model.REGION_C, self.model.REGION_D]
        CATCHABILITY = self.model.CATCHABILITY_COASTAL
        COST_EXISTENCE = self.model.HIGH_COST_EXISTENCE
        COST_ACTIVITY = self.model.HIGH_COST_ACTIVITY
        COST_TRAVEL = self.model.HIGH_COST_TRAVEL
        technology = True
        collegue = True
        partner = False
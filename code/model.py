from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from .agent import FisherAgent
from . import config
import random
import pandas as pd
from datetime import datetime
import os

class FisheryModel(Model):
    def __init__(self, end_of_sim, num_archipelago, num_coastal, num_trawler, verbose=True):
        super().__init__()
        
        self.verbose = verbose
        
        self.current_step = 0
        self.end_of_sim = end_of_sim

        self.num_archipelago = num_archipelago
        self.num_coastal = num_coastal
        self.num_trawler = num_trawler

        # Define time constants
        self.WEEK = config.WEEK
        self.MONTH = config.MONTH
        self.SEASON = config.SEASON
        self.HALFYEAR = config.HALFYEAR
        self.YEAR = config.YEAR
        
        # Weather tracking
        self.bad_weather = False
        self.bad_weather_probability = config.BAD_WEATHER_PROBABILITY

        # Define spatial constants
        self.REGION_A = config.REGION_A
        self.REGION_B = config.REGION_B
        self.REGION_C = config.REGION_C
        self.REGION_D = config.REGION_D
        self.LAND = config.LAND

        # Define level labels
        self.LOW = config.LOW
        self.MEDIUM = config.MEDIUM
        self.HIGH = config.HIGH
        self.MEDIUM_HIGH = config.MEDIUM_HIGH
        self.LOW_MEDIUM = config.LOW_MEDIUM

        # Define cost existence values
        self.LOW_COST_EXISTENCE = config.ARCHIPELAGO_COST_EXISTENCE # archepelago
        self.MEDIUM_COST_EXISTENCE = config.COASTAL_COST_EXISTENCE # coastal
        self.HIGH_COST_EXISTENCE = config.TRAWLER_COST_EXISTENCE # trawler

        # Define activity cost
        self.LOW_COST_ACTIVITY = config.ARCHIPELAGO_COST_ACTIVITY # small equipment
        self.MEDIUM_COST_ACTIVITY = config.COASTAL_COST_ACTIVITY # medium equipment
        self.HIGH_COST_ACTIVITY = config.TRAWLER_COST_ACTIVITY # industrial equipment

        # Define travel cost
        self.LOW_COST_TRAVEL = config.LOW_COST_TRAVEL # go to region A
        self.MEDIUM_COST_TRAVEL = config.MEDIUM_COST_TRAVEL # go to region B
        self.MEDIUM_COST_TRAVEL_BIGVESSEL = config.MEDIUM_COST_TRAVEL_BIGVESSEL # go to region B with trawler
        self.HIGH_COST_TRAVEL = config.HIGH_COST_TRAVEL # go to region C or D
        # self.COST_TRAVEL_B2C = 10.0 # go from region B to C
        # self.COST_TRAVEL_C2D = 10.0 # go from region C to D
        # self.COST_TRAVEL_B2D = 15.0 # go from region B to D

        # Define carring capacity
        self.LOW_CARRYING_CAPACITY = config.LOW_CARRYING_CAPACITY # poor patch
        self.MEDIUM_CARRYING_CAPACITY = config.MEDIUM_CARRYING_CAPACITY # medium patch
        self.HIGH_CARRYING_CAPACITY = config.HIGH_CARRYING_CAPACITY # rich patch
        self.CARRYING_CAPACITY_A = config.CARRYING_CAPACITY_A_INITIAL # capacity region A
        self.CARRYING_CAPACITY_B = config.CARRYING_CAPACITY_B_INITIAL # capacity region B
        self.CARRYING_CAPACITY_C = config.CARRYING_CAPACITY_C_INITIAL # capacity region C
        self.CARRYING_CAPACITY_D = config.CARRYING_CAPACITY_D_INITIAL # capacity region D

        # Define MSY (Maximum Sustainable Yield)
        self.MSY_STOCK_A = config.get_msy_stock(self.CARRYING_CAPACITY_A)
        self.MSY_STOCK_B = config.get_msy_stock(self.CARRYING_CAPACITY_B)
        self.MSY_STOCK_C = config.get_msy_stock(self.CARRYING_CAPACITY_C)
        self.MSY_STOCK_D = config.get_msy_stock(self.CARRYING_CAPACITY_D)

        # Define daily catchability
        self.CATCHABILITY_ARCHEPELAGO = config.ARCHIPELAGO_CATCHABILITY # archepelago
        self.CATCHABILITY_COASTAL = config.COASTAL_CATCHABILITY # coastal
        self.CATCHABILITY_TRAWLER = config.TRAWLER_CATCHABILITY # trawler

        # Define patchs 
        self.HOTSPOTS_A = config.HOTSPOTS_A # high density spots in region A
        self.HOTSPOTS_B = config.HOTSPOTS_B # high density spots in region B
        self.HOTSPOTS_C = config.HOTSPOTS_C # high density spots in region C
        self.HOTSPOTS_D = config.HOTSPOTS_D # high density spots in region D

        # Define growth rate
        self.GROWTH_RATE = config.GROWTH_RATE # 10% per year
        
        self.FISH_PRICE = config.FISH_PRICE
        
        # Initialize spatial grid(50x56)
        self.grid = MultiGrid(config.GRID_WIDTH, config.GRID_HEIGHT, torus=False)

        # Initialize patches with fish stocks
        self.init_patches()
        
        self._recalculate_regional_capacities()
        
        self._create_agents()
        # Data collector
        self.datacollector = DataCollector(
            model_reporters={
                # Fish stocks
                "stock_A": lambda m: m.get_region_stock("A"),
                "stock_B": lambda m: m.get_region_stock("B"),
                "stock_C": lambda m: m.get_region_stock("C"),
                "stock_D": lambda m: m.get_region_stock("D"),
                "total_stock": lambda m: m.get_total_stock(),
                "stock_below_MSY_A": lambda m: 1 if m.get_region_stock("A") < m.MSY_STOCK_A else 0,
                "stock_below_MSY_B": lambda m: 1 if m.get_region_stock("B") < m.MSY_STOCK_B else 0,
                "stock_below_MSY_C": lambda m: 1 if m.get_region_stock("C") < m.MSY_STOCK_C else 0,
                "stock_below_MSY_D": lambda m: 1 if m.get_region_stock("D") < m.MSY_STOCK_D else 0,
                
                # Agent counts
                "num_agents": lambda m: len(list(m.agents)),
                "num_archipelago": lambda m: sum(1 for a in m.agents if a.fisher_type == "archipelago"),
                "num_coastal": lambda m: sum(1 for a in m.agents if a.fisher_type == "coastal"),
                "num_trawler": lambda m: sum(1 for a in m.agents if a.fisher_type == "trawler"),
                "num_fishing": lambda m: sum(1 for a in m.agents if a.gone_fishing),
                "num_at_home": lambda m: sum(1 for a in m.agents if a.at_home),
                "num_bankrupt": lambda m: sum(1 for a in m.agents if a.bankrupt),
                
                # Catches
                "total_catch_daily": lambda m: sum(a.accumulated_catch for a in m.agents),
                "total_catch_cumulative": lambda m: sum(a.total_catch for a in m.agents),
                "total_catch": lambda m: m.get_total_catch_all_agents(),
                "avg_catch_per_agent": lambda m: m._safe_mean([a.total_catch for a in m.agents]),
                "catch_region_A": lambda m: sum(a.accumulated_catch for a in m.agents if a.current_region == "A"),
                "catch_region_B": lambda m: sum(a.accumulated_catch for a in m.agents if a.current_region == "B"),
                "catch_region_C": lambda m: sum(a.accumulated_catch for a in m.agents if a.current_region == "C"),
                "catch_region_D": lambda m: sum(a.accumulated_catch for a in m.agents if a.current_region == "D"),
                
                # Economic metrics
                "total_capital": lambda m: sum(a.capital for a in m.agents),
                "avg_capital": lambda m: m._safe_mean([a.capital for a in m.agents]),
                "median_capital": lambda m: m._safe_median([a.capital for a in m.agents]),
                "min_capital": lambda m: min([a.capital for a in m.agents]) if len(list(m.agents)) > 0 else 0,
                "max_capital": lambda m: max([a.capital for a in m.agents]) if len(list(m.agents)) > 0 else 0,
                "total_profit": lambda m: sum(a.total_profit for a in m.agents),
                "avg_profit": lambda m: m._safe_mean([a.total_profit for a in m.agents]),
                "total_revenue": lambda m: sum(a.total_revenue for a in m.agents),
                "total_costs": lambda m: sum(a.total_cost for a in m.agents),
                
                # Inequality
                "gini_capital": lambda m: m.calculate_gini([a.capital for a in m.agents]),
                "gini_wealth": lambda m: m.calculate_gini([a.wealth for a in m.agents]),
                "gini_catch": lambda m: m.calculate_gini([a.total_catch for a in m.agents]),
                
                # Activity
                "avg_days_at_sea": lambda m: m._safe_mean([a.days_at_sea for a in m.agents]),
                "total_trips": lambda m: sum(a.profitable_trip + a.unprofitable_trip for a in m.agents),
                "avg_success_rate": lambda m: m._safe_mean([
                    a.profitable_trip / (a.profitable_trip + a.unprofitable_trip) 
                    if (a.profitable_trip + a.unprofitable_trip) > 0 else 0 
                    for a in m.agents
                ]),
                
                # memory and perception
                "avg_growth_perception": lambda m: m._safe_mean([a.growth_perception for a in m.agents]),
                "num_perceive_scarcity": lambda m: sum(1 for a in m.agents if getattr(a, 'perceive_scarcity', False)),
                "avg_memory_size": lambda m: m._safe_mean([len(a.memory) for a in m.agents]),
                
                # Weather and time
                "bad_weather": lambda m: 1 if m.bad_weather else 0,
                "current_step": lambda m: m.current_step,
                "current_year": lambda m: m.current_step // m.YEAR,
                "current_day_of_year": lambda m: m.current_step % m.YEAR,
            },
            agent_reporters={
                # Identity
                "unique_id": "unique_id",
                "fisher_type": "fisher_type",
                "age": "age",
                
                # Financial
                "capital": "capital",
                "wealth": "wealth",
                "total_profit": "total_profit",
                "total_revenue": "total_revenue",
                "total_cost": "total_cost",
                "bankrupt": "bankrupt",
                
                # Activity
                "total_catch": "total_catch",
                "days_at_sea": "days_at_sea",
                "profitable_trips": "profitable_trip",
                "unprofitable_trips": "unprofitable_trip",
                "at_home": "at_home",
                "gone_fishing": "gone_fishing",
                "at_sea": "at_sea",
                
                # Decision-making
                "will_fish": "will_fish",
                "region_preference": "region_preference",
                "current_region": "current_region",
                "growth_perception": "growth_perception",
                "lay_low": "lay_low",
                
                # Memory
                "memory_size": lambda a: len(a.memory),
                "good_spots_count": lambda a: len(a.good_spots_memory),
            }
        )
        
        self.yearly_data = []
    
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
    
    def update_fish_stock(self, time_step_days=1):
        """Update fish stocks with yearly regrowth (logistic growth)"""
        
        """Update fish stocks with logistic growth over a time step (days)."""
                
        # Convert yearly rate to per-step rate
        effective_rate = self.GROWTH_RATE * (time_step_days / self.YEAR)
        
        # Density-based regen multipliers
        density_factor = {
            self.HIGH: 2.0,
            self.MEDIUM: 1.25,
            self.LOW: 1.0,
        }

        growth_by_region = {"A": 0, "B": 0, "C": 0, "D": 0}
        
        for pos, patch in self.patches.items():
            region = patch['region']
            if patch['region'] not in ["LAND", "NULL"]:
                current_stock = patch['fish_stock']
                carrying_capacity = patch['carrying_capacity']
                
                factor = density_factor.get(patch['density'], 1.0)
                regen_amount = current_stock * effective_rate * factor * (1 - current_stock / carrying_capacity)
            
                
                
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
        """
        Advance the model by one step (one day).
        
        Daily execution order:
        1. Determine weather
        2. Agents make decisions and execute actions
        3. Collect data
        4. (If end of year) Fish stock regeneration
        5. Check simulation end condition
        """
        
        # Determine weather
        self.determine_weather()
        
        # --- DEBUG: snapshot before fishing (monthly) ---
        if self.current_step % self.MONTH == 0:
            p = self.patches.get((7, 3), {})
            #print(f"[Before fishing] Day {self.current_step} | Patch(7,3)={p.get('fish_stock', 0):.2f} | Stock A={self.get_region_stock('A'):,.0f}")

        # All agent act
        for agent in self.agents:
            agent.step()

        # --- DEBUG: snapshot after fishing (monthly) ---
        if self.current_step % self.MONTH == 0:
            p = self.patches.get((7, 3), {})
            #print(f"[After fishing ] Day {self.current_step} | Patch(7,3)={p.get('fish_stock', 0):.2f} | Stock A={self.get_region_stock('A'):,.0f}")

        # Collect daily data
        self.datacollector.collect(self)

        # Daily regeneration
        self.update_fish_stock(time_step_days=1)

        # --- DEBUG: snapshot after regen (monthly) ---
        if self.current_step % self.MONTH == 0:
            p = self.patches.get((7, 3), {})
            #print(f"[After regen   ] Day {self.current_step} | Patch(7,3)={p.get('fish_stock', 0):.2f} | Stock A={self.get_region_stock('A'):,.0f}")

        
        # Increment step counter
        self.current_step += 1
        
        
        #Yearly action
        if self.current_step % self.YEAR == 0:
            
                # Store catches at START of year to calculate yearly increment
            if not hasattr(self, 'last_year_catches'):
                self.last_year_catches = {}
            
            current_catches = {a.unique_id: a.total_catch for a in self.agents}
            
            # Calculate yearly catch increment
            yearly_catch = 0
            for agent in self.agents:
                last_catch = self.last_year_catches.get(agent.unique_id, 0)
                yearly_catch += (agent.total_catch - last_catch)
            
            # Update for next year
            self.last_year_catches = current_catches
        
            # Collect yearly data
            yearly_summary = self.collect_yearly_data()
            
            if self.verbose:
                year = self.current_step // self.YEAR
                print(f"\n{'='*60}")
                print(f"YEAR {year} COMPLETED")
                print(f"{'='*60}")
                print(f"Stocks: A={yearly_summary['stock_A']:,.0f} ({yearly_summary['stock_A_pct_K']:.1%}), "
                    f"B={yearly_summary['stock_B']:,.0f} ({yearly_summary['stock_B_pct_K']:.1%})")
                print(f"Yearly catch: {yearly_catch:,.0f}")  # ← Capture de l'année
                print(f"Total catch: {yearly_summary['total_catch_all']:,.0f}")
                print(f"Avg capital: {yearly_summary['total_capital']/len(list(self.agents)):,.2f}")
                print(f"Gini capital: {yearly_summary['gini_capital']:.3f}")
                print(f"Success rate: {yearly_summary['avg_success_rate']:.1%}")
                print(f"{'='*60}\n")
                
                total = sum(agent.total_catch for agent in self.agents)
                print(f"Year {self.current_step//365}: Real total_catch = {total}")
                
                # Debug par type
                for ftype in ["archipelago", "coastal", "trawler"]:
                    agents = [a for a in self.agents if a.fisher_type == ftype]
                    if agents:
                        catch = sum(a.total_catch for a in agents)
                        print(f"  {ftype}: {len(agents)} agents, {catch} total catch")
                
        # Check if simulation should end
        if self.current_step >= self.end_of_sim:
            self.running = False
            if self.verbose:
                self.print_final_summary()
            
    def print_final_summary(self):
        """Print comprehensive summary at end of simulation"""
        print("\n" + "="*80)
        print("SIMULATION FINALE SUMMARY")
        print("="*80)
        
        agents_list = list(self.agents)
        
        print(f"\nDuration: {self.current_step} days ({self.current_step/self.YEAR:.1f} years)")
        print(f"Agents: {len(agents_list)} total")
        
        print(f"\n--- FISH STOCKS ---")
        print(f"Region A: {self.get_region_stock('A'):>10,.0f} / {self.CARRYING_CAPACITY_A:,.0f} ({self.get_region_stock('A')/self.CARRYING_CAPACITY_A:.1%})")
        print(f"Region B: {self.get_region_stock('B'):>10,.0f} / {self.CARRYING_CAPACITY_B:,.0f} ({self.get_region_stock('B')/self.CARRYING_CAPACITY_B:.1%})")
        print(f"Region C: {self.get_region_stock('C'):>10,.0f} / {self.CARRYING_CAPACITY_C:,.0f} ({self.get_region_stock('C')/self.CARRYING_CAPACITY_C:.1%})")
        print(f"Region D: {self.get_region_stock('D'):>10,.0f} / {self.CARRYING_CAPACITY_D:,.0f} ({self.get_region_stock('D')/self.CARRYING_CAPACITY_D:.1%})")
        print(f"TOTAL:    {self.get_total_stock():>10,.0f}")
        
        print(f"\n--- ECONOMICS ---")
        total_catch = sum(a.total_catch for a in agents_list)
        total_capital = sum(a.capital for a in agents_list)
        total_profit = sum(a.total_profit for a in agents_list)
        
        print(f"Total catch:   {total_catch:>12,.0f}")
        print(f"Total capital: {total_capital:>12,.2f}")
        print(f"Total profit:  {total_profit:>12,.2f}")
        print(f"Avg capital:   {total_capital/len(agents_list):>12,.2f}")
        
        print(f"\n--- INEQUALITY ---")
        print(f"Gini capital: {self.calculate_gini([a.capital for a in agents_list]):.3f}")
        print(f"Gini wealth:  {self.calculate_gini([a.wealth for a in agents_list]):.3f}")
        print(f"Gini catch:   {self.calculate_gini([a.total_catch for a in agents_list]):.3f}")
        
        print(f"\n--- BY FISHER TYPE ---")
        for ftype in ["archipelago", "coastal", "trawler"]:
            type_agents = [a for a in agents_list if a.fisher_type == ftype]
            if type_agents:
                avg_catch = sum(a.total_catch for a in type_agents) / len(type_agents)
                avg_capital = sum(a.capital for a in type_agents) / len(type_agents)
                bankrupt = sum(1 for a in type_agents if a.bankrupt)
                print(f"{ftype:>12}: {len(type_agents):>3} agents, "
                    f"avg catch={avg_catch:>8,.0f}, "
                    f"avg capital={avg_capital:>8,.2f}, "
                    f"bankrupt={bankrupt}")
        
        print("="*80 + "\n")
        
    def export_data(self, filename_prefix='fibe_output', directory='./results/'):
        """
        Export collected data to CSV files.
        
        Args:
            filename_prefix: Prefix for output files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = directory + f"{timestamp}/"
        os.makedirs(directory, exist_ok=True)
        
        # Export daily model data
        model_df = self.datacollector.get_model_vars_dataframe()
        model_df.to_csv(f"{os.path.join(directory, f"{filename_prefix}_model_{timestamp}.csv")}", index=False)
        if self.verbose:
            print(f"Exported: {filename_prefix}_model_{timestamp}.csv ({len(model_df)} rows)")
        
        # Export daily agent data
        agent_df = self.datacollector.get_agent_vars_dataframe()
        agent_df.to_csv(f"{os.path.join(directory, f"{filename_prefix}_agent_{timestamp}.csv")}", index=False)
        if self.verbose:
            print(f"Exported: {filename_prefix}_agents_{timestamp}.csv ({len(agent_df)} rows)")
        
        if self.yearly_data:
            yearly_df = pd.DataFrame(self.yearly_data)
            yearly_df.to_csv(f"{os.path.join(directory, f"{filename_prefix}_yearly_{timestamp}.csv")}", index=False)
            if self.verbose:
                print(f"Exported: {filename_prefix}_yearly_{timestamp}.csv ({len(yearly_df)} rows)")
        
        if self.verbose:
            print(f"\n All data exported with timestamp: {timestamp}")
        
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
        
        if self.verbose:
            print(f"Capacités régionales recalculées:")
            print(f"  Region A: {self.CARRYING_CAPACITY_A} (MSY: {self.MSY_STOCK_A})")
            print(f"  Region B: {self.CARRYING_CAPACITY_B} (MSY: {self.MSY_STOCK_B})")
            print(f"  Region C: {self.CARRYING_CAPACITY_C} (MSY: {self.MSY_STOCK_C})")
            print(f"  Region D: {self.CARRYING_CAPACITY_D} (MSY: {self.MSY_STOCK_D})")

    def determine_weather(self):
        """
        Determine daily weather conditions (stochastic).
        Bad weather occurs with 10% probability per day.
        """
        self.bad_weather = random.random() < self.bad_weather_probability
        return self.bad_weather
    
    def run_model(self, steps=None):
        """
        Run the model for a specified number of steps or until end_of_sim.
        
        Args:
            steps: Number of steps to run (if None, runs until end_of_sim)
        """
        
        if steps is None:
            steps = self.end_of_sim
        
        if self.verbose:    
            print(f"Starting simulation for {steps} days ({steps/self.YEAR:.1f} years)")
            print(f"Agents: {self.num_archipelago} archipelago, {self.num_coastal} coastal, {self.num_trawler} trawler")
            print("=" * 60) 
            
        for _ in range(steps):
            self.step()
            
            # Print progress every month
            if self.current_step % self.MONTH == 0:
                month = self.current_step // self.MONTH
                # Print progress every month
            if self.current_step % self.MONTH == 0:
                month = self.current_step // self.MONTH
                patch_7_3 = self.patches.get((7, 3), {}).get('fish_stock', 0)
                #print(f"Month {month} - Day {self.current_step} - Stock A: {self.get_region_stock('A'):,.0f} - Patch(7,3): {patch_7_3:,.2f}")
  
            if not self.running:
                break
        
        if self.verbose:    
            print("=" * 60)
            print(f"Simulation completed after {self.current_step} days ({self.current_step/self.YEAR:.1f} years)")

    def get_model_summary(self):
        """
        Get a summary of current model state.
        
        Returns:
            dict: Summary statistics
        """
        
        agents_list = list(self.agents)
        num_agents = len(agents_list)
        
        return{
            'current_step': self.current_step,
            'current_year': self.current_step // self.YEAR,
            'current_day': self.current_step % self.YEAR,
            'num_agents': num_agents,
            'num_fishing': sum(1 for a in agents_list if a.gone_fishing),
            'num_at_home': sum(1 for a in agents_list if a.at_home),
            'total_stock': self.get_total_stock(),
            'stock_A': self.get_region_stock("A"),
            'stock_B': self.get_region_stock("B"),
            'stock_C': self.get_region_stock("C"),
            'stock_D': self.get_region_stock("D"),
            'total_catch': sum(a.total_catch for a in agents_list),
            'avg_capital': sum(a.capital for a in agents_list) / num_agents if num_agents > 0 else 0,
            'bad_weather': self.bad_weather
        }
        
    def _safe_mean(self, values):
        """Calculate mean safely"""
        if not values or len(values) == 0:
            return 0
        return sum(values) / len(values)
    
    def _safe_median(self, values):
        """Calculate median safely"""
        if not values or len(values) == 0:
            return 0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return(sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            return sorted_values[n//2]
        
    def calculate_gini(self, values):
        """
        Calculate Gini coefficient for inequality measure.
        
        Args:
            values: List of values (capital, wealth, catch, etc.)
            
        Returns:
            float: Gini coefficient (0 = perfect equality, 1 = perfect inequality)
        """
        if not values or len(values) == 0:
            return 0
        
        values = [max(0, v) for v in values]
        
        if sum(values) == 0:
            return 0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        cumsum = 0
        for i, value in enumerate(sorted_values):
            cumsum += (i + 1) * value
            
        gini = (2 * cumsum) / (n * sum(sorted_values)) - (n + 1) / n
        
        return gini
    
    def collect_yearly_data(self):
        """
        Collect yearly summary data (called at end of each year).
        More detailed than daily datacollector.
        """
        year = self.current_step // self.YEAR
        
        agents_list = list(self.agents)
        
        archipelago_agents = [a for a in agents_list if a.fisher_type == "archipelago"]
        coastal_agents = [a for a in agents_list if a.fisher_type == "coastal"]
        trawler_agents = [a for a in agents_list if a.fisher_type == "trawler"]
        
        yearly_summary = {
            'year': year,
            'step': self.current_step,
            
            # === STOCKS ===
            'stock_A': self.get_region_stock("A"),
            'stock_B': self.get_region_stock("B"),
            'stock_C': self.get_region_stock("C"),
            'stock_D': self.get_region_stock("D"),
            'total_stock': self.get_total_stock(),
            'stock_A_pct_K': self.get_region_stock("A") / self.CARRYING_CAPACITY_A if self.CARRYING_CAPACITY_A > 0 else 0,
            'stock_B_pct_K': self.get_region_stock("B") / self.CARRYING_CAPACITY_B if self.CARRYING_CAPACITY_B > 0 else 0,
            'stock_C_pct_K': self.get_region_stock("C") / self.CARRYING_CAPACITY_C if self.CARRYING_CAPACITY_C > 0 else 0,
            'stock_D_pct_K': self.get_region_stock("D") / self.CARRYING_CAPACITY_D if self.CARRYING_CAPACITY_D > 0 else 0,
            
            # === AGENTS ===
            'num_agents': len(agents_list),
            'num_archipelago': len(archipelago_agents),
            'num_coastal': len(coastal_agents),
            'num_trawler': len(trawler_agents),
            'num_bankrupt': sum(1 for a in agents_list if a.bankrupt),
            
            # === CATCHES (by type) ===
            'total_catch_archipelago': sum(a.total_catch for a in archipelago_agents),
            'total_catch_coastal': sum(a.total_catch for a in coastal_agents),
            'total_catch_trawler': sum(a.total_catch for a in trawler_agents),
            'total_catch_all': sum(a.total_catch for a in agents_list),
            'avg_catch_archipelago': self._safe_mean([a.total_catch for a in archipelago_agents]),
            'avg_catch_coastal': self._safe_mean([a.total_catch for a in coastal_agents]),
            'avg_catch_trawler': self._safe_mean([a.total_catch for a in trawler_agents]),
            
            # === ECONOMICS (by type) ===
            'avg_capital_archipelago': self._safe_mean([a.capital for a in archipelago_agents]),
            'avg_capital_coastal': self._safe_mean([a.capital for a in coastal_agents]),
            'avg_capital_trawler': self._safe_mean([a.capital for a in trawler_agents]),
            'total_capital': sum(a.capital for a in agents_list),
            'total_profit': sum(a.total_profit for a in agents_list),
            'total_revenue': sum(a.total_revenue for a in agents_list),
            'total_costs': sum(a.total_cost for a in agents_list),
            
            # === INEQUALITY ===
            'gini_capital': self.calculate_gini([a.capital for a in agents_list]),
            'gini_wealth': self.calculate_gini([a.wealth for a in agents_list]),
            'gini_catch': self.calculate_gini([a.total_catch for a in agents_list]),
            
            # === ACTIVITY ===
            'total_trips': sum(a.profitable_trip + a.unprofitable_trip for a in agents_list),
            'total_profitable_trips': sum(a.profitable_trip for a in agents_list),
            'total_unprofitable_trips': sum(a.unprofitable_trip for a in agents_list),
            'avg_success_rate': self._safe_mean([
                a.profitable_trip / (a.profitable_trip + a.unprofitable_trip) 
                if (a.profitable_trip + a.unprofitable_trip) > 0 else 0 
                for a in agents_list
            ]),
            'avg_days_at_sea': self._safe_mean([a.days_at_sea for a in agents_list]),
        }
        
        self.yearly_data.append(yearly_summary)
        
        return yearly_summary
    
    def get_total_catch_all_agents(model):
        """Somme des captures de TOUS les agents"""
        return sum(agent.total_catch for agent in model.agents)
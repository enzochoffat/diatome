from time import sleep, time

from collections import defaultdict
from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from .agent import FisherAgent
from . import config
import random
import pandas as pd
from datetime import datetime
import os
import numpy as np

from src.config import get_hotspots_for_step
from src.Couplage.couplage import Coupling
from src.ecospace_outputs import get_ecospace_data
from src import ecospace_outputs
class FisheryModel(Model):
    def __init__(
        self,
        end_of_sim,
        num_archipelago,
        num_coastal,
        num_trawler,
        verbose=True,
        growth_rate=None,
        fish_price=None,
        bad_weather_probability=None,
        initial_capital=None,
        archipelago_names=None,
        coastal_names=None,
        trawler_names=None,
        coupling=None,
    ):
        super().__init__()
        
        self.coupling = coupling
        self.verbose = verbose
        
        self.current_step = 0
        self.end_of_sim = end_of_sim

        self.num_archipelago = num_archipelago
        self.num_coastal = num_coastal
        self.num_trawler = num_trawler

        self.archipelago_names = archipelago_names
        self.coastal_names = coastal_names
        self.trawler_names = trawler_names

        # Define time constants
        self.WEEK = config.WEEK
        self.MONTH = config.MONTH
        self.SEASON = config.SEASON
        self.HALFYEAR = config.HALFYEAR
        self.YEAR = config.YEAR
        
        # Weather tracking
        self.bad_weather = False
        self.bad_weather_probability = (
            config.BAD_WEATHER_PROBABILITY
            if bad_weather_probability is None
            else float(bad_weather_probability)
        )

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
        self.HOTSPOTS_A = get_hotspots_for_step(0, 'A')
        self.HOTSPOTS_B = get_hotspots_for_step(0, 'B')
        self.HOTSPOTS_C = get_hotspots_for_step(0, 'C')
        self.HOTSPOTS_D = get_hotspots_for_step(0, 'D')
        # Define growth rate
        self.GROWTH_RATE = config.GROWTH_RATE if growth_rate is None else float(growth_rate)
        
        self.FISH_PRICE = config.FISH_PRICE if fish_price is None else float(fish_price)
        self.initial_capital = config.INITIAL_CAPITAL if initial_capital is None else float(initial_capital)
        
        self.init_stock_size = config.INIT_STOCK_SIZE
        
        # Initialize spatial grid(50x56)
        self.grid = MultiGrid(config.GRID_WIDTH, config.GRID_HEIGHT, torus=False)
        
        self._region_stock_cache = {"A": 0, "B": 0, "C": 0, "D": 0, "total": 0}
        self._daily_agent_metrics = {}
        self._monthly_agent_rows = []
        self.yearly_data = []
        self.last_year_catches = {}

        # Initialize patches with fish stocks
        self.init_patches()
        self._initialize_region_stock_cache()
        
        if self.verbose:
            print("\n" + "="*60)
            print("HOTSPOT DISTRIBUTION")
            print("="*60)
            self.validate_hotspot_distribution()
            print("="*60 + "\n")
        
        self._recalculate_regional_capacities()
        self._create_agents()
        
        self.num_fishing_midday = sum(1 for a in self.agents if a.gone_fishing)
        self.num_at_home_midday = sum(1 for a in self.agents if a.at_home)
        self.num_fished_today = 0
        # Data collector

        self.datacollector = self._build_datacollector()


        self._build_daily_agent_metrics_cache()

        self.datacollector.collect(self)  # Collect initial data at step 0

    def _initialize_region_stock_cache(self):
        cache = {"A": 0, "B": 0, "C": 0, "D": 0, "TOTAL": 0}

        for patch in self.patches.values():
            region = patch["region"]
            fish_stock = patch["fish_stock"]
            if region in ("A", "B", "C", "D"):
                cache[region] += fish_stock
                cache["TOTAL"] += fish_stock

        self._region_stock_cache = cache

    def _refresh_region_stocks_cache(self):
        self._initialize_region_stock_cache()

    def _set_patch_fish_stock(self, pos, new_stock):
        """
        Set the fish stock of one patch and update regional cache incrementally.
        Returns the new stock.
        """
        patch = self.patches[pos]
        old_stock = patch["fish_stock"]
        new_stock = max(0, new_stock)
        delta = new_stock - old_stock

        if delta:
            patch["fish_stock"] = new_stock
            region = patch["region"]
            if region in ("A", "B", "C", "D"):
                self._region_stock_cache[region] += delta
                self._region_stock_cache["TOTAL"] += delta
        else:
            patch["fish_stock"] = new_stock

        return patch["fish_stock"]
    
    def _adjust_patch_fish_stock(self, pos, delta):
        """
        Add/subtract a delta to one patch and update regional cache incrementally.
        Returns the new stock.
        """
        patch = self.patches[pos]
        current_stock = patch["fish_stock"]
        return self._set_patch_fish_stock(pos, current_stock + delta)

    def _build_daily_agent_metrics_cache(self):
        agents = list(self.agents)

        capitals = []
        wealths = []
        catches = []
        profits = []
        revenues = []
        costs = []
        days_at_sea = []
        growth_perceptions = []
        memory_sizes = []

        by_type_count = {
            "archipelago": 0,
            "coastal": 0,
            "trawler": 0
        }

        by_region_catch = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0
        }

        num_bankrupt = 0   
        total_catch_daily = 0
        total_catch_cumulative = 0
        total_capital = 0
        total_profit = 0
        total_revenue = 0
        total_costs = 0
        total_trips = 0
        num_perceive_scarcity = 0


        success_rate_sum = 0.0
        success_rate_count = 0

        min_capital = None
        max_capital = None

        for a in agents:
            ftype = a.fisher_type
            if ftype in by_type_count:
                by_type_count[ftype] += 1

            if a.bankrupt:
                num_bankrupt += 1

            total_catch_daily += a.accumulated_catch
            total_catch_cumulative += a.total_catch
            total_capital += a.capital
            total_profit += a.total_profit
            total_revenue += a.total_revenue
            total_costs += a.total_cost

            capitals.append(a.capital)
            wealths.append(a.wealth)
            catches.append(a.total_catch)
            profits.append(a.total_profit)
            revenues.append(a.total_revenue)
            costs.append(a.total_cost)
            days_at_sea.append(a.days_at_sea)
            growth_perceptions.append(a.growth_perception)
            memory_sizes.append(len(a.memory))

            if getattr(a, "perceive_scarcity", False):
                num_perceive_scarcity += 1

            trips = a.profitable_trip + a.unprofitable_trip
            total_trips += trips
            if trips > 0:
                success_rate_sum += a.profitable_trip / trips
                success_rate_count += 1

            if a.current_region in by_region_catch:
                by_region_catch[a.current_region] += a.accumulated_catch

            if min_capital is None or a.capital < min_capital:
                min_capital = a.capital
            if max_capital is None or a.capital > max_capital:
                max_capital = a.capital

        
        self._daily_agent_metrics = {
            "num_agents": len(agents),
            "num_archipelago": by_type_count["archipelago"],
            "num_coastal": by_type_count["coastal"],
            "num_trawler": by_type_count["trawler"],
            "num_bankrupt": num_bankrupt,

            "total_catch_daily": total_catch_daily,
            "total_catch_cumulative": total_catch_cumulative,

            "total_capital": total_capital,
            "avg_capital": self._safe_mean(capitals),
            "median_capital": self._safe_median(capitals),
            "min_capital": min_capital if min_capital is not None else 0,
            "max_capital": max_capital if max_capital is not None else 0,

            "total_profit": total_profit,
            "avg_profit": self._safe_mean(profits),
            "total_revenue": total_revenue,
            "total_costs": total_costs,

            "gini_capital": self.calculate_gini(capitals) if capitals else 0,
            "gini_wealth": self.calculate_gini(wealths) if wealths else 0,
            "gini_catch": self.calculate_gini(catches) if catches else 0,

            "avg_days_at_sea": self._safe_mean(days_at_sea),
            "total_trips": total_trips,
            "avg_success_rate": (
                success_rate_sum / success_rate_count if success_rate_count else 0
            ),

            "avg_growth_perception": self._safe_mean(growth_perceptions),
            "num_perceive_scarcity": num_perceive_scarcity,
            "avg_memory_size": self._safe_mean(memory_sizes),

            "catch_region_A": by_region_catch["A"],
            "catch_region_B": by_region_catch["B"],
            "catch_region_C": by_region_catch["C"],
            "catch_region_D": by_region_catch["D"],
        }


    def _append_daily_agent_rows_for_monthly_export(self):
        """
        Stocke uniquement les lignes du jour pour l'export mensuel,
        afin d'éviter de reconstruire tout l'historique depuis DataCollector.
        """
        step_value = self.current_step

        for a in self.agents:
            self._monthly_agent_rows.append({
                "step": step_value,
                "unique_id": a.unique_id,
                "fisher_type": a.fisher_type,
                "age": a.age,

                "capital": a.capital,
                "wealth": a.wealth,
                "total_profit": a.total_profit,
                "total_revenue": a.total_revenue,
                "total_cost": a.total_cost,
                "bankrupt": a.bankrupt,

                "total_catch": a.total_catch,
                "days_at_sea": a.days_at_sea,
                "profitable_trips": a.profitable_trip,
                "unprofitable_trips": a.unprofitable_trip,
                "at_home": a.at_home,
                "gone_fishing": a.gone_fishing,
                "fished_today": a.fished_today,
                "at_sea": a.at_sea,
                "current_location": a.current_location if a.gone_fishing else (0, 0),
                "catch": a.accumulated_catch if a.gone_fishing else 0,

                "will_fish": a.will_fish,
                "region_preference": a.region_preference,
                "current_region": a.current_region,
                "growth_perception": a.growth_perception,
                "lay_low": a.lay_low,

                "memory_size": len(a.memory),
                "good_spots_count": len(a.good_spots_memory),
            })


    def _export_monthly_agent_buffer(self):
        if not self._monthly_agent_rows:
            return

        os.makedirs("./results/biomass", exist_ok=True)
        df = pd.DataFrame(self._monthly_agent_rows)
        output_path = os.path.join("./results/biomass", f"agent_{self.current_step}.csv")
        df.to_csv(output_path, index=False)

        if self.verbose:
            print(f"Exported: agent_{self.current_step}.csv ({len(df)} rows)")

        self._monthly_agent_rows.clear()


    def _wait_for_coupling_update(self, json_path="configs/config.json", poll_interval=0.5):
        """
        Attend qu'un fichier de config soit modifié.
        Retourne species_maps, current_step_val dès qu'une mise à jour est détectée.
        """
        species_maps, last_step = Coupling.read_csv_biomass(self)
        current_step_val = last_step

        last_modified_time = 0
        current_modified_time = 0

        if os.path.exists(json_path):
            last_modified_time = os.path.getmtime(json_path)
            current_modified_time = last_modified_time

        while current_modified_time <= last_modified_time and self.current_step != 28:
            sleep(poll_interval)

            if os.path.exists(json_path):
                current_modified_time = os.path.getmtime(json_path)
                if current_modified_time > last_modified_time:
                    species_maps, current_step_val = Coupling.read_csv_biomass(self)
                    if self.verbose:
                        print(
                            f"File {json_path} updated. Proceeding with biomass update for step {current_step_val}."
                        )
            else:
                if self.verbose:
                    print(f"File {json_path} not found. Waiting for the file to be created...")

        return species_maps, current_step_val


    def _build_datacollector(self):
        return DataCollector(
            model_reporters={
                # =========================
                # Fish stocks
                # =========================
                "stock_A": lambda m: m._region_stock_cache["A"],
                "stock_B": lambda m: m._region_stock_cache["B"],
                "stock_C": lambda m: m._region_stock_cache["C"],
                "stock_D": lambda m: m._region_stock_cache["D"],
                "total_stock": lambda m: m._region_stock_cache["TOTAL"],
                "stock_below_MSY_A": lambda m: 1 if m._region_stock_cache["A"] < m.MSY_STOCK_A else 0,
                "stock_below_MSY_B": lambda m: 1 if m._region_stock_cache["B"] < m.MSY_STOCK_B else 0,
                "stock_below_MSY_C": lambda m: 1 if m._region_stock_cache["C"] < m.MSY_STOCK_C else 0,
                "stock_below_MSY_D": lambda m: 1 if m._region_stock_cache["D"] < m.MSY_STOCK_D else 0,

                # =========================
                # Agent counts
                # =========================
                "num_agents": lambda m: m._daily_agent_metrics["num_agents"],
                "num_archipelago": lambda m: m._daily_agent_metrics["num_archipelago"],
                "num_coastal": lambda m: m._daily_agent_metrics["num_coastal"],
                "num_trawler": lambda m: m._daily_agent_metrics["num_trawler"],
                "num_fishing": lambda m: m.num_fishing_midday,
                "num_at_home": lambda m: m.num_at_home_midday,
                "num_fished_today": lambda m: m.num_fished_today,
                "num_bankrupt": lambda m: m._daily_agent_metrics["num_bankrupt"],

                # =========================
                # Catches
                # =========================
                "total_catch_daily": lambda m: m._daily_agent_metrics["total_catch_daily"],
                "total_catch_cumulative": lambda m: m._daily_agent_metrics["total_catch_cumulative"],
                "total_catch": lambda m: m.get_total_catch_all_agents(),
                "avg_catch_per_agent": lambda m: (
                    m._daily_agent_metrics["total_catch_cumulative"] / m._daily_agent_metrics["num_agents"]
                    if m._daily_agent_metrics["num_agents"] else 0
                ),
                "catch_region_A": lambda m: m._daily_agent_metrics["catch_region_A"],
                "catch_region_B": lambda m: m._daily_agent_metrics["catch_region_B"],
                "catch_region_C": lambda m: m._daily_agent_metrics["catch_region_C"],
                "catch_region_D": lambda m: m._daily_agent_metrics["catch_region_D"],

                # =========================
                # Economic metrics
                # =========================
                "total_capital": lambda m: m._daily_agent_metrics["total_capital"],
                "avg_capital": lambda m: m._daily_agent_metrics["avg_capital"],
                "median_capital": lambda m: m._daily_agent_metrics["median_capital"],
                "min_capital": lambda m: m._daily_agent_metrics["min_capital"],
                "max_capital": lambda m: m._daily_agent_metrics["max_capital"],
                "total_profit": lambda m: m._daily_agent_metrics["total_profit"],
                "avg_profit": lambda m: m._daily_agent_metrics["avg_profit"],
                "total_revenue": lambda m: m._daily_agent_metrics["total_revenue"],
                "total_costs": lambda m: m._daily_agent_metrics["total_costs"],

                # =========================
                # Inequality
                # =========================
                "gini_capital": lambda m: m._daily_agent_metrics["gini_capital"],
                "gini_wealth": lambda m: m._daily_agent_metrics["gini_wealth"],
                "gini_catch": lambda m: m._daily_agent_metrics["gini_catch"],

                # =========================
                # Activity
                # =========================
                "avg_days_at_sea": lambda m: m._daily_agent_metrics["avg_days_at_sea"],
                "total_trips": lambda m: m._daily_agent_metrics["total_trips"],
                "avg_success_rate": lambda m: m._daily_agent_metrics["avg_success_rate"],

                # =========================
                # Memory and perception
                # =========================
                "avg_growth_perception": lambda m: m._daily_agent_metrics["avg_growth_perception"],
                "num_perceive_scarcity": lambda m: m._daily_agent_metrics["num_perceive_scarcity"],
                "avg_memory_size": lambda m: m._daily_agent_metrics["avg_memory_size"],

                # =========================
                # Weather and time
                # =========================
                "bad_weather": lambda m: 1 if m.bad_weather else 0,
                "current_step": lambda m: m.current_step,
                "current_year": lambda m: m.current_step // m.YEAR,
                "current_day_of_year": lambda m: m.current_step % m.YEAR,
            },
            agent_reporters={
                # =========================
                # Identity
                # =========================
                "step": lambda a: a.model.current_step,
                "unique_id": "unique_id",
                "fisher_type": "fisher_type",
                "age": "age",

                # =========================
                # Financial
                # =========================
                "capital": "capital",
                "wealth": "wealth",
                "total_profit": "total_profit",
                "total_revenue": "total_revenue",
                "total_cost": "total_cost",
                "bankrupt": "bankrupt",

                # =========================
                # Activity
                # =========================
                "total_catch": "total_catch",
                "days_at_sea": "days_at_sea",
                "profitable_trips": "profitable_trip",
                "unprofitable_trips": "unprofitable_trip",
                "at_home": "at_home",
                "gone_fishing": "gone_fishing",
                "fished_today": "fished_today",
                "at_sea": "at_sea",
                "current_location": lambda a: a.current_location if a.gone_fishing else (0, 0),
                "catch": lambda a: a.accumulated_catch if a.gone_fishing else 0,

                # =========================
                # Decision-making
                # =========================
                "will_fish": "will_fish",
                "region_preference": "region_preference",
                "current_region": "current_region",
                "growth_perception": "growth_perception",
                "lay_low": "lay_low",

                # =========================
                # Memory
                # =========================
                "memory_size": lambda a: len(a.memory),
                "good_spots_count": lambda a: len(a.good_spots_memory),
            }
        )


    def _create_agents(self):
        """Create fisher agents of different types"""
        
        agent_id = 0
        
        for _ in range(self.num_archipelago):
            agent = FisherAgent(agent_id, self, "archipelago", initial_capital=self.initial_capital, name=self.archipelago_names[agent_id] if self.archipelago_names else None)
            start_pos = self._get_random_position_in_region("A")
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = "A"
                agent.region_preference = "A"
            agent_id += 1
            
        for _ in range(self.num_coastal):
            agent = FisherAgent(agent_id, self, "coastal", initial_capital=self.initial_capital, name=self.coastal_names[agent_id - self.num_archipelago] if self.coastal_names else None)
            region = self.random.choice(["A", "B"])
            start_pos = self._get_random_position_in_region(region)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = region
            agent_id += 1
            
        for _ in range(self.num_trawler):
            agent = FisherAgent(agent_id, self, "trawler", initial_capital=self.initial_capital, name=self.trawler_names[agent_id - self.num_archipelago - self.num_coastal] if self.trawler_names else None)
            region = self.random.choice(config.TRAWLER_ACCESSIBLE_REGIONS)
            start_pos = self._get_random_position_in_region(region)
            if start_pos:
                self.grid.place_agent(agent, start_pos)
                agent.current_location = start_pos
                agent.current_region = region
            agent_id += 1
    
    def _get_random_position_in_region(self, region):
        """Get a random valid patch position in a region"""
        candidates = [pos for pos, patch in self.patches.items() 
                     if patch['region'] == region]
        return random.choice(candidates) if candidates else None
    

    def init_patches(self):
        self._prepare_spatial_indexes()
        self._build_density_offsets()
        self._build_density_map_exact()

        width = self.grid.width
        height = self.grid.height
        growth_rate = self.GROWTH_RATE

        patches = {}

        # Bind locaux pour accélérer légèrement la boucle Python
        get_region = self.get_region
        get_density = self.get_density
        get_carrying_capacity = self.get_carrying_capacity
        get_initial_fish_stock = self.get_initial_fish_stock

        ecospace_data, species_names = ecospace_outputs.get_ecospace_data()
        sum_data = np.sum(ecospace_data, axis=2)
        print(f"shape sum_data: {sum_data.shape}, width: {width}, height: {height}")
        for x in range(height):
            for y in range(width):
                region = get_region(x, y)
                density = get_density(x, y, region)
                carrying_capacity = get_carrying_capacity(region, density)
                fish_stock = sum_data[x, y] if region not in ("LAND", "NULL") else 0
                #if region not in ("LAND", "NULL") and density != "low":
                #    print(f"Patch ({x}, {y}): Region={region}, Density={density}, Carrying Capacity={carrying_capacity}, Initial Fish Stock={fish_stock}")

                patches[(x, y)] = {
                    'region': region,
                    'density': density,
                    'fish_stock': fish_stock,
                    'carrying_capacity': carrying_capacity,
                    'growth_rate': growth_rate,
                    'regen_amount': 0,
                    'patch_stock_after_regrowth': fish_stock
                }

        self.patches = patches


        
    
    def _prepare_spatial_indexes(self):
        
        # Régions / LAND : membership O(1)
        self._land_set = {tuple(coord) for coord in self.LAND}
        self._region_a_set = {tuple(coord) for coord in self.REGION_A}
        self._region_b_set = {tuple(coord) for coord in self.REGION_B}
        self._region_c_set = {tuple(coord) for coord in self.REGION_C}
        self._region_d_set = {tuple(coord) for coord in self.REGION_D}

        # Hotspots : liste pour parcourir / set pour membership rapide
        self._hotspots_a_list = [tuple(coord) for coord in self.HOTSPOTS_A]
        self._hotspots_b_list = [tuple(coord) for coord in self.HOTSPOTS_B]
        self._hotspots_c_list = [tuple(coord) for coord in self.HOTSPOTS_C]
        self._hotspots_d_list = [tuple(coord) for coord in self.HOTSPOTS_D]
        for point in self._hotspots_a_list:
              # Ensure the region is set correctly for each hotspot
            print(f"Hotspot A at {point} is in region: {self.get_region(point[0], point[1])}")
        for point in self._hotspots_b_list:
            self.get_region(point[0], point[1])  # Ensure the region is set correctly for each hotspot
            print(f"Hotspot B at {point} is in region: {self.get_region(point[0], point[1])}")
        for point in self._hotspots_c_list:
            self.get_region(point[0], point[1])  # Ensure the region is set correctly for each hotspot
            print(f"Hotspot C at {point} is in region: {self.get_region(point[0], point[1])}")
        for point in self._hotspots_d_list:
            self.get_region(point[0], point[1])  # Ensure the region is set correctly for each hotspot
            print(f"Hotspot D at {point} is in region: {self.get_region(point[0], point[1])}")

        self._hotspots_a_set = set(self._hotspots_a_list)
        self._hotspots_b_set = set(self._hotspots_b_list)
        self._hotspots_c_set = set(self._hotspots_c_list)
        self._hotspots_d_set = set(self._hotspots_d_list)


        self._region_sets = {
                'A': self._region_a_set,
                'B': self._region_b_set,
                'C': self._region_c_set,
                'D': self._region_d_set,
            }

        self._hotspots_lists = {
                'A': self._hotspots_a_list,
                'B': self._hotspots_b_list,
                'C': self._hotspots_c_list,
                'D': self._hotspots_d_list,
            }

        self._hotspots_sets = {
                'A': self._hotspots_a_set,
                'B': self._hotspots_b_set,
                'C': self._hotspots_c_set,
                'D': self._hotspots_d_set,
            }



    def _build_density_offsets(self):
        # HIGH : distance <= 3
        high_offsets = []

        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    high_offsets.append((dx, dy))

        # MEDIUM_ONLY : 3 < distance <= 5
        medium_only_offsets = []

        for dx in range(-5, 6):
            for dy in range(-5, 6):
                d2 = dx * dx + dy * dy
                if 9 < d2 <= 25:
                    medium_only_offsets.append((dx, dy))

        self._high_offsets = high_offsets
        self._medium_only_offsets = medium_only_offsets


    def _build_density_map_exact(self):
        self._density_map_by_region = {
            'A': {},
            'B': {},
            'C': {},
            'D': {},
        }

        for region_label in ('A', 'B', 'C', 'D'):
            region_coords = self._region_sets[region_label]
            hotspots = self._hotspots_lists[region_label]
            density_map = self._density_map_by_region[region_label]

            # 1) Marquage MEDIUM (anneau 3 < d <= 5)
            # setdefault évite d'écraser plus tard inutilement
            for hx, hy in hotspots:
                for dx, dy in self._medium_only_offsets:
                    coord = (hx + dx, hy + dy)
                    if coord in region_coords:
                        density_map.setdefault(coord, self.MEDIUM)

            # 2) Marquage HIGH (d <= 3) -> écrase MEDIUM si besoin
            for hx, hy in hotspots:
                for dx, dy in self._high_offsets:
                    coord = (hx + dx, hy + dy)
                    if coord in region_coords:
                        density_map[coord] = self.HIGH

    def get_region(self, x, y):
        
        coord = (x, y)

        if coord in self._land_set:
            return 'LAND'
        elif coord in self._region_a_set:
            return 'A'
        elif coord in self._region_b_set:
            return 'B'
        elif coord in self._region_c_set:
            return 'C'
        elif coord in self._region_d_set:
            return 'D'
        else:
            return 'NULL'

    
    def get_density(self, x, y, region):
        
        
        if region == 'LAND' or region == 'NULL':
                return None

        return self._density_map_by_region[region].get((x, y), self.LOW)


            
    
    def get_carrying_capacity(self, region, density):
        """Get carrying capacity based on region and density"""
        if region == "LAND" or region == "NULL":
            return 0
    
        # Normaliser la densité pour la comparaison (case-insensitive)
        if density is None:
            return 0
    
        density_upper = density.upper() if isinstance(density, str) else str(density).upper()
    
        if density_upper == "HIGH":
            base_capacity = self.HIGH_CARRYING_CAPACITY
        elif density_upper == "MEDIUM":
            base_capacity = self.MEDIUM_CARRYING_CAPACITY
        elif density_upper == "LOW":
            base_capacity = self.LOW_CARRYING_CAPACITY
        else:
            print(f"WARNING: Unknown density '{density}' for region {region}")
            return 0

        sd = config.SD_CARCAP * base_capacity
        random_capacity = np.random.normal(base_capacity, sd)
        
        random_capacity = max(1, round(random_capacity))
        
        return random_capacity

    def validate_hotspot_distribution(self):
        """
        Validate that hotspots are properly distributed across densities.
        Prints distribution statistics similar to NetLogo's medHighDensSpotsX.
        """
        for region_name in ["A", "B", "C", "D"]:
            high_count = 0
            medium_count = 0
            low_count = 0
            
            for pos, patch in self.patches.items():
                if patch['region'] == region_name:
                    density = patch['density']
                    if density == self.HIGH:
                        high_count += 1
                    elif density == self.MEDIUM:
                        medium_count += 1
                    elif density == self.LOW:
                        low_count += 1
            
            total = high_count + medium_count + low_count
            if total > 0:
                print(f"Region {region_name}:")
                print(f"  HIGH:   {high_count:3d} patches ({high_count/total*100:5.1f}%)")
                print(f"  MEDIUM: {medium_count:3d} patches ({medium_count/total*100:5.1f}%)")
                print(f"  LOW:    {low_count:3d} patches ({low_count/total*100:5.1f}%)")
            
    def get_initial_fish_stock(self, carrying_capacity, region):
        """NetLogo-aligned init-stock-size behavior."""
        if region in ["LAND", "NULL"]:
            return 0

        # Read from config module directly (not self.init_stock_size)
        mode = config.INIT_STOCK_SIZE

        if mode == "random":
            return self.random.randrange(carrying_capacity) if carrying_capacity > 0 else 0
        if mode == "carryingCap":
            return round(carrying_capacity)
        if mode == "halfCarryingCap":
            return round(0.5 * carrying_capacity)
        if mode == "quartCarryingCap":
            return round(0.25 * carrying_capacity)
  
        
        raise ValueError(f"Invalid initial stock size mode: {mode}")
    


    def get_region_stock(self, region_name):
        return self._region_stock_cache.get(region_name, 0)
    
    def get_total_stock(self):
        """Calculate total fish stock across all regions"""
        return self._region_stock_cache["TOTAL"]
    
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
        
        for patch in self.patches.values():
            region = patch['region']
            if patch['region'] not in ["LAND", "NULL"]:
                current_stock = patch['fish_stock']
                print(f"Patch at {patch} has current stock: {current_stock}")
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
                        new_stock = patch['fish_stock'] + patch['regen_amount']
                        self._set_patch_fish_stock(pos, new_stock)
                        patch['patch_stock_after_regrowth'] = patch['fish_stock']
            else:
                for pos, patch in self.patches.items():
                    if patch['region'] == region:
                        new_stock = patch['fish_stock'] + patch['regen_amount']
                        self._set_patch_fish_stock(pos, new_stock)
                        patch['patch_stock_after_regrowth'] = patch['fish_stock']

    def update_fish_stock_yearly(self):
        """Régénération annuelle (comme NetLogo)"""
        for pos, patch in self.patches.items():
            if patch['region'] in ["LAND", "NULL"]:
                continue
            
            current_stock = patch['fish_stock']
            carrying_capacity = patch['carrying_capacity']
            
            regen_amount = round(
                current_stock * self.GROWTH_RATE * (1 - (current_stock / carrying_capacity))
            )
            
            patch['regen_amount'] = regen_amount
            self._set_patch_fish_stock(pos, current_stock + regen_amount)
            patch['patch_stock_after_regrowth'] = patch['fish_stock']
                        
    def get_patch_info(self, x, y):
        """Get information about a specific patch"""
        return self.patches.get((x, y), None)
    
    def reduce_stock(self, x, y, catch_amount):
        "Reduce fish stock at a specific location due to fishing"
        pos = (x, y)
        if pos in self.patches:
            paatch = self.patches[pos]
            current_stock = paatch['fish_stock']
            actual_catch = min(catch_amount, current_stock)
            self._set_patch_fish_stock(pos, current_stock - actual_catch)
            return actual_catch
        return 0
    
    
    def step(self):
        """
        Advance the model by one step (one day).

        Daily execution order:
        1. Determine weather
        2. If year boundary: yearly stock update + annual reset + yearly summary
        3. Reset daily flags
        4. Agents act
        5. Refresh counters / caches / collect data
        6. Finalize day
        7. End / monthly coupling/export
        """
        # =========================
        # 1) Determine weather
        # =========================
        self.determine_weather()

        is_new_year = (self.current_step % self.YEAR == 0 and self.current_step > 0)

        yearly_summary = None
        yearly_catch = 0

        # =========================
        # 2) Yearly actions
        # =========================
        if is_new_year:
            self.update_fish_stock_yearly()

            for agent in self.agents:
                agent.reset_yearly_counters()

            if self.verbose:
                print(f"\n{'=' * 60}")
                print(f"{'=' * 60}")

                active_agents = [a for a in self.agents if not a.bankrupt]
                bankrupt_agents = [a for a in self.agents if a.bankrupt]

                print(f"\nAgents: {len(active_agents)} active, {len(bankrupt_agents)} bankrupt")

                if active_agents:
                    avg_capital = sum(a.capital for a in active_agents) / len(active_agents)
                    avg_catch = sum(a.accumulated_catch for a in active_agents) / len(active_agents)
                    print(f"Average capital: {avg_capital:.0f} SEK")
                    print(f"Average catch: {avg_catch:.0f} fish")

                    for fisher_type in ["archipelago", "coastal", "trawler"]:
                        agents_of_type = [a for a in active_agents if a.fisher_type == fisher_type]
                        if agents_of_type:
                            avg_cap = sum(a.capital for a in agents_of_type) / len(agents_of_type)
                            print(
                                f"  {fisher_type.capitalize()}: {len(agents_of_type)} agents, "
                                f"avg capital = {avg_cap:.0f} SEK"
                            )
                print(f"{'=' * 60}\n")

            yearly_summary = self.collect_yearly_data()

            current_catches = {a.unique_id: a.total_catch for a in self.agents}
            yearly_catch = sum(
                current_catches[aid] - self.last_year_catches.get(aid, 0)
                for aid in current_catches
            )
            self.last_year_catches = current_catches

        # =========================
        # 3) Reset daily flags
        # =========================
        for agent in self.agents:
            agent.reset_daily_flags()

        # =========================
        # 4) Agents act + direct counters
        # =========================
        self.num_fishing_midday = 0
        self.num_at_home_midday = 0
        self.num_fished_today = 0

        for agent in self.agents:
            agent.step()

            if agent.gone_fishing:
                self.num_fishing_midday += 1
            if agent.at_home:
                self.num_at_home_midday += 1
            if agent.fished_today:
                self.num_fished_today += 1

        # =========================
        # 5) Refresh caches and collect
        # =========================
        self._build_daily_agent_metrics_cache()
        self.datacollector.collect(self)

        # Store only today's agent rows for monthly export
        self._append_daily_agent_rows_for_monthly_export()

        # =========================
        # 6) Finalize day
        # =========================
        for agent in self.agents:
            agent.finalize_day()

        # =========================
        # 7) Yearly logs
        # =========================
        if is_new_year and yearly_summary is not None:
            if self.verbose:
                year = self.current_step // self.YEAR
                print(f"\n{'=' * 60}")
                print(f"YEAR {year} COMPLETED")
                print(f"{'=' * 60}")
                print(
                    f"Stocks: A={yearly_summary['stock_A']:,.0f} ({yearly_summary['stock_A_pct_K']:.1%}), "
                    f"B={yearly_summary['stock_B']:,.0f} ({yearly_summary['stock_B_pct_K']:.1%})"
                )
                print(f"Yearly catch: {yearly_catch:,.0f}")
                print(f"Total catch: {yearly_summary['total_catch_all']:,.0f}")
                print(
                    f"Avg capital: "
                    f"{yearly_summary['total_capital'] / max(yearly_summary['num_agents'], 1):,.2f}"
                )
                print(f"Gini capital: {yearly_summary['gini_capital']:.3f}")
                print(f"Success rate: {yearly_summary['avg_success_rate']:.1%}")
                print(f"{'=' * 60}\n")

        # =========================
        # Increment step counter
        # =========================
        self.current_step += 1

        #if self.verbose:
            #print(
            #   f"Step {self.current_step} completed. "
            #   f"Agents fishing: {self.num_fishing_midday}, "
            #   f"at home: {self.num_at_home_midday}, "
            #   f"fished today: {self.num_fished_today}"
            #)

        # =========================
        # End condition
        # =========================
        if self.current_step >= self.end_of_sim:
            self.running = False
            if self.verbose:
                self.print_final_summary()

        # =========================
        # Monthly updates
        # (same timing as your original code: AFTER increment)
        # =========================
        if self.current_step % self.MONTH == 0:
            self.HOTSPOTS_A = get_hotspots_for_step(self.current_step, "A")
            self.HOTSPOTS_B = get_hotspots_for_step(self.current_step, "B")
            self.HOTSPOTS_C = get_hotspots_for_step(self.current_step, "C")
            self.HOTSPOTS_D = get_hotspots_for_step(self.current_step, "D")

            if self.coupling:
                species_maps, current_step_val = self._wait_for_coupling_update(
                    json_path="configs/config.json",
                    poll_interval=0.5,
                )

                fish = Coupling.update_biomass(self, species_maps)
                self.update_patches(fish)

                # Stock changed => refresh cache for future reads

                self._export_monthly_agent_buffer()

                    
            
    
    def print_final_summary(self):
        """Print comprehensive summary at end of simulation."""
        print("\n" + "=" * 80)
        print("SIMULATION FINALE SUMMARY")
        print("=" * 80)

        stock_a = self._region_stock_cache["A"]
        stock_b = self._region_stock_cache["B"]
        stock_c = self._region_stock_cache["C"]
        stock_d = self._region_stock_cache["D"]
        total_stock = self._region_stock_cache["TOTAL"]

        agents_list = list(self.agents)

        print(f"\nDuration: {self.current_step} days ({self.current_step / self.YEAR:.1f} years)")
        print(f"Agents: {len(agents_list)} total")

        print(f"\n--- FISH STOCKS ---")
        print(
            f"Region A: {stock_a:>10,.0f} / {self.CARRYING_CAPACITY_A:,.0f} "
            f"({(stock_a / self.CARRYING_CAPACITY_A if self.CARRYING_CAPACITY_A > 0 else 0):.1%})"
        )
        print(
            f"Region B: {stock_b:>10,.0f} / {self.CARRYING_CAPACITY_B:,.0f} "
            f"({(stock_b / self.CARRYING_CAPACITY_B if self.CARRYING_CAPACITY_B > 0 else 0):.1%})"
        )
        print(
            f"Region C: {stock_c:>10,.0f} / {self.CARRYING_CAPACITY_C:,.0f} "
            f"({(stock_c / self.CARRYING_CAPACITY_C if self.CARRYING_CAPACITY_C > 0 else 0):.1%})"
        )
        print(
            f"Region D: {stock_d:>10,.0f} / {self.CARRYING_CAPACITY_D:,.0f} "
            f"({(stock_d / self.CARRYING_CAPACITY_D if self.CARRYING_CAPACITY_D > 0 else 0):.1%})"
        )
        print(f"TOTAL:    {total_stock:>10,.0f}")

        print(f"\n--- ECONOMICS ---")
        total_catch = sum(a.total_catch for a in agents_list)
        total_capital = sum(a.capital for a in agents_list)
        total_profit = sum(a.total_profit for a in agents_list)

        print(f"Total catch:   {total_catch:>12,.0f}")
        print(f"Total capital: {total_capital:>12,.2f}")
        print(f"Total profit:  {total_profit:>12,.2f}")
        print(f"Avg capital:   {(total_capital / len(agents_list)) if agents_list else 0:>12,.2f}")

        print(f"\n--- INEQUALITY ---")
        print(f"Gini capital: {self.calculate_gini([a.capital for a in agents_list]) if agents_list else 0:.3f}")
        print(f"Gini wealth:  {self.calculate_gini([a.wealth for a in agents_list]) if agents_list else 0:.3f}")
        print(f"Gini catch:   {self.calculate_gini([a.total_catch for a in agents_list]) if agents_list else 0:.3f}")

        print(f"\n--- BY FISHER TYPE ---")
        by_type = {
            "archipelago": [],
            "coastal": [],
            "trawler": [],
        }

        for a in agents_list:
            if a.fisher_type in by_type:
                by_type[a.fisher_type].append(a)

        for ftype in ["archipelago", "coastal", "trawler"]:
            type_agents = by_type[ftype]
            if type_agents:
                avg_catch = sum(a.total_catch for a in type_agents) / len(type_agents)
                avg_capital = sum(a.capital for a in type_agents) / len(type_agents)
                bankrupt = sum(1 for a in type_agents if a.bankrupt)
                print(
                    f"{ftype:>12}: {len(type_agents):>3} agents, "
                    f"avg catch={avg_catch:>8,.0f}, "
                    f"avg capital={avg_capital:>8,.2f}, "
                    f"bankrupt={bankrupt}"
                )

        print("=" * 80 + "\n")

        
        
    def export_data(self, filename_prefix="fibe_output", directory="./results/"):
        """
        Export collected data to CSV files.

        Args:
            filename_prefix: Prefix for output files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = os.path.join(directory, timestamp)
        os.makedirs(export_dir, exist_ok=True)

        # =========================
        # Export daily model data
        # =========================
        model_df = self.datacollector.get_model_vars_dataframe()
        model_path = os.path.join(export_dir, f"{filename_prefix}_model_{timestamp}.csv")
        model_df.to_csv(model_path, index=False)

        if self.verbose:
            print(f"Exported: {os.path.basename(model_path)} ({len(model_df)} rows)")

        # =========================
        # Export daily agent data
        # =========================
        agent_df = self.datacollector.get_agent_vars_dataframe()
        agent_path = os.path.join(export_dir, f"{filename_prefix}_agent_{timestamp}.csv")
        agent_df.to_csv(agent_path, index=False)

        if self.verbose:
            print(f"Exported: {os.path.basename(agent_path)} ({len(agent_df)} rows)")

        # =========================
        # Export yearly data
        # =========================
        if self.yearly_data:
            yearly_df = pd.DataFrame(self.yearly_data)
            yearly_path = os.path.join(export_dir, f"{filename_prefix}_yearly_{timestamp}.csv")
            yearly_df.to_csv(yearly_path, index=False)

            self.save_output_map(export_dir, f"{filename_prefix}_stock_{timestamp}.csv")

            if self.verbose:
                print(f"Exported: {os.path.basename(yearly_path)} ({len(yearly_df)} rows)")

        if self.verbose:
            print(f"\nAll data exported with timestamp: {timestamp}")

        
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
                    total_capacity += patch['fish_stock']
            
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
            'num_fishing': self.num_fishing_midday,
            'num_at_home': self.num_at_home_midday,
            'num_fished_today': self.num_fished_today,
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

        stock_a = self._region_stock_cache["A"]
        stock_b = self._region_stock_cache["B"]
        stock_c = self._region_stock_cache["C"]
        stock_d = self._region_stock_cache["D"]
        total_stock = self._region_stock_cache["TOTAL"]

        by_type_count = {
            "archipelago": 0,
            "coastal": 0,
            "trawler": 0,
        }

        by_type_total_catch = {
            "archipelago": 0,
            "coastal": 0,
            "trawler": 0,
        }

        by_type_capitals = {
            "archipelago": [],
            "coastal": [],
            "trawler": [],
        }

        capitals = []
        wealths = []
        catches = []
        days_at_sea = []

        total_capital = 0
        total_profit = 0
        total_revenue = 0
        total_costs = 0

        total_trips = 0
        total_profitable_trips = 0
        total_unprofitable_trips = 0

        success_rate_sum = 0.0
        success_rate_count = 0

        num_bankrupt = 0
        num_agents = 0

        for a in self.agents:
            num_agents += 1
            ftype = a.fisher_type

            if ftype in by_type_count:
                by_type_count[ftype] += 1
                by_type_total_catch[ftype] += a.total_catch
                by_type_capitals[ftype].append(a.capital)

            capitals.append(a.capital)
            wealths.append(a.wealth)
            catches.append(a.total_catch)
            days_at_sea.append(a.days_at_sea)

            total_capital += a.capital
            total_profit += a.total_profit
            total_revenue += a.total_revenue
            total_costs += a.total_cost

            total_profitable_trips += a.profitable_trip
            total_unprofitable_trips += a.unprofitable_trip

            trips = a.profitable_trip + a.unprofitable_trip
            total_trips += trips
            if trips > 0:
                success_rate_sum += a.profitable_trip / trips
                success_rate_count += 1

            if a.bankrupt:
                num_bankrupt += 1

        yearly_summary = {
            # =========================
            # General
            # =========================
            "year": year,
            "step": self.current_step,

            # =========================
            # Stocks
            # =========================
            "stock_A": stock_a,
            "stock_B": stock_b,
            "stock_C": stock_c,
            "stock_D": stock_d,
            "total_stock": total_stock,
            "stock_A_pct_K": stock_a / self.CARRYING_CAPACITY_A if self.CARRYING_CAPACITY_A > 0 else 0,
            "stock_B_pct_K": stock_b / self.CARRYING_CAPACITY_B if self.CARRYING_CAPACITY_B > 0 else 0,
            "stock_C_pct_K": stock_c / self.CARRYING_CAPACITY_C if self.CARRYING_CAPACITY_C > 0 else 0,
            "stock_D_pct_K": stock_d / self.CARRYING_CAPACITY_D if self.CARRYING_CAPACITY_D > 0 else 0,

            # =========================
            # Agents
            # =========================
            "num_agents": num_agents,
            "num_archipelago": by_type_count["archipelago"],
            "num_coastal": by_type_count["coastal"],
            "num_trawler": by_type_count["trawler"],
            "num_bankrupt": num_bankrupt,

            # =========================
            # Catches
            # =========================
            "total_catch_archipelago": by_type_total_catch["archipelago"],
            "total_catch_coastal": by_type_total_catch["coastal"],
            "total_catch_trawler": by_type_total_catch["trawler"],
            "total_catch_all": sum(catches),
            "avg_catch_archipelago": (
                by_type_total_catch["archipelago"] / by_type_count["archipelago"]
                if by_type_count["archipelago"] else 0
            ),
            "avg_catch_coastal": (
                by_type_total_catch["coastal"] / by_type_count["coastal"]
                if by_type_count["coastal"] else 0
            ),
            "avg_catch_trawler": (
                by_type_total_catch["trawler"] / by_type_count["trawler"]
                if by_type_count["trawler"] else 0
            ),

            # =========================
            # Economics
            # =========================
            "avg_capital_archipelago": self._safe_mean(by_type_capitals["archipelago"]),
            "avg_capital_coastal": self._safe_mean(by_type_capitals["coastal"]),
            "avg_capital_trawler": self._safe_mean(by_type_capitals["trawler"]),
            "total_capital": total_capital,
            "total_profit": total_profit,
            "total_revenue": total_revenue,
            "total_costs": total_costs,

            # =========================
            # Inequality
            # =========================
            "gini_capital": self.calculate_gini(capitals) if capitals else 0,
            "gini_wealth": self.calculate_gini(wealths) if wealths else 0,
            "gini_catch": self.calculate_gini(catches) if catches else 0,

            # =========================
            # Activity
            # =========================
            "total_trips": total_trips,
            "total_profitable_trips": total_profitable_trips,
            "total_unprofitable_trips": total_unprofitable_trips,
            "avg_success_rate": success_rate_sum / success_rate_count if success_rate_count else 0,
            "avg_days_at_sea": self._safe_mean(days_at_sea),
        }

        self.yearly_data.append(yearly_summary)
        return yearly_summary

    
    
    def get_total_catch_all_agents(self):
        """Somme des captures de tous les agents depuis le dernier snapshot annuel."""
        if not hasattr(self, "last_year_catches") or not self.last_year_catches:
            return sum(a.total_catch for a in self.agents)

        current_catches = {a.unique_id: a.total_catch for a in self.agents}
        yearly_catch = sum(
            current_catches[aid] - self.last_year_catches.get(aid, 0)
            for aid in current_catches
        )
        return yearly_catch

    
    def get_output_map(self):
        """Get a map of current fish stocks for visualization"""
        stock_map = np.zeros((self.grid.height, self.grid.width), dtype=int)
        for (x, y), patch in self.patches.items():
            stock_map[x, y] = int(patch['fish_stock'])
        return stock_map
    
    def save_output_map(self, directory, filename):
        """Save current stock map as an csv"""
        stock_map = self.get_output_map()
        if os.path.exists(directory):
            np.savetxt(f"{directory}/{filename}", stock_map, fmt='%d', delimiter=",")
        else:
            os.makedirs(directory)
            np.savetxt(f"{directory}/{filename}", stock_map, fmt='%d', delimiter=",")

    def update_patches(self, new_fish_stocks):
        """Update patch fish stocks with a provided map (for coupling)"""
        for (x, y), stock in new_fish_stocks.items():
            pos = (x, y)
            if pos in self.patches:
                self._set_patch_fish_stock(pos, stock)

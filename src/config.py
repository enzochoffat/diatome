"""
Configuration constants for the FIBE fishery model.

This module centralizes all model parameters, making them easy to modify
for experiments and sensitivity analysis.
"""

import sys 
from pathlib import Path
import numpy as np 

# Add the project root to Python path so we can import from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ecospace_outputs import masks
from src.ecospace_outputs import get_ecospace_data
from src import ecospace_outputs

# =============================================================================
# TIME CONSTANTS
# =============================================================================

WEEK = 7
MONTH = 28
SEASON = 84
HALFYEAR = 168
YEAR = 365

# =============================================================================
# SPATIAL DEFINITIONS
# =============================================================================

# Grid dimensions
GRID_WIDTH = 101
GRID_HEIGHT = 70
TOPOLOGY = masks(topology=True, windfarm=False)['masks'][0]
# Regional boundaries [x_range, y_range]
LAND = [row for row in [[val for val in row if val < 1e-29] for row in TOPOLOGY] if row]

def add_windfarm_to_topology():
    """
    Load Wind Farm topology and merge it with existing TOPOLOGY.
    Updates LAND zones to include Wind Farm areas.
    Also recalculates REGION_A/B/C/D with new topology.
    """
    global TOPOLOGY, LAND, WATER, y_min_water, REGION_A, REGION_B, REGION_C, REGION_D
    try:
        # Load Wind Farm topology
        windfarm_data = masks(topology=False, windfarm=True)
        windfarm_topology = windfarm_data['masks'][0]
        
        # Merge: if either TOPOLOGY or WINDFARM is LAND (value < 1e-29), result is LAND
        merged_topology = []
        for y in range(len(TOPOLOGY)):
            row = []
            for x in range(len(TOPOLOGY[y])):
                topo_val = TOPOLOGY[y][x]
                wind_val = windfarm_topology[y][x] if y < len(windfarm_topology) and x < len(windfarm_topology[y]) else topo_val
                
                # If either is LAND, result is LAND
                if topo_val < 1e-29 or wind_val == 1:
                    row.append(1e-30)  # LAND (small value < 1e-29)
                else:
                    row.append(topo_val)  # Water
            merged_topology.append(row)
        
        # Update global TOPOLOGY
        TOPOLOGY = merged_topology
        LAND = [row for row in [[val for val in row if val < 1e-29] for row in TOPOLOGY] if row]
        
        # Recalculate WATER and y_min_water
        WATER = [row for row in [[val for val in row if val >= 1e-29] for row in TOPOLOGY] if row]
        y_min_water = int(min(WATER[-1])) if WATER else 0
        
        # Recalculate regions with new topology
        REGION_A = define_region('A')
        REGION_B = define_region('B')
        REGION_C = define_region('C')
        REGION_D = define_region('D')
        
        return merged_topology
    
    except Exception as e:
        print(f"Error loading Wind Farm topology: {e}")
        return TOPOLOGY



WATER = [row for row in [[val for val in row if val >= 1e-29] for row in TOPOLOGY] if row]
single_slice = GRID_HEIGHT//4
y_min_water = int(min(WATER[-1]))

def define_region(REGION_NAME) :
    REGION = []
    if REGION_NAME == 'A' : 
        max_slice = single_slice
    elif REGION_NAME == 'B' : 
        max_slice = 2*single_slice
    elif REGION_NAME == 'C' : 
        max_slice = 3*single_slice
    elif REGION_NAME == 'D' : 
        max_slice = 4*single_slice
    for y in range(y_min_water, max_slice):
        for x in range(GRID_WIDTH):
            if y < len(TOPOLOGY) and x < len(TOPOLOGY[y]) and TOPOLOGY[y][x] > 0:
                REGION.append([x, y])
    return REGION

REGION_A = define_region('A')    #Archipelagos 
REGION_B = define_region('B')    # Coastal zone 1
REGION_C = define_region('C')    # Coastal zone 2
REGION_D = define_region('D')   # Open sea



# =============================================================================
# HOTSPOT LOCATIONS
# =============================================================================

# High-density fishing spots (coordinates [x, y])

def get_hotspots_for_step(step, region_name):
    """
    Retourne les 2 hotspots avec la plus haute concentration pour une région à un step donné.
    Chaque date Ecospace = 30 steps du modèle.
    La première date Ecospace correspond à step 0.
    Utilise les hotspots par défaut si les données Ecospace n'ont pas été chargées.
    """
    # Hotspots par défaut si Ecospace n'est pas disponible
    default_hotspots = {
        'A': [[7, 3], [16, 3]],
        'B': [[3, 19], [8, 11]],
        'C': [[4, 51], [21, 51]],
        'D': [[30, 51], [47, 51]]
    }
    
    # Si ecospace_data n'a jamais été chargé (cache is None), utiliser les defaults
    if ecospace_outputs._ecospace_data_cache is None:
        return default_hotspots.get(region_name, [])
    
    try:
        ecospace_data = ecospace_outputs._ecospace_data_cache
        if ecospace_data is None or 'maps' not in ecospace_data:
            return default_hotspots.get(region_name, [])
        
        date_index = step // 30
        
        # Gestion des limites
        if date_index >= len(ecospace_data['maps']['map']):
            date_index = len(ecospace_data['maps']['map']) - 1
        
        fish_map = np.array(ecospace_data['maps']['map'][date_index][0])
        
        # Sélectionner la région
        region_map = {
            'A': REGION_A,
            'B': REGION_B,
            'C': REGION_C,
            'D': REGION_D
        }
        region = region_map.get(region_name, [])
        
        # Trouver les 3 plus hautes concentrations
        if region:
            top_coords = sorted(region, key=lambda xy: fish_map[xy[1]][xy[0]], reverse=True)[:3]
            return top_coords
    except Exception as e:
        pass
    
    return default_hotspots.get(region_name, [])


# =============================================================================
# DENSITY LEVELS
# =============================================================================

LOW = "low"
MEDIUM = "medium"
HIGH = "high"
MEDIUM_HIGH = "medium_high"
LOW_MEDIUM = "low_medium"

# =============================================================================
# FISH STOCK PARAMETERS
# =============================================================================

# Growth rate (annual logistic growth)
GROWTH_RATE = 1.0  # 10% per year

# Carrying capacities by density level (fish per patch)
LOW_CARRYING_CAPACITY = 4           # Poor patch
MEDIUM_CARRYING_CAPACITY = 3276     # Medium patch
HIGH_CARRYING_CAPACITY = 8736     # Rich patch (hotspot)

# Regional carrying capacities (total fish)
# NOTE: These are recalculated at model init based on actual patch distribution
CARRYING_CAPACITY_A_INITIAL = 219000    # Archipelago
CARRYING_CAPACITY_B_INITIAL = 438000    # Coastal 1
CARRYING_CAPACITY_C_INITIAL = 876000    # Coastal 2
CARRYING_CAPACITY_D_INITIAL = 876000    # Open sea

INIT_STOCK_SIZE = "halfCarryingCap"

# =============================================================================
# ECONOMIC PARAMETERS
# =============================================================================

# Fish market price (SEK per fish)
FISH_PRICE = 1.0

# Initial capital for all fisher types (SEK)
INITIAL_CAPITAL = 1000

# Age range for fishers
MIN_AGE = 18
MAX_AGE = 65

# Bankruptcy parameters
BANKRUPTCY_THRESHOLD_YEARS = 1          # Years of existence costs before bankruptcy
BANKRUPTCY_LAYLOW_DAYS = 30             # Days to lay low after bankruptcy
NEGATIVE_CAPITAL_LAYLOW_PROBABILITY = 0.3  # Probability to lay low when capital < 0
NEGATIVE_CAPITAL_LAYLOW_DAYS = 7        # Days to lay low when capital < 0

# Financial safety buffer
SAFETY_BUFFER_DAYS = 7                  # Days of existence costs to keep as buffer

# =============================================================================
# FISHER TYPE: ARCHIPELAGO
# =============================================================================

ARCHIPELAGO_COST_EXISTENCE = 0.5      # Daily existence cost (SEK)
ARCHIPELAGO_COST_ACTIVITY = 0.5       # Fishing activity cost (SEK)
ARCHIPELAGO_CATCHABILITY = 5          # Fish caught per day
ARCHIPELAGO_ACCESSIBLE_REGIONS = ["A"]
ARCHIPELAGO_MAX_GOOD_SPOTS = 5        # Memory capacity for good spots

# =============================================================================
# FISHER TYPE: COASTAL
# =============================================================================

COASTAL_COST_EXISTENCE = 1.0          # Daily existence cost (SEK)
COASTAL_COST_ACTIVITY = 1.0           # Fishing activity cost (SEK)
COASTAL_CATCHABILITY = 10             # Fish caught per day
COASTAL_ACCESSIBLE_REGIONS = ["A", "B"]
COASTAL_MAX_GOOD_SPOTS = 3            # Memory capacity for good spots

# =============================================================================
# FISHER TYPE: TRAWLER
# =============================================================================

TRAWLER_COST_EXISTENCE = 5.0          # Daily existence cost (SEK)
TRAWLER_COST_ACTIVITY = 5.0           # Fishing activity cost (SEK)
TRAWLER_CATCHABILITY = 50             # Fish caught per day
TRAWLER_ACCESSIBLE_REGIONS = ["B", "C", "D"]
TRAWLER_MAX_GOOD_SPOTS = 2            # Memory capacity for good spots
TRAWLER_STORAGE_CAPACITY = 50       # Fish storage capacity

# =============================================================================
# TRAVEL COSTS
# =============================================================================

LOW_COST_TRAVEL = 2.5                 # Travel to Region A (SEK)
MEDIUM_COST_TRAVEL = 5.0              # Travel to Region B (SEK)
MEDIUM_COST_TRAVEL_BIGVESSEL = 8.0    # Travel to Region B (trawler) (SEK)
HIGH_COST_TRAVEL = 15.0               # Travel to Region C or D (SEK)

# Inter-region travel cost multiplier
INTER_REGION_TRAVEL_MULTIPLIER = 0.5  # Cheaper to switch between regions

# Travel cost per unit distance (for calculate_travel_cost)
TRAVEL_COST_PER_UNIT = 1.0

# =============================================================================
# DECISION-MAKING PARAMETERS
# =============================================================================

# Memory settings
DEFAULT_MEMORY_SIZE = 365              # Remember last N fishing trips
SPATIAL_MEMORY_MAX_AGE = 365 * 1      # Forget spots after 1 years

# Decision thresholds (coastal)
SATISFACTION_HOME_THRESHOLD = 0.5
SATISFACTION_GROWTH_THRESHOLD = 0.5
SCARCE_PERCEPTION_THRESHOLD = -0.05

# Good spot criteria
GOOD_SPOT_EFFICIENCY_THRESHOLD = 0.7  # Catch must be 70% of expected

# Simple decision probability (for testing)
SIMPLE_FISHING_PROBABILITY = 0.5    # Probability to fish in simple mode

# Memory windows for perception
MEMORY_RECENT_WINDOW = 5              # Last N trips for recent catches
MEMORY_OLDER_WINDOW = 10              # N trips before recent for comparison
MEMORY_WEEKLY_WINDOW = 7              # Last week for revenue calculation
MEMORY_BIWEEKLY_WINDOW = 14           # Two weeks for satisfaction calculation
MEMORY_MONTHLY_WINDOW = 30            # One month for regional estimates

# Scarcity perception
SCARCITY_CATCH_RATIO_THRESHOLD = 0.5  # Catch below 50% of expected = scarcity
SCARCITY_MIN_MEMORY = 10              # Minimum trips needed to perceive scarcity

# Exploration phase
EXPLORATION_PHASE_TRIPS = 5           # Number of trips before normal decision-making


TRAWLER_PROFIT_THRESHOLD_DAYS = 1
# =============================================================================
# WEATHER PARAMETERS
# =============================================================================

BAD_WEATHER_PROBABILITY = 0.1         # 10% chance of bad weather per day

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Social attributes
PARTNER_PROBABILITY = 0.5 

SD_CARCAP = 0.1
HOTSPOT_HIGH_RADIUS = 1.5
HOTSPOT_MEDIUM_RADIUS = 3.0



def get_region_initial_capacity(region_name):
    """
    Get initial carrying capacity for a region.
    
    Args:
        region_name (str): Region identifier (A, B, C, D)
        
    Returns:
        int: Initial carrying capacity
    """
    capacities = {
        "A": CARRYING_CAPACITY_A_INITIAL,
        "B": CARRYING_CAPACITY_B_INITIAL,
        "C": CARRYING_CAPACITY_C_INITIAL,
        "D": CARRYING_CAPACITY_D_INITIAL,
        "LAND": 0,
        "NULL": 0
    }
    return capacities.get(region_name, 0)


def get_msy_stock(carrying_capacity):
    """
    Calculate Maximum Sustainable Yield stock level.
    MSY occurs at 50% of carrying capacity (K/2).
    
    Args:
        carrying_capacity (int): Total carrying capacity
        
    Returns:
        int: MSY stock level
    """
    return round(carrying_capacity / 2)


def get_fisher_config(fisher_type):
    """
    Get all configuration parameters for a fisher type.
    
    Args:
        fisher_type (str): "archipelago", "coastal", or "trawler"
        
    Returns:
        dict: Configuration dictionary
    """
    configs = {
        "archipelago": {
            "cost_existence": ARCHIPELAGO_COST_EXISTENCE,
            "cost_activity": ARCHIPELAGO_COST_ACTIVITY,
            "catchability": ARCHIPELAGO_CATCHABILITY,
            "accessible_regions": ARCHIPELAGO_ACCESSIBLE_REGIONS,
            "max_good_spots": ARCHIPELAGO_MAX_GOOD_SPOTS,
            "storage_capacity": 0,
        },
        "coastal": {
            "cost_existence": COASTAL_COST_EXISTENCE,
            "cost_activity": COASTAL_COST_ACTIVITY,
            "catchability": COASTAL_CATCHABILITY,
            "accessible_regions": COASTAL_ACCESSIBLE_REGIONS,
            "max_good_spots": COASTAL_MAX_GOOD_SPOTS,
            "storage_capacity": 0,
        },
        "trawler": {
            "cost_existence": TRAWLER_COST_EXISTENCE,
            "cost_activity": TRAWLER_COST_ACTIVITY,
            "catchability": TRAWLER_CATCHABILITY,
            "accessible_regions": TRAWLER_ACCESSIBLE_REGIONS,
            "max_good_spots": TRAWLER_MAX_GOOD_SPOTS,
            "storage_capacity": TRAWLER_STORAGE_CAPACITY,
        }
    }
    return configs.get(fisher_type, {})


def get_travel_cost(region, fisher_type="coastal"):
    """
    Calculate travel cost to a region.
    
    Args:
        region (str): Target region (A, B, C, D)
        fisher_type (str): Fisher type (affects cost for region B)
        
    Returns:
        float: Travel cost in SEK
    """
    if region == "A":
        return LOW_COST_TRAVEL
    elif region == "B":
        if fisher_type == "trawler":
            return MEDIUM_COST_TRAVEL_BIGVESSEL
        else:
            return MEDIUM_COST_TRAVEL
    elif region in ["C", "D"]:
        return HIGH_COST_TRAVEL
    else:
        return 0

def get_bankruptcy_threshold(cost_existence):
    """
    Calculate bankruptcy threshold for a fisher.
    
    Args:
        cost_existence (float): Daily existence cost
        
    Returns:
        float: Negative capital threshold for bankruptcy
    """
    return -(cost_existence * YEAR * BANKRUPTCY_THRESHOLD_YEARS)

def get_safety_buffer(cost_existence):
    """
    Calculate safety buffer for trip affordability.
    
    Args:
        cost_existence (float): Daily existence cost
        
    Returns:
        float: Safety buffer amount
    """
    return cost_existence * SAFETY_BUFFER_DAYS

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================

def validate_config():
    """
    Validate configuration parameters for consistency.
    
    Raises:
        ValueError: If configuration is invalid
    """
    # Check positive values
    assert GROWTH_RATE > 0, "Growth rate must be positive"
    assert FISH_PRICE > 0, "Fish price must be positive"
    assert INITIAL_CAPITAL > 0, "Initial capital must be positive"
    
    # Check age range
    assert MIN_AGE < MAX_AGE, "MIN_AGE must be less than MAX_AGE"
    assert MIN_AGE >= 0, "MIN_AGE must be non-negative"
    
    # Check costs
    assert ARCHIPELAGO_COST_EXISTENCE > 0, "Existence costs must be positive"
    assert COASTAL_COST_EXISTENCE > 0, "Existence costs must be positive"
    assert TRAWLER_COST_EXISTENCE > 0, "Existence costs must be positive"
    
    # Check catchabilities
    assert ARCHIPELAGO_CATCHABILITY > 0, "Catchability must be positive"
    assert COASTAL_CATCHABILITY > 0, "Catchability must be positive"
    assert TRAWLER_CATCHABILITY > 0, "Catchability must be positive"
    
    # Check grid dimensions
    assert GRID_WIDTH > 0 and GRID_HEIGHT > 0, "Grid dimensions must be positive"
    
    # Check thresholds
    assert 0 <= GOOD_SPOT_EFFICIENCY_THRESHOLD <= 1, "Efficiency threshold must be in [0,1]"
    assert 0 <= SATISFACTION_HOME_THRESHOLD <= 1, "Satisfaction thresholds must be in [0,1]"
    assert 0 <= SATISFACTION_GROWTH_THRESHOLD <= 1, "Satisfaction thresholds must be in [0,1]"
    
    # Check probabilities
    assert 0 <= BAD_WEATHER_PROBABILITY <= 1, "Weather probability must be in [0,1]"
    assert 0 <= SIMPLE_FISHING_PROBABILITY <= 1, "Fishing probability must be in [0,1]"
    assert 0 <= NEGATIVE_CAPITAL_LAYLOW_PROBABILITY <= 1, "Laylow probability must be in [0,1]"
    
    assert INIT_STOCK_SIZE in {"random", "halfCarryingCap", "carryingCap", "quartCarryingCap"}, "Invalid initial stock size option"
    print("Configuration validated successfully")


if __name__ == "__main__":
    # Run validation when module is executed directly
    validate_config()
    
    # Print summary
    print("\n" + "="*60)
    print("FIBE MODEL CONFIGURATION SUMMARY")
    print("="*60)
    print(f"\nGrid: {GRID_WIDTH} × {GRID_HEIGHT}")
    print(f"Growth rate: {GROWTH_RATE*100}% per year")
    print(f"Fish price: {FISH_PRICE} SEK")
    print(f"Initial capital: {INITIAL_CAPITAL} SEK")
    
    print("\nFisher types:")
    for ftype in ["archipelago", "coastal", "trawler"]:
        cfg = get_fisher_config(ftype)
        print(f"  {ftype.capitalize():12} - Catchability: {cfg['catchability']:3}, "
              f"Existence: {cfg['cost_existence']:.1f} SEK, "
              f"Regions: {', '.join(cfg['accessible_regions'])}")
    
    print("\nRegional capacities (initial):")
    for region in ["A", "B", "C", "D"]:
        cap = get_region_initial_capacity(region)
        msy = get_msy_stock(cap)
        print(f"  Region {region}: {cap:>9,} fish (MSY: {msy:>9,})")
    
    print("\nDecision-making parameters:")
    print(f"  Memory size: {DEFAULT_MEMORY_SIZE} trips")
    print(f"  Satisfaction thresholds: home={SATISFACTION_HOME_THRESHOLD}, growth={SATISFACTION_GROWTH_THRESHOLD}")
    print(f"  Good spot efficiency: {GOOD_SPOT_EFFICIENCY_THRESHOLD:.0%}")
    print(f"  Scarcity threshold: {SCARCE_PERCEPTION_THRESHOLD}")
    
    print("="*60)
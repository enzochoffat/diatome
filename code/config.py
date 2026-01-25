"""
Configuration constants for the FIBE fishery model.

This module centralizes all model parameters, making them easy to modify
for experiments and sensitivity analysis.
"""

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

# Regional boundaries [x_range, y_range]
REGION_A = [[0, 25], [0, 8]]      # Archipelago zone
REGION_B = [[0, 25], [8, 24]]     # Coastal zone 1
REGION_C = [[0, 25], [24, 56]]    # Coastal zone 2
REGION_D = [[25, 50], [24, 56]]   # Open sea
LAND = [[25, 50], [0, 24]]        # Non-fishing area

# Grid dimensions
GRID_WIDTH = 50
GRID_HEIGHT = 56

# =============================================================================
# HOTSPOT LOCATIONS
# =============================================================================

# High-density fishing spots (coordinates [x, y])
HOTSPOTS_A = [[7, 3], [16, 3], [3, 3], [10, 7]]
HOTSPOTS_B = [[3, 19], [8, 11], [19, 11], [15, 19]]
HOTSPOTS_C = [
    [4, 51], [21, 51], [13, 45], [3, 39], 
    [12, 36], [22, 40], [7, 27], [19, 27]
]
HOTSPOTS_D = [
    [30, 51], [47, 51], [37, 45], [29, 39], 
    [46, 39], [37, 33], [31, 27], [44, 27]
]

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
GROWTH_RATE = 0.1  # 10% per year

# Carrying capacities by density level (fish per patch)
LOW_CARRYING_CAPACITY = 4           # Poor patch
MEDIUM_CARRYING_CAPACITY = 3276     # Medium patch
HIGH_CARRYING_CAPACITY = 873600     # Rich patch (hotspot)

# Regional carrying capacities (total fish)
# NOTE: These are recalculated at model init based on actual patch distribution
CARRYING_CAPACITY_A_INITIAL = 219000    # Archipelago
CARRYING_CAPACITY_B_INITIAL = 438000    # Coastal 1
CARRYING_CAPACITY_C_INITIAL = 876000    # Coastal 2
CARRYING_CAPACITY_D_INITIAL = 876000    # Open sea

# =============================================================================
# ECONOMIC PARAMETERS
# =============================================================================

# Fish market price (SEK per fish)
FISH_PRICE = 10.0

# Initial capital for all fisher types (SEK)
INITIAL_CAPITAL = 1000.0

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
TRAWLER_ACCESSIBLE_REGIONS = ["A", "B", "C", "D"]
TRAWLER_MAX_GOOD_SPOTS = 2            # Memory capacity for good spots
TRAWLER_STORAGE_CAPACITY = 5000       # Fish storage capacity

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
DEFAULT_MEMORY_SIZE = 10              # Remember last N fishing trips
SPATIAL_MEMORY_MAX_AGE = 365 * 2      # Forget spots after 2 years

# Decision thresholds (archipelago)
SATISFACTION_HOME_THRESHOLD = 0.5
SATISFACTION_GROWTH_THRESHOLD = 0.6
SCARCE_PERCEPTION_THRESHOLD = -0.05

# Good spot criteria
GOOD_SPOT_EFFICIENCY_THRESHOLD = 0.7  # Catch must be 70% of expected

# Simple decision probability (for testing)
SIMPLE_FISHING_PROBABILITY = 0.7      # Probability to fish in simple mode

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


TRAWLER_PROFIT_THRESHOLD_DAYS = 3
# =============================================================================
# WEATHER PARAMETERS
# =============================================================================

BAD_WEATHER_PROBABILITY = 0.1         # 10% chance of bad weather per day

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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
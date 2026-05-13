"""
Configuration constants for the FIBE fishery model.

This module centralizes all model parameters, making them easy to modify
for experiments and sensitivity analysis.
"""

import sys 
from pathlib import Path
import numpy as np 
import math

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

def compute_land_coordinates(topo_matrix):
    """Compute list of [x, y] coordinates for all LAND cells"""
    land_coords = []
    for y in range(len(topo_matrix)):
        for x in range(len(topo_matrix[y])):
            if topo_matrix[y][x] == 0 or topo_matrix[y][x] < 1e-29:
                land_coords.append([x, y])
    return land_coords

TOPOLOGY = []
ORIGINAL_TOPOLOGY = []
LAND = []
WATER = []
GRID_HEIGHT = 0
GRID_WIDTH = 0
single_slice = 0
y_min_water = 0
all_water_depths = []
max_depth = 0
min_depth = 0
percentile_90_depth = 0
REGION_A = []
REGION_B = []
REGION_C = []
REGION_D = []

def add_windfarm_to_topology():
    """
    Load Wind Farm topology and merge it with existing TOPOLOGY.
    Updates LAND zones to include Wind Farm areas.
    Also recalculates REGION_A/B/C/D with new topology.
    """
    try:
        reload_spatial_configuration(apply_windfarm=True)
        return TOPOLOGY
    
    except Exception as e:
        print(f"Error loading Wind Farm topology: {e}")
print(f"  Total water cells: {len(all_water_depths)}")


import numpy as np

def get_neighbors_by_euclidean_distance(matrix, center_value, radius=7):
    """
    Récupère les valeurs et coordonnées des cellules situées à une distance 
    euclidienne <= radius de n'importe quelle occurrence de center_value.
    
    Paramètres :
    - matrix : Liste de listes (matrice)
    - center_value : La valeur numérique à rechercher
    - radius : Rayon du cercle (ex: 7)
    
    Retourne :
    - indices : Liste de tuples (ligne, colonne)
    - values : Liste des valeurs correspondantes
    """
    
    # 1. Trouver toutes les coordonnées (l, c) où la valeur est égale à center_value
    centers = []
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            if val == center_value:
                centers.append((i, j))
    
    print(f"    [get_neighbors] Looking for center_value={center_value}, found {len(centers)} centers")
    
    if not centers:
        print(f"    [get_neighbors] WARNING: No centers found! Unique values in TOPOLOGY: {sorted(set([v for row in matrix for v in row if v > 0]))[:10]}...")
        return [], []

    # 2. Initialiser un tableau de distances infinies pour chaque cellule
    # On stocke la distance minimale trouvée pour chaque cellule
    rows_count = len(matrix)
    cols_count = len(matrix[0]) if rows_count > 0 else 0
    
    # On crée une structure pour stocker la distance minimale actuelle pour chaque (i, j)
    # Initialisée à l'infini
    min_distances = [[float('inf') for _ in range(cols_count)] for _ in range(rows_count)]
    
    # 3. Pour chaque cellule de la matrice, calculer la distance vers LE PLUS PROCHE centre
    # Optimisation : on parcourt chaque cellule et on calcule la distance vers chaque centre
    # (Pour une matrice très grande et des milliers de centers, une approche vectorielle ou k-d tree serait préférable,
    # mais pour des tailles courantes, cette boucle imbriquée est claire et fonctionnelle).
    
    for r in range(rows_count):
        for c in range(cols_count):
            # On cherche la distance minimale vers n'importe quel centre
            current_min_dist = float('inf')
            
            for cr, cc in centers:
                # Distance euclidienne : sqrt((r - cr)^2 + (c - cc)^2)
                dist = math.sqrt((r - cr)**2 + (c - cc)**2)
                if dist < current_min_dist:
                    current_min_dist = dist
            
            min_distances[r][c] = current_min_dist

    # 4. Filtrer : distance <= radius ET la valeur n'est PAS center_value
    result_indices = []
    result_values = []
    
    for r in range(rows_count):
        for c in range(cols_count):
            # On vérifie la condition de distance et on exclut la valeur 'center' elle-même
            if min_distances[r][c] <= radius and matrix[r][c] != center_value:
                if matrix[r][c] > 0 : #water zone
                            result_indices.append([r, c])
                            result_values.append(matrix[r][c])
    
    return result_indices, result_values


def get_neighbors_by_euclidean_distance_as_xy(matrix, center_value, radius=7):
    """
    Wrapper that returns coordinates in (x, y) format instead of (row, col) format.
    x = column, y = row
    """
    indices, values = get_neighbors_by_euclidean_distance(matrix, center_value, radius)
    # Convert from [row, col] to [x, y] which is [col, row]
    indices_xy = [[col, row] for row, col in indices]
    return indices_xy, values


def reload_spatial_configuration(topology_map_path=None, windfarm_map_path=None, apply_windfarm=False):
    """Reload all spatial globals from the configured CSV sources."""
    global TOPOLOGY, ORIGINAL_TOPOLOGY, LAND, WATER, GRID_HEIGHT, GRID_WIDTH
    global single_slice, y_min_water, all_water_depths, max_depth, min_depth, percentile_90_depth
    global REGION_A, REGION_B, REGION_C, REGION_D

    if topology_map_path is not None or windfarm_map_path is not None:
        ecospace_outputs.configure_sources(
            topology_map_path=topology_map_path,
            wind_farm_map_path=windfarm_map_path,
        )

    base_topology = masks(topology=True, windfarm=False)['masks'][0]
    original_topology = [row[:] for row in base_topology]

    if apply_windfarm:
        windfarm_data = masks(topology=False, windfarm=True)
        windfarm_topology = windfarm_data['masks'][0]

        merged_topology = []
        for y in range(len(base_topology)):
            row = []
            for x in range(len(base_topology[y])):
                topo_val = base_topology[y][x]
                wind_val = windfarm_topology[y][x] if y < len(windfarm_topology) and x < len(windfarm_topology[y]) else topo_val
                if topo_val == 0 or wind_val == 1:
                    row.append(0)
                else:
                    row.append(topo_val)
            merged_topology.append(row)

        base_topology = merged_topology

    TOPOLOGY = base_topology
    ORIGINAL_TOPOLOGY = original_topology
    LAND = compute_land_coordinates(TOPOLOGY)
    WATER = [row for row in [[val for val in row if val >= 0] for row in TOPOLOGY] if row]

    GRID_HEIGHT = len(TOPOLOGY)
    GRID_WIDTH = len(TOPOLOGY[0]) if GRID_HEIGHT > 0 else 0
    single_slice = GRID_HEIGHT // 4
    y_min_water = int(min(WATER[-1])) if WATER else 0

    all_water_depths = [val for row in TOPOLOGY for val in row if val > 0]
    max_depth = np.max(all_water_depths) if all_water_depths else 0
    min_depth = np.min(all_water_depths) if all_water_depths else 0
    percentile_90_depth = np.percentile(all_water_depths, 95) if all_water_depths else max_depth

    REGION_A = define_region('A', topology_matrix=ORIGINAL_TOPOLOGY)
    REGION_B = define_region('B', topology_matrix=ORIGINAL_TOPOLOGY)
    REGION_C = define_region('C', topology_matrix=ORIGINAL_TOPOLOGY)
    REGION_D = define_region('D', topology_matrix=ORIGINAL_TOPOLOGY)

    region_d_set = set(tuple(cell) for cell in REGION_D)
    REGION_C = [cell for cell in REGION_C if tuple(cell) not in region_d_set]

    print(f"[DEBUG] Loaded topology: GRID_WIDTH={GRID_WIDTH}, GRID_HEIGHT={GRID_HEIGHT}")
    print(f"[DEBUG] Depth calculation:")
    print(f"  min_depth = {min_depth}, max_depth = {max_depth}")
    print(f"  percentile_90_depth = {percentile_90_depth}")
    print(f"  Total water cells: {len(all_water_depths)}")

    return TOPOLOGY



def define_region(REGION_NAME, topology_matrix=None) :
    if topology_matrix is None:
        topology_matrix = TOPOLOGY
    
    if REGION_NAME == 'A' : 
        center_value = min_depth
        radius = 20
    elif REGION_NAME == 'B' : 
        center_value = (max_depth - min_depth)/4 + min_depth
        radius = 20
    elif REGION_NAME == 'C' : 
        center_value = 3*(max_depth - min_depth)/4 + min_depth
        radius = 30
    elif REGION_NAME == 'D' : 
       center_value = percentile_90_depth
       radius = 20
    
    # Convert to int to match TOPOLOGY values
    center_value = int(round(center_value))
    
    # DEBUG: Print center value details
    print(f"\n[DEBUG] Region {REGION_NAME}:")
    print(f"  center_value = {center_value} (type: {type(center_value).__name__})")
    print(f"  min_depth = {min_depth}, max_depth = {max_depth}")
    
    result_indices, result_values = get_neighbors_by_euclidean_distance_as_xy(topology_matrix, center_value, radius = radius)
    
    print(f"  Found {len(result_indices)} cells in the region")
    if result_indices:
        print(f"  Values in region: min={min(result_values)}, max={max(result_values)}")
    
    return result_indices

reload_spatial_configuration()

print(f"\n[DEBUG] After removing overlaps:")
print(f"  REGION_C: {len(REGION_C)} cells")
print(f"  REGION_D: {len(REGION_D)} cells")



# =============================================================================
# HOTSPOT LOCATIONS
# =============================================================================

# High-density fishing spots (coordinates [x, y])

def get_hotspots_for_step(step, region_name):
    """
    Retourne les 2 hotspots avec la plus haute concentration pour une région à un step donné.
    Chaque date Ecospace = 30 steps du modèle.
    La première date Ecospace correspond à step 0.
    Si Ecospace n'est pas disponible, utilise les valeurs de TOPOLOGY pour trouver les hotspots.
    """
    # Sélectionner la région
    region_map = {
        'A': REGION_A,
        'B': REGION_B,
        'C': REGION_C,
        'D': REGION_D
    }
    region = region_map.get(region_name, [])
    
    if not region:
        return []
    
    # Essayer d'utiliser Ecospace si disponible
    if ecospace_outputs._ecospace_data_cache is not None:
        try:
            ecospace_data = ecospace_outputs._ecospace_data_cache
            if ecospace_data and 'maps' in ecospace_data:
                date_index = step // 30
                
                # Gestion des limites
                if date_index >= len(ecospace_data['maps']['map']):
                    date_index = len(ecospace_data['maps']['map']) - 1
                
                fish_map = np.array(ecospace_data['maps']['map'][date_index][0])
                
                # Trouver les 2 points avec les plus hautes concentrations
                top_coords = sorted(region, key=lambda xy: fish_map[xy[1]][xy[0]], reverse=True)[:3]
                if len(top_coords) == 3:
                    return top_coords
        except Exception as e:
            pass
    
    # Fallback: utiliser les valeurs TOPOLOGY pour trouver les hotspots
    top_coords = sorted(region, key=lambda xy: TOPOLOGY[xy[1]][xy[0]], reverse=True)[:3]
    return top_coords


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
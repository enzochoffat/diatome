"""Configuration constants for the FIBE fishery model.

This module centralises all model parameters, making them easy to modify
for experiments and sensitivity analysis.
"""

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src import ecospace_outputs
from src.ecospace_outputs import get_ecospace_data
from src.ecospace_outputs import masks
from src.ecospace_outputs import plot_masks


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

GRID_WIDTH: int = 0
GRID_HEIGHT: int = 0

TOPOLOGY: List[List[int]] = []
ORIGINAL_TOPOLOGY: List[List[int]] = []
LAND: List[List[int]] = []
WATER: List[List[int]] = []

single_slice: int = 0
y_min_water: int = 0
all_water_depths: np.ndarray = np.array([])
max_depth: int = 0
min_depth: int = 0
percentile_90_depth: float = 0.0

REGION_A: List[List[int]] = []
REGION_B: List[List[int]] = []
REGION_C: List[List[int]] = []
REGION_D: List[List[int]] = []


def compute_land_coordinates(
    topo_matrix: List[List[float]],
) -> List[List[int]]:
    """Computes coordinates of all land cells in the topology matrix.

    A cell is considered land if its value is 0 or below the floating-point
    threshold 1e-29.

    Args:
        topo_matrix: 2-D grid of depth/topology values.

    Returns:
        List of [x, y] coordinate pairs for all land cells.
    """
    return [
        [x, y]
        for y in range(len(topo_matrix))
        for x in range(len(topo_matrix[y]))
        if topo_matrix[y][x] == 0 or topo_matrix[y][x] < 1e-29
    ]


def get_neighbors_by_euclidean_distance(
    matrix: List[List[int]],
    center_value: int,
    radius: int = 7,
) -> Tuple[List[Tuple[int, int]], List[int]]:
    """Finds all cells within a given Euclidean distance of a centre value.

    Identifies all grid cells whose value matches ``center_value``, then
    returns every other positive-valued cell within ``radius`` of at least
    one such centre.

    Args:
        matrix: 2-D integer grid.
        center_value: Grid value used to locate centre cells.
        radius: Maximum Euclidean distance from any centre cell.

    Returns:
        A tuple of (indices, values) where indices is a list of (row, col)
        pairs and values contains the corresponding grid values.
    """
    arr = np.array(matrix)
    centers = np.argwhere(arr == center_value)
    print(
        f"    [get_neighbors] Looking for center_value={center_value},"
        f" found {len(centers)} centers"
    )

    if centers.size == 0:
        unique_vals = sorted(
            {v for row in matrix for v in row if v > 0}
        )[:10]
        print(
            f"    [get_neighbors] WARNING: No centers found!"
            f" Unique values: {unique_vals}..."
        )
        return [], []

    rows, cols = arr.shape
    rr, cc = np.meshgrid(
        np.arange(rows), np.arange(cols), indexing="ij"
    )

    dists = np.sqrt(
        (rr[..., None] - centers[:, 0]) ** 2
        + (cc[..., None] - centers[:, 1]) ** 2
    )
    min_dist = np.min(dists, axis=2)
    mask = (min_dist <= radius) & (arr != center_value) & (arr > 0)

    indices = np.argwhere(mask)
    values = arr[mask]
    return indices.tolist(), values.tolist()


def get_neighbors_by_euclidean_distance_as_xy(
    matrix: List[List[int]],
    center_value: int,
    radius: int = 7,
) -> Tuple[List[List[int]], List[int]]:
    """Wraps ``get_neighbors_by_euclidean_distance`` returning (x, y) pairs.

    Args:
        matrix: 2-D integer grid.
        center_value: Grid value used to locate centre cells.
        radius: Maximum Euclidean distance from any centre cell.

    Returns:
        A tuple of (xy_indices, values) where xy_indices is a list of
        [col, row] pairs (i.e. [x, y]) and values contains the
        corresponding grid values.
    """
    indices, values = get_neighbors_by_euclidean_distance(
        matrix, center_value, radius
    )
    xy_indices = [[col, row] for row, col in indices]
    return xy_indices, values


def reload_spatial_configuration(
    topology_map_path: Optional[str] = None,
    windfarm_map_path: Optional[str] = None,
    apply_windfarm: bool = False,
) -> List[List[int]]:
    """Loads and rebuilds all spatial globals from source files.

    Optionally merges a wind-farm mask into the base topology before
    deriving region definitions and depth statistics.

    Args:
        topology_map_path: Optional path to a custom topology raster.
        windfarm_map_path: Optional path to a wind-farm raster.
        apply_windfarm: If True, subtracts the wind-farm footprint from
            the topology, marking those cells as land.

    Returns:
        The updated TOPOLOGY grid as a 2-D list.
    """
    global TOPOLOGY, ORIGINAL_TOPOLOGY, LAND, WATER, GRID_HEIGHT, GRID_WIDTH
    global single_slice, y_min_water, all_water_depths
    global max_depth, min_depth, percentile_90_depth
    global REGION_A, REGION_B, REGION_C, REGION_D

    if topology_map_path is not None or windfarm_map_path is not None:
        ecospace_outputs.configure_sources(
            topology_map_path=topology_map_path,
            wind_farm_map_path=windfarm_map_path,
        )

    base_topology = np.array(
        masks(topology=True, windfarm=False)["masks"][0]
    )
    original_topology = base_topology.copy()

    if apply_windfarm:
        wf = np.array(masks(topology=False, windfarm=True)["masks"][0])
        h, w = base_topology.shape
        wf_resized = np.zeros_like(base_topology)
        h_wf, w_wf = wf.shape
        wf_resized[: min(h, h_wf), : min(w, w_wf)] = wf[:h, :w]
        base_topology = np.where(wf_resized == 1, 0, base_topology)

    TOPOLOGY = base_topology.tolist()
    ORIGINAL_TOPOLOGY = original_topology.tolist()

    GRID_HEIGHT, GRID_WIDTH = base_topology.shape
    single_slice = GRID_HEIGHT // 4

    positive_mask = base_topology > 0
    WATER = [
        row[row >= 0].tolist()
        for row in base_topology
        if np.any(row >= 0)
    ]
    all_water_depths = base_topology[positive_mask]
    y_min_water = int(np.min(WATER[-1])) if WATER else 0

    if all_water_depths.size > 0:
        max_depth = int(np.max(all_water_depths))
        min_depth = int(np.min(all_water_depths))
        percentile_90_depth = float(np.percentile(all_water_depths, 90))
    else:
        max_depth = min_depth = 0
        percentile_90_depth = 0.0

    LAND = compute_land_coordinates(TOPOLOGY)

    REGION_A = define_region("A", ORIGINAL_TOPOLOGY)
    REGION_B = define_region("B", ORIGINAL_TOPOLOGY)
    REGION_C = define_region("C", ORIGINAL_TOPOLOGY)
    REGION_D = define_region("D", ORIGINAL_TOPOLOGY)

    set_a = {tuple(cell) for cell in REGION_A}
    set_b = {tuple(cell) for cell in REGION_B}
    set_c = {tuple(cell) for cell in REGION_C}
    set_d = {tuple(cell) for cell in REGION_D}

    set_c -= set_d
    set_b -= set_c | set_d
    set_a -= set_b | set_c | set_d

    REGION_A = list(set_a)
    REGION_B = list(set_b)
    REGION_C = list(set_c)
    REGION_D = list(set_d)

    print("[DEBUG] After removing overlaps:")
    print(f"  REGION_A: {len(REGION_A)} cells")
    print(f"  REGION_B: {len(REGION_B)} cells")
    print(f"  REGION_C: {len(REGION_C)} cells")
    print(f"  REGION_D: {len(REGION_D)} cells")
    print(
        f"[DEBUG] Loaded topology:"
        f" GRID_WIDTH={GRID_WIDTH}, GRID_HEIGHT={GRID_HEIGHT}"
    )
    print("[DEBUG] Depth calculation:")
    print(f"  min_depth = {min_depth}, max_depth = {max_depth}")
    print(f"  percentile_90_depth = {percentile_90_depth}")
    print(f"  Total water cells: {all_water_depths.size}")

    return TOPOLOGY


def define_region(
    region_name: str,
    topology_matrix: Optional[List[List[int]]] = None,
) -> List[List[int]]:
    """Defines the set of grid cells belonging to a named fishing region.

    Region boundaries are derived from depth percentiles of the global
    topology. The four regions correspond to increasing depth bands:
    A (shallow) → D (deep).

    Args:
        region_name: One of ``"A"``, ``"B"``, ``"C"``, or ``"D"``.
        topology_matrix: Topology grid to use. Defaults to ``TOPOLOGY``.

    Returns:
        List of [x, y] cell coordinates that fall within the region.
    """
    if topology_matrix is None:
        topology_matrix = TOPOLOGY

    depth_range = max_depth - min_depth

    region_params: Dict[str, Tuple[float, float]] = {
        "A": (float(min_depth), depth_range / 3),
        "B": (depth_range / 3, depth_range / 6),
        "C": (6 * depth_range / 8 + min_depth, depth_range / 6),
        "D": (float(max_depth - 5), depth_range / 6),
    }

    center_value_f, radius = region_params[region_name]
    center_value = int(round(center_value_f))

    print(f"\n[DEBUG] Region {region_name}:")
    print(
        f"  center_value = {center_value}"
        f" (type: {type(center_value).__name__})"
    )
    print(f"  min_depth = {min_depth}, max_depth = {max_depth}")

    result_indices, result_values = get_neighbors_by_euclidean_distance_as_xy(
        topology_matrix, center_value, radius=radius
    )

    print(f"  Found {len(result_indices)} cells in the region")
    if result_indices:
        print(
            f"  Values in region:"
            f" min={min(result_values)}, max={max(result_values)}"
        )

    return result_indices


reload_spatial_configuration()

print("\n[DEBUG] After removing overlaps:")
print(f"  REGION_A: {len(REGION_A)} cells")
print(f"  REGION_B: {len(REGION_B)} cells")
print(f"  REGION_C: {len(REGION_C)} cells")
print(f"  REGION_D: {len(REGION_D)} cells")


# =============================================================================
# HOTSPOT LOCATIONS
# =============================================================================

def get_hotspots_for_step(
    step: int,
    region_name: str,
) -> List[Tuple[int, int]]:
    """Returns the top-3 hotspots for a region at a given simulation step.

    Each Ecospace date corresponds to 30 model steps. If Ecospace data are
    unavailable the function falls back to raw topology values.

    Args:
        step: Current simulation step.
        region_name: One of ``"A"``, ``"B"``, ``"C"``, or ``"D"``.

    Returns:
        List of up to 3 (x, y) coordinate pairs with the highest fish
        concentration, spaced at least 10 units apart.
    """
    region_map = {
        "A": REGION_A,
        "B": REGION_B,
        "C": REGION_C,
        "D": REGION_D,
    }
    region = region_map.get(region_name, [])

    if not region:
        return []

    if ecospace_outputs._ecospace_data_cache is not None:
        try:
            ecospace_data, _ = ecospace_outputs.get_ecospace_data()
            sum_data = np.sum(ecospace_data, axis=2)

            if sum_data is not None:
                fish_map = np.array(sum_data)
                top_coords = sorted(
                    region,
                    key=lambda xy: fish_map[xy[1]][xy[0]],
                    reverse=True,
                )
                hotspots: List[Tuple[int, int]] = []

                for x, y in top_coords:
                    if all(
                        (x - hx) ** 2 + (y - hy) ** 2 >= 10 ** 2
                        for hx, hy in hotspots
                    ):
                        hotspots.append((x, y))
                    if len(hotspots) == 3:
                        break

                if len(hotspots) == 3:
                    return hotspots
        except Exception:
            pass

    top_coords = sorted(
        region,
        key=lambda xy: TOPOLOGY[xy[1]][xy[0]],
        reverse=True,
    )[:3]
    return top_coords

def load_ports_map(ports_map_path: Optional[str] = None) -> List[List[int]]:
    """Loads the ports map from a CSV file.

    Args:
        ports_map_path: Optional path to a custom ports map CSV.
    Returns:
        2-D list representing the ports map, where each cell contains
        an integer value indicating the presence of a port.
    """
    if ports_map_path is not None:
        ecospace_outputs.configure_sources(ports_map_path=ports_map_path)

    ports_map = np.array(masks(topology=False, windfarm=False)["masks"][0])
    for y in range(ports_map.shape[0]):
        for x in range(ports_map.shape[1]):
            if ports_map[y][x] > 0:
                print(f"[DEBUG] Port found at (x={x}, y={y}) with value {ports_map[y][x]}")
            else:
                continue

    return ports_map.tolist()

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

GROWTH_RATE = 1.0

LOW_CARRYING_CAPACITY = 4
MEDIUM_CARRYING_CAPACITY = 3276
HIGH_CARRYING_CAPACITY = 8736

CARRYING_CAPACITY_A_INITIAL = 219000
CARRYING_CAPACITY_B_INITIAL = 438000
CARRYING_CAPACITY_C_INITIAL = 876000
CARRYING_CAPACITY_D_INITIAL = 876000

INIT_STOCK_SIZE = "halfCarryingCap"


# =============================================================================
# ECONOMIC PARAMETERS
# =============================================================================

FISH_PRICE = 1.0
INITIAL_CAPITAL = 1000

MIN_AGE = 18
MAX_AGE = 65

BANKRUPTCY_THRESHOLD_YEARS = 1
BANKRUPTCY_LAYLOW_DAYS = 30
NEGATIVE_CAPITAL_LAYLOW_PROBABILITY = 0.3
NEGATIVE_CAPITAL_LAYLOW_DAYS = 7
SAFETY_BUFFER_DAYS = 7


# =============================================================================
# FISHER TYPE: ARCHIPELAGO
# =============================================================================

ARCHIPELAGO_COST_EXISTENCE = 0.5
ARCHIPELAGO_COST_ACTIVITY = 0.5
ARCHIPELAGO_CATCHABILITY = 5
ARCHIPELAGO_ACCESSIBLE_REGIONS = ["A"]
ARCHIPELAGO_MAX_GOOD_SPOTS = 5


# =============================================================================
# FISHER TYPE: COASTAL
# =============================================================================

COASTAL_COST_EXISTENCE = 1.0
COASTAL_COST_ACTIVITY = 1.0
COASTAL_CATCHABILITY = 10
COASTAL_ACCESSIBLE_REGIONS = ["A", "B"]
COASTAL_MAX_GOOD_SPOTS = 3


# =============================================================================
# FISHER TYPE: TRAWLER
# =============================================================================

TRAWLER_COST_EXISTENCE = 5.0
TRAWLER_COST_ACTIVITY = 5.0
TRAWLER_CATCHABILITY = 50
TRAWLER_ACCESSIBLE_REGIONS = ["B", "C", "D"]
TRAWLER_MAX_GOOD_SPOTS = 2
TRAWLER_STORAGE_CAPACITY = 50


# =============================================================================
# TRAVEL COSTS
# =============================================================================

LOW_COST_TRAVEL = 2.5
MEDIUM_COST_TRAVEL = 5.0
MEDIUM_COST_TRAVEL_BIGVESSEL = 8.0
HIGH_COST_TRAVEL = 15.0
INTER_REGION_TRAVEL_MULTIPLIER = 0.5
TRAVEL_COST_PER_UNIT = 1.0


# =============================================================================
# DECISION-MAKING PARAMETERS
# =============================================================================

DEFAULT_MEMORY_SIZE = 365
SPATIAL_MEMORY_MAX_AGE = 365 * 1

SATISFACTION_HOME_THRESHOLD = 0.5
SATISFACTION_GROWTH_THRESHOLD = 0.5
SCARCE_PERCEPTION_THRESHOLD = -0.05

GOOD_SPOT_EFFICIENCY_THRESHOLD = 0.7
SIMPLE_FISHING_PROBABILITY = 0.5

MEMORY_RECENT_WINDOW = 5
MEMORY_OLDER_WINDOW = 10
MEMORY_WEEKLY_WINDOW = 7
MEMORY_BIWEEKLY_WINDOW = 14
MEMORY_MONTHLY_WINDOW = 30

SCARCITY_CATCH_RATIO_THRESHOLD = 0.5
SCARCITY_MIN_MEMORY = 10
EXPLORATION_PHASE_TRIPS = 5

TRAWLER_PROFIT_THRESHOLD_DAYS = 1


# =============================================================================
# WEATHER PARAMETERS
# =============================================================================

BAD_WEATHER_PROBABILITY = 0.1


# =============================================================================
# SOCIAL ATTRIBUTES
# =============================================================================

PARTNER_PROBABILITY = 0.5
SD_CARCAP = 0.1
HOTSPOT_HIGH_RADIUS = 1.5
HOTSPOT_MEDIUM_RADIUS = 3.0


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_region_initial_capacity(region_name: str) -> int:
    """Returns the initial carrying capacity for a named region.

    Args:
        region_name: Region identifier, one of ``"A"``, ``"B"``,
            ``"C"``, ``"D"``, ``"LAND"``, or ``"NULL"``.

    Returns:
        Initial carrying capacity (fish count). Returns 0 for unknown
        or non-fishing regions.
    """
    capacities: Dict[str, int] = {
        "A": CARRYING_CAPACITY_A_INITIAL,
        "B": CARRYING_CAPACITY_B_INITIAL,
        "C": CARRYING_CAPACITY_C_INITIAL,
        "D": CARRYING_CAPACITY_D_INITIAL,
        "LAND": 0,
        "NULL": 0,
    }
    return capacities.get(region_name, 0)


def get_msy_stock(carrying_capacity: int) -> int:
    """Calculates the Maximum Sustainable Yield stock level.

    MSY occurs at 50 % of carrying capacity (K/2).

    Args:
        carrying_capacity: Total carrying capacity of the region.

    Returns:
        MSY stock level (rounded to the nearest integer).
    """
    return round(carrying_capacity / 2)


def get_fisher_config(fisher_type: str) -> Dict:
    """Returns all configuration parameters for a given fisher type.

    Args:
        fisher_type: One of ``"archipelago"``, ``"coastal"``,
            or ``"trawler"``.

    Returns:
        Dictionary of configuration values. Returns an empty dict if
        the fisher type is not recognised.
    """
    configs: Dict[str, Dict] = {
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
        },
    }
    return configs.get(fisher_type, {})


def get_travel_cost(
    region: str,
    fisher_type: str = "coastal",
) -> float:
    """Calculates the travel cost to reach a region.

    Args:
        region: Target region, one of ``"A"``, ``"B"``, ``"C"``,
            or ``"D"``.
        fisher_type: Fisher type; affects cost for region ``"B"``
            (trawlers pay more).

    Returns:
        Travel cost in SEK. Returns 0.0 for unrecognised regions.
    """
    if region == "A":
        return LOW_COST_TRAVEL
    if region == "B":
        return (
            MEDIUM_COST_TRAVEL_BIGVESSEL
            if fisher_type == "trawler"
            else MEDIUM_COST_TRAVEL
        )
    if region in {"C", "D"}:
        return HIGH_COST_TRAVEL
    return 0.0


def get_bankruptcy_threshold(cost_existence: float) -> float:
    """Calculates the negative-capital threshold that triggers bankruptcy.

    Args:
        cost_existence: Daily existence cost for the fisher (SEK).

    Returns:
        The (negative) capital level below which the fisher is bankrupt.
    """
    return -(cost_existence * YEAR * BANKRUPTCY_THRESHOLD_YEARS)


def get_safety_buffer(cost_existence: float) -> float:
    """Calculates the capital safety buffer for trip-affordability checks.

    Args:
        cost_existence: Daily existence cost for the fisher (SEK).

    Returns:
        Safety buffer amount in SEK.
    """
    return cost_existence * SAFETY_BUFFER_DAYS


# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================

def validate_config() -> None:
    """Validates all configuration parameters for internal consistency.

    Raises:
        AssertionError: If any parameter violates its constraint.
    """
    assert GROWTH_RATE > 0, "Growth rate must be positive"
    assert FISH_PRICE > 0, "Fish price must be positive"
    assert INITIAL_CAPITAL > 0, "Initial capital must be positive"

    assert MIN_AGE < MAX_AGE, "MIN_AGE must be less than MAX_AGE"
    assert MIN_AGE >= 0, "MIN_AGE must be non-negative"

    assert ARCHIPELAGO_COST_EXISTENCE > 0, "Existence costs must be positive"
    assert COASTAL_COST_EXISTENCE > 0, "Existence costs must be positive"
    assert TRAWLER_COST_EXISTENCE > 0, "Existence costs must be positive"

    assert ARCHIPELAGO_CATCHABILITY > 0, "Catchability must be positive"
    assert COASTAL_CATCHABILITY > 0, "Catchability must be positive"
    assert TRAWLER_CATCHABILITY > 0, "Catchability must be positive"

    assert GRID_WIDTH > 0 and GRID_HEIGHT > 0, (
        "Grid dimensions must be positive"
    )

    assert 0 <= GOOD_SPOT_EFFICIENCY_THRESHOLD <= 1, (
        "Efficiency threshold must be in [0,1]"
    )
    assert 0 <= SATISFACTION_HOME_THRESHOLD <= 1, (
        "Satisfaction thresholds must be in [0,1]"
    )
    assert 0 <= SATISFACTION_GROWTH_THRESHOLD <= 1, (
        "Satisfaction thresholds must be in [0,1]"
    )

    assert 0 <= BAD_WEATHER_PROBABILITY <= 1, (
        "Weather probability must be in [0,1]"
    )
    assert 0 <= SIMPLE_FISHING_PROBABILITY <= 1, (
        "Fishing probability must be in [0,1]"
    )
    assert 0 <= NEGATIVE_CAPITAL_LAYLOW_PROBABILITY <= 1, (
        "Laylow probability must be in [0,1]"
    )

    valid_stock_sizes = {
        "random", "halfCarryingCap", "carryingCap", "quartCarryingCap"
    }
    assert INIT_STOCK_SIZE in valid_stock_sizes, (
        "Invalid initial stock size option"
    )
    print("Configuration validated successfully")


if __name__ == "__main__":
    validate_config()

    print("\n" + "=" * 60)
    print("FIBE MODEL CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"\nGrid: {GRID_WIDTH} × {GRID_HEIGHT}")
    print(f"Growth rate: {GROWTH_RATE * 100}% per year")
    print(f"Fish price: {FISH_PRICE} SEK")
    print(f"Initial capital: {INITIAL_CAPITAL} SEK")

    print("\nFisher types:")
    for ftype in ["archipelago", "coastal", "trawler"]:
        cfg = get_fisher_config(ftype)
        print(
            f"  {ftype.capitalize():12} -"
            f" Catchability: {cfg['catchability']:3},"
            f" Existence: {cfg['cost_existence']:.1f} SEK,"
            f" Regions: {', '.join(cfg['accessible_regions'])}"
        )

    print("\nRegional capacities (initial):")
    for region in ["A", "B", "C", "D"]:
        cap = get_region_initial_capacity(region)
        msy = get_msy_stock(cap)
        print(
            f"  Region {region}: {cap:>9,} fish (MSY: {msy:>9,})"
        )

    print("\nDecision-making parameters:")
    print(f"  Memory size: {DEFAULT_MEMORY_SIZE} trips")
    print(
        f"  Satisfaction thresholds:"
        f" home={SATISFACTION_HOME_THRESHOLD},"
        f" growth={SATISFACTION_GROWTH_THRESHOLD}"
    )
    print(
        f"  Good spot efficiency: {GOOD_SPOT_EFFICIENCY_THRESHOLD:.0%}"
    )
    print(f"  Scarcity threshold: {SCARCE_PERCEPTION_THRESHOLD}")
    print("=" * 60)
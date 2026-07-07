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
BANKRUPTCY_LAYLOW_DAYS = 7
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

SOCIAL_INFLUENCE = "descriptiveNorm"


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
"""Global constants for the fishing simulation model.

This module defines all configuration constants used across the
simulation, including time scales, economic parameters, fisher
types, travel costs, decision-making rules, weather conditions,
and social attributes.

All values are immutable and must not be modified at runtime.
"""

from typing import Final, List

# =============================================================================
# TIME CONSTANTS
# =============================================================================

WEEK: Final[int] = 7
MONTH: Final[int] = 28
SEASON: Final[int] = 84
HALFYEAR: Final[int] = 168
YEAR: Final[int] = 365

# =============================================================================
# ECONOMIC PARAMETERS
# =============================================================================

FISH_PRICE: Final[float] = 1.0
INITIAL_CAPITAL: Final[int] = 1000

MIN_AGE: Final[int] = 18
MAX_AGE: Final[int] = 65

BANKRUPTCY_THRESHOLD_YEARS: Final[int] = 1
BANKRUPTCY_LAYLOW_DAYS: Final[int] = 7

NEGATIVE_CAPITAL_LAYLOW_PROBABILITY: Final[float] = 0.3
NEGATIVE_CAPITAL_LAYLOW_DAYS: Final[int] = 7

SAFETY_BUFFER_DAYS: Final[int] = 7

# =============================================================================
# FISHER TYPE: ARCHIPELAGO
# =============================================================================

ARCHIPELAGO_COST_EXISTENCE: Final[float] = 0.5
ARCHIPELAGO_COST_ACTIVITY: Final[float] = 0.5
ARCHIPELAGO_CATCHABILITY: Final[int] = 5
ARCHIPELAGO_ACCESSIBLE_REGIONS: Final[List[str]] = ["A"]
ARCHIPELAGO_MAX_GOOD_SPOTS: Final[int] = 5

# =============================================================================
# FISHER TYPE: COASTAL
# =============================================================================

COASTAL_COST_EXISTENCE: Final[float] = 1.0
COASTAL_COST_ACTIVITY: Final[float] = 1.0
COASTAL_CATCHABILITY: Final[int] = 10
COASTAL_ACCESSIBLE_REGIONS: Final[List[str]] = ["A", "B"]
COASTAL_MAX_GOOD_SPOTS: Final[int] = 3

# =============================================================================
# FISHER TYPE: TRAWLER
# =============================================================================

TRAWLER_COST_EXISTENCE: Final[float] = 5.0
TRAWLER_COST_ACTIVITY: Final[float] = 5.0
TRAWLER_CATCHABILITY: Final[int] = 50
TRAWLER_ACCESSIBLE_REGIONS: Final[List[str]] = ["B", "C", "D"]
TRAWLER_MAX_GOOD_SPOTS: Final[int] = 2
TRAWLER_STORAGE_CAPACITY: Final[int] = 50

# =============================================================================
# TRAVEL COSTS
# =============================================================================

LOW_COST_TRAVEL: Final[float] = 2.5
MEDIUM_COST_TRAVEL: Final[float] = 5.0
MEDIUM_COST_TRAVEL_BIGVESSEL: Final[float] = 8.0
HIGH_COST_TRAVEL: Final[float] = 15.0

INTER_REGION_TRAVEL_MULTIPLIER: Final[float] = 0.5
TRAVEL_COST_PER_UNIT: Final[float] = 1.0

# =============================================================================
# DECISION-MAKING PARAMETERS
# =============================================================================

DEFAULT_MEMORY_SIZE: Final[int] = 365
SPATIAL_MEMORY_MAX_AGE: Final[int] = 365 * 1

SATISFACTION_HOME_THRESHOLD: Final[float] = 0.5
SATISFACTION_GROWTH_THRESHOLD: Final[float] = 0.5
SCARCE_PERCEPTION_THRESHOLD: Final[float] = -0.05

GOOD_SPOT_EFFICIENCY_THRESHOLD: Final[float] = 0.7
SIMPLE_FISHING_PROBABILITY: Final[float] = 0.5

MEMORY_RECENT_WINDOW: Final[int] = 5
MEMORY_OLDER_WINDOW: Final[int] = 10
MEMORY_WEEKLY_WINDOW: Final[int] = 7
MEMORY_BIWEEKLY_WINDOW: Final[int] = 14
MEMORY_MONTHLY_WINDOW: Final[int] = 30

SCARCITY_CATCH_RATIO_THRESHOLD: Final[float] = 0.5
SCARCITY_MIN_MEMORY: Final[int] = 10
EXPLORATION_PHASE_TRIPS: Final[int] = 5

TRAWLER_PROFIT_THRESHOLD_DAYS: Final[int] = 1

SOCIAL_INFLUENCE: Final[str] = "descriptiveNorm"

# =============================================================================
# WEATHER PARAMETERS
# =============================================================================

BAD_WEATHER_PROBABILITY: Final[float] = 0.1

# =============================================================================
# SOCIAL ATTRIBUTES
# =============================================================================

PARTNER_PROBABILITY: Final[float] = 0.5
SD_CARCAP: Final[float] = 0.1

HOTSPOT_HIGH_RADIUS: Final[float] = 1.5
HOTSPOT_MEDIUM_RADIUS: Final[float] = 3.0

# =============================================================================
# DENSITY LEVELS
# =============================================================================

LOW: Final[str] = "low"
MEDIUM: Final[str] = "medium"
HIGH: Final[str] = "high"
MEDIUM_HIGH: Final[str] = "medium_high"
LOW_MEDIUM: Final[str] = "low_medium"
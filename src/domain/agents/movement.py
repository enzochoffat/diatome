import warnings
from typing import Optional, Tuple
from src import config
from src.domain.environment import distance
from src.domain.environment import restricted_areas


def is_restricted(self, x: int, y: int) -> bool:
    """Legacy: fishing restriction (habitat + zone not open). Deprecated."""
    warnings.warn("movement.is_restricted is deprecated, use is_fishing_restricted or restricted_areas.can_fish", DeprecationWarning, stacklevel=2)
    return is_fishing_restricted(self, x, y)

def is_fishing_restricted(self, x: int, y: int) -> bool:
    """True if fishing is forbidden at (x,y) for this agent (habitat or zone not open)."""
    try:
        fleet = getattr(self, "fisher_type", None)
        date = getattr(self.model, "current_date", None) if hasattr(self, "model") else None
        if fleet is not None and date is not None:
            return not restricted_areas.can_fish(fleet, x, y, date)
    except Exception:
        pass
    # Fallback legacy habitat check
    if self.restricted_mask is None:
        return False
    try:
        return bool(self.restricted_mask[y][x])
    except Exception:
        return False

def is_navigation_restricted(self, x: int, y: int) -> bool:
    """True if transit is forbidden at (x,y) (zone fermé only)."""
    try:
        fleet = getattr(self, "fisher_type", None)
        date = getattr(self.model, "current_date", None) if hasattr(self, "model") else None
        if fleet is not None and date is not None:
            return not restricted_areas.can_navigate(fleet, x, y, date)
    except Exception:
        pass
    return False


def move_to(self, x: int, y: int) -> None:
        if not (
            0 <= x < self.model.grid.width
            and 0 <= y < self.model.grid.height
        ):
            return

        if is_navigation_restricted(self, x, y):
            return

        if self.pos is not None:
            self.model.grid.remove_agent(self)
        self.model.grid.place_agent(self, (x, y))
        self.current_location = (x, y)
        self.display_location = (x, y)


def calculate_travel_cost(
        self,
        from_pos: Optional[Tuple[int, int]],
        to_pos: Optional[Tuple[int, int]],
    ) -> float:
        if from_pos is None or to_pos is None:
            return 0.0
        distance_map = getattr(self, "distance_map", None)
        if not distance_map:
            return 0.0
        return distance.get_distance(distance_map, to_pos[0], to_pos[1])

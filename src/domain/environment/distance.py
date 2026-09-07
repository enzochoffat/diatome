import math
import heapq
import warnings
from pathlib import Path
from typing import Union, Optional, Tuple, Dict

from src.domain.environment.spatial_utils import read_depth_map
from src.domain.environment import restricted_areas

# Cache port x fleet x month (YYYY-MM)
_distance_cache: Dict[Tuple[Tuple[int,int], str, str], list[list[float]]] = {}

def create_distance_map(
        self,
        port_location: tuple[int, int],
        fleet: Optional[str] = None,
        ) -> list[list[float]]:
    """Creates a distance map from a port location for a given fleet.

    Transit is blocked only on land (depth 0) and on zones with statut 0 (fermé).
    Zones with statut 1 (navigable) and habitats interdits do NOT block transit
    (they only block fishing).

    Args:
        self: Model instance providing current_date and grid.
        port_location: (x,y) port coordinates.
        fleet: Fisher type for navigation restrictions (archipelago/coastal/trawler).
               If None, falls back to legacy behavior (any zone blocks) for compat.
    """
    base_map = read_depth_map()
    grid_height = len(base_map)
    grid_width = len(base_map[0]) if grid_height > 0 else 0
    R = 6371
    cell_size_deg = 0.0202
    dh_cell = cell_size_deg * (math.pi / 180) * R
    lat_rad = math.radians(53.5260)
    dw_cell = cell_size_deg * (math.pi / 180) * R * math.cos(lat_rad)

    # Resolve fleet for cache key and navigation check
    current_date = getattr(self, "current_date", None)

    normalized_map = []
    for y, row in enumerate(base_map):
        norm_row = []
        for x, val in enumerate(row):
            if val == 0:
                norm_row.append(0)
            else:
                if fleet is not None and current_date is not None:
                    # New logic: transit blocked only if can_navigate == False
                    if not restricted_areas.can_navigate(fleet, x, y, current_date):
                        norm_row.append(0)
                    else:
                        norm_row.append(1)
                else:
                    # Legacy fallback: any zone blocks
                    # Use is_restricted_area for compat if fleet not provided
                    warnings.warn("create_distance_map called without fleet, using legacy zone check", DeprecationWarning, stacklevel=2)
                    # is_restricted_area is deprecated but still works (zone presence)
                    try:
                        if restricted_areas.is_restricted_area(x, y, current_date):
                            norm_row.append(0)
                        else:
                            norm_row.append(1)
                    except Exception:
                        norm_row.append(1)
            # keep row append outside else? need handle val==0 case already
        # Ensure norm_row appended? Actually we handled val==0 inside loop, but we appended inside each branch
        # The above appends per cell, but we need to ensure we appended for val==0 too
        # Already handled: val==0 -> 0, else -> check
        normalized_map.append(norm_row)

    distance_map = [[float('inf') for _ in range(grid_width)] for _ in range(grid_height)]

    if not is_on_grid(port_location[0], port_location[1], grid_width, grid_height):
        raise ValueError(f"Port location {port_location} is out of grid bounds.")

    heap = []
    px, py = port_location
    heapq.heappush(heap, (0.0, px, py))
    distance_map[py][px] = 0.0

    direction_weights = {
        (1, 0): dw_cell,
        (-1, 0): dw_cell,
        (0, 1): dh_cell,
        (0, -1): dh_cell
    }

    while heap:
        current_dist, x, y = heapq.heappop(heap)

        if current_dist > distance_map[y][x]:
            continue

        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            
            if 0 <= nx < grid_width and 0 <= ny < grid_height and normalized_map[ny][nx] == 1:
                
                weight = direction_weights.get((dx, dy), 1.0)
                new_dist = current_dist + weight

                if new_dist < distance_map[ny][nx]:
                    distance_map[ny][nx] = new_dist
                    heapq.heappush(heap, (new_dist, nx, ny))

    for y in range(grid_height):
        for x in range(grid_width):
            if distance_map[y][x] == float('inf'):
                distance_map[y][x] = -1

    return distance_map

def get_cached_distance_map(self, port_location: tuple[int,int], fleet: str) -> list[list[float]]:
    """Returns cached distance map for port x fleet x month (YYYY-MM)."""
    current_date = getattr(self, "current_date", None)
    if current_date is None:
        # No date, no cache
        return create_distance_map(self, port_location, fleet)
    # Build key
    try:
        year = current_date.year
        month = current_date.month
        key_month = f"{year:04d}-{month:02d}"
    except Exception:
        key_month = str(current_date)
    key = (tuple(port_location), fleet.lower() if fleet else "", key_month)
    if key not in _distance_cache:
        _distance_cache[key] = create_distance_map(self, port_location, fleet)
    return _distance_cache[key]

def clear_distance_cache():
    _distance_cache.clear()

def save_distance_map(
    distance_map: list[list[float]],
    file_path: Union[str, Path],
) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        for row in distance_map:
            row_str = ';'.join(str(value) for value in row)
            file.write(row_str + '\n')
            
def normalize_distance_map(distance_map: list[list[float]]) -> list[list[float]]:
    for y, row in enumerate(distance_map):
        for x, value in enumerate(row):
            if value == 0.0:
                distance_map[y][x] = 0
            else:
                distance_map[y][x] = 1

def is_on_grid(x: int, y: int, grid_width: int, grid_height: int) -> bool:
    return 0 <= x < grid_width and 0 <= y < grid_height

def get_distance(distance_map: list[list[float]], x: int, y: int) -> float:
    return float(distance_map[y][x])

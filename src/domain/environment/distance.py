import math
import heapq

from src.domain.environment.spatial_utils import read_depth_map
from src.domain.environment.restricted_areas import is_restricted_area

def create_distance_map(
        self,
        port_location: tuple[int, int],
        ) -> list[list[float]]:
    """Creates a distance map from a port location."""
    global _distance_map
    base_map = read_depth_map()
    grid_height = len(base_map)
    grid_width = len(base_map[0]) if grid_height > 0 else 0
    R = 6371
    cell_size_deg = 0.0202
    dh_cell = cell_size_deg * (math.pi / 180) * R
    lat_rad = math.radians(53.5260)
    dw_cell = cell_size_deg * (math.pi / 180) * R * math.cos(lat_rad)

    normalized_map = []
    for y, row in enumerate(base_map):
        norm_row = []
        for x, val in enumerate(row):
            if val == 0 or is_restricted_area(x, y, self.current_date):
                norm_row.append(0)
            else:
                norm_row.append(1)
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

        # Si on a déjà trouvé un chemin plus court, on ignore
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

    _distance_map = distance_map

    return _distance_map

def save_distance_map(distance_map: list[list[float]], file_path: str) -> None:
    """Saves the distance map to a CSV file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        for row in distance_map:
            row_str = ';'.join(str(value) for value in row)
            file.write(row_str + '\n')
            
def normalize_distance_map(distance_map: list[list[float]]) -> list[list[float]]:
    """Normalizes the distance map to a range between 0 and 1."""
    for y, row in enumerate(distance_map):
        for x, value in enumerate(row):
            if value == 0.0:
                distance_map[y][x] = 0  # Set restricted areas to 0
            else:
                distance_map[y][x] = 1  # Set other areas to 1

def is_on_grid(x: int, y: int, grid_width: int, grid_height: int) -> bool:
    """Checks if the given coordinates are within the grid boundaries."""
    return 0 <= x < grid_width and 0 <= y < grid_height

def get_distance(x: int, y: int) -> list[list[float]]:
    map = _distance_map
    price = map[y][x]
    print(map[y][x])
    return price
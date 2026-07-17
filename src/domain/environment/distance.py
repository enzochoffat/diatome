from collections import deque

from src.domain.environment.spatial_utils import read_depth_map
from src.domain.environment.restricted_areas import is_restricted_area

def create_distance_map(
        self,
        port_location: tuple[int, int],
        ) -> list[list[float]]:
    """Creates a distance map from a port location."""
    base_map = read_depth_map()
    grid_height = len(base_map)
    grid_width = len(base_map[0]) if grid_height > 0 else 0

    normalized_map = []
    for y, row in enumerate(base_map):
        norm_row = []
        for x, val in enumerate(row):
            if val == 0 or is_restricted_area(x, y, self.current_date):
                norm_row.append(0)
            else:
                norm_row.append(1)
        normalized_map.append(norm_row)

    distance_map = [[-1 for _ in range(grid_width)] for _ in range(grid_height)]

    if not is_on_grid(port_location[0], port_location[1], grid_width, grid_height):
        raise ValueError(f"Port location {port_location} is out of grid bounds.")

    queue = deque()
    px, py = port_location
    queue.append((px, py))
    distance_map[py][px] = 0

    while queue:
        x, y = queue.popleft()
        current_distance = distance_map[y][x]
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < grid_width and 0 <= ny < grid_height and normalized_map[ny][nx] == 1:
                if distance_map[ny][nx] == -1:
                    distance_map[ny][nx] = current_distance + 1
                    queue.append((nx, ny))
    return distance_map

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


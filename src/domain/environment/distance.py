import heapq

from src.domain.environment.spatial_utils import read_depth_map
from src.domain.environment.restricted_areas import is_restricted_area

def create_distance_map(
        self,
        port_location: tuple[int, int],
        ) -> list[list[float]]:
    """Creates a distance map from a port location."""
    distance_map = []
    base_map = read_depth_map()
    grid_height = len(base_map)
    grid_width = len(base_map[0]) if grid_height > 0 else 0
    for y, row in enumerate(base_map):
        distance_row = []
        for x, _ in enumerate(row):
            if base_map[y][x] == 0:  # Skip land cells
                distance_row.append(0)  # Mark land cells with 0
                continue
            if is_restricted_area(x, y, self.current_date):  # Check if the cell is in a restricted area
                distance_row.append(0)  # Mark restricted areas with 0
                continue
            distance_row.append(1)  # Mark accessible areas with 1
        distance_map.append(distance_row)
    normalized_map = [row[:] for row in distance_map]  # Create a copy of the distance map for normalization
    distance_map = [[-1 for _ in range(grid_width)] for _ in range(grid_height)]

    if not is_on_grid(port_location[0], port_location[1], grid_width, grid_height):
        raise ValueError(f"Port location {port_location} is out of grid bounds.")
    
    priority_queue = []  # (distance, (x, y))
    px, py = port_location
    heapq.heappush(priority_queue, (0, px, py))
    distance_map[py][px] = 0  # Distance to the port itself is 0

    while priority_queue:
        current_distance, x, y = heapq.heappop(priority_queue)
        if current_distance > distance_map[y][x] and distance_map[y][x] != -1:
            continue
        for nx, ny in get_neighbors(x, y, grid_width=grid_width, grid_height=grid_height, distance_map=normalized_map):
            new_distance = current_distance + 1
            if distance_map[ny][nx] == -1 or new_distance < distance_map[ny][nx]:
                distance_map[ny][nx] = new_distance
                heapq.heappush(priority_queue, (new_distance, nx, ny))
    save_distance_map(distance_map, "C:\\Users\\enzo.choffat\\Documents\\Stage\\code\\diatome\\Ecospace_outputs\\topology\\Distance.csv")
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

def is_accessible(x: int, y: int, distance_map: list[list[float]]) -> bool:
    """Checks if the given coordinates are accessible (not land or restricted)."""
    return distance_map[y][x] == 1

def get_neighbors(x: int, y: int, grid_width: int, grid_height: int, distance_map: list[list[float]]) -> list[tuple[int, int]]:
    """Returns the neighboring coordinates (up, down, left, right) of a given cell."""
    neighbors = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = x + dx, y + dy
        if is_on_grid(nx, ny, grid_width, grid_height) and is_accessible(nx, ny, distance_map):
            neighbors.append((nx, ny))
    return neighbors
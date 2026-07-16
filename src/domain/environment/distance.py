from src.domain.environment.spatial_utils import read_depth_map
from src.domain.environment.restricted_areas import is_restricted_area

def create_distance_map(
        self,
        port_location: tuple[int, int],
        ) -> list[list[float]]:
    """Creates a distance map from a port location."""
    distance_map = []
    base_map = read_depth_map()
    for y, row in enumerate(base_map):
        distance_row = []
        for x, _ in enumerate(row):
            if base_map[y][x] == 0:  # Skip land cells
                distance_row.append(float('inf'))  # Mark land cells with infinity
                continue
            if is_restricted_area(x, y, self.current_date):  # Check if the cell is in a restricted area
                distance_row.append(float('inf'))  # Mark restricted areas with infinity
                pass
            dx = x - port_location[0]
            dy = y - port_location[1]
            distance = (dx ** 2 + dy ** 2) ** 0.5
            distance_row.append(distance)
        distance_map.append(distance_row)
    return distance_map

def save_distance_map(distance_map: list[list[float]], file_path: str) -> None:
    """Saves the distance map to a CSV file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        for row in distance_map:
            row_str = ';'.join(str(value) for value in row)
            file.write(row_str + '\n')
            
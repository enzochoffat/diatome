from typing import List, Tuple, Optional
import numpy as np

from src.infrastructure.ecospace import ecospace_outputs
from src.infrastructure.ecospace.ecospace_outputs import masks


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

    ports_map = np.array(masks(topology=False, windfarm=False, ports=True)["masks"][0])
    return ports_map.tolist()

def count_ports(ports_map: List[List[int]]) -> int:
    """Counts the number of ports in the ports map.

    Args:
        ports_map: 2-D list representing the ports map.

    Returns:
        The number of ports in the ports map.
    """
    return sum(1 for row in ports_map for cell in row if cell != 0)

def get_port_coordinates() -> List[Tuple[int, int]]:
    """Returns the coordinates of all ports in the ports map.

    Args:
        ports_map: 2-D list representing the ports map.

    Returns:
        A list of tuples representing the coordinates of all ports in the ports map.
    """
    ports_map = load_ports_map()
    list_ports = []
    for y, row in enumerate(ports_map):
        for x, cell in enumerate(row):
            if cell != 0:
                list_ports.append((x, y))
    return list_ports
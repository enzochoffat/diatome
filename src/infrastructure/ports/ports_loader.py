from typing import Dict, List, Tuple, Optional
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

def count_ports(ports_map: List[List[int]]) -> Dict[int, (int,int)]:
    """Counts the number of ports in the ports map.

    Args:
        ports_map: 2-D list representing the ports map.

    Returns:
        A dictionary mapping port IDs to their coordinates.
    """
    port_counts = {}
    counter = 0
    for y, row in enumerate(ports_map):
        for x, cell in enumerate(row):
            if cell != 0:
                port_counts[counter] = (x, y)
                counter += 1
    return port_counts

def get_port_coordinates() -> Dict[int, Tuple[int, int]]:
    """Returns the coordinates of all ports in the ports map.

    Args:
        ports_map: 2-D list representing the ports map.

    Returns:
        A list of tuples representing the coordinates of all ports in the ports map.
    """
    ports_map = load_ports_map()
    dict_ports = count_ports(ports_map)
    return dict_ports
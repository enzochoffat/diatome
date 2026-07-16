
from typing import Tuple, List, Optional
import random
import numpy as np

from src.infrastructure.ecospace import ecospace_outputs

def get_random_position_in_region(
    self, region: str
) -> Optional[Tuple[int, int]]:
    """Returns a random patch position within a named region.

    Args:
        region: Region identifier (``"A"``, ``"B"``, ``"C"``,
            or ``"D"``).

    Returns:
        A random ``(x, y)`` tuple from that region, or None if the
        region contains no patches.
    """
    candidates = [
        pos
        for pos, patch in self.patches.items()
        if patch["region"] == region
    ]
    return random.choice(candidates) if candidates else None

def restricted_habitat(self, habitat: List[str]) -> np.ndarray:
    """Returns a boolean mask of restricted areas based on habitat.

    Args:
        habitat: List of habitat types to not restrict.

    Returns:
        A 2D boolean numpy array where True indicates a restricted
        area.
    """
    habitat_array, habitat_names = ecospace_outputs.load_habitat_map()
    
    restricted_names = [name for name in habitat_names if name not in habitat]
    index = [habitat_names.index(name) for name in restricted_names]
    restricted_layers = habitat_array[:, :, index]
    mask = np.any(restricted_layers > 0, axis=2)

    return mask
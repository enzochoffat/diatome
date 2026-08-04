
from typing import List
import numpy as np

from src.infrastructure.ecospace import ecospace_outputs

def restricted_habitat(self, habitat: List[str]) -> np.ndarray:
    """Returns a boolean mask of forbidden areas based on habitat.

    A cell is restricted when at least one of the fleet's forbidden
    habitats is present there.

    Args:
        habitat: List of habitat types the fleet is forbidden to fish on.

    Returns:
        A 2D boolean numpy array where True indicates a restricted
        area.
    """
    habitat_array, habitat_names = ecospace_outputs.load_habitat_map()

    forbidden_index = [habitat_names.index(name) for name in habitat if name in habitat_names]
    forbidden_layers = habitat_array[:, :, forbidden_index] if forbidden_index else None
    if forbidden_layers is None or forbidden_layers.size == 0:
        return np.zeros((habitat_array.shape[0], habitat_array.shape[1]), dtype=bool)

    forbidden_mask = np.any(forbidden_layers > 0, axis=2)
    return forbidden_mask
import numpy as np
from datetime import datetime
from typing import Optional

from src.infrastructure.ecospace import ecospace_outputs

def load_restricted_area_map(restricted_area_map_path: Optional[str]) -> np.ndarray:
    """Loads the restricted area map from a CSV file.

    Args:
        restricted_area_map_path: The path to the restricted area map CSV file.

    Returns:
        np.ndarray: A 2D boolean numpy array where True indicates a restricted
        area.
    """
    global _restricted_area_map
    if restricted_area_map_path is None:
        raise ValueError("No restricted area map path provided.")

    grid = np.genfromtxt(restricted_area_map_path, delimiter=",", skip_header=1)[:, 1:]
    _restricted_area_map = grid > 0
    return _restricted_area_map

def load_restricted_area_vector(restricted_area_vector_path: Optional[str]) -> np.ndarray:
    """Loads the restricted area vector from a CSV file.

    Args:
        restricted_area_vector_path: The path to the restricted area vector CSV file.

    Returns:
        np.ndarray: A 1D boolean numpy array where True indicates a restricted
        area is closed, open to navigation or open.
    """
    global _restricted_area_vector
    if restricted_area_vector_path is None:
        raise ValueError("No restricted area vector path provided.")

    vector = np.genfromtxt(restricted_area_vector_path, delimiter=",", skip_header=1)[:]
    _restricted_area_vector = vector.astype(int).flatten()
    return _restricted_area_vector

def restricted_area_status(date: datetime) -> str:
    """Checks if a given position is in a restricted area.

    Args:
        x: The x-coordinate of the position.
        y: The y-coordinate of the position.
        date: The date for which to check the restricted area status.

    Returns:
        str: The status of the restricted area at the given position and date.
    """
    global _restricted_area_map
    global _restricted_area_vector
    if _restricted_area_vector[date] == 1:  # Navigation
        return "Navigation"  # Open to navigation
    elif _restricted_area_vector[date] == 2:  # Open
        return "Open"
    else:
        return "Closed"  # Open to closed
    
def is_restricted_area(x: int, y: int, date: datetime) -> bool:
    """Checks if a given position is in a restricted area.

    Args:
        x: The x-coordinate of the position.
        y: The y-coordinate of the position.
        date: The date for which to check the restricted area status.

    Returns:
        bool: True if the position is in a restricted area, False otherwise.
    """
    # global _restricted_area_map
    # if (x, y) in _restricted_area_map:
    #     if _restricted_area_vector[date] == 2:  # Open
    #         return False  # Open to navigation
    #     return True  # Closed or restricted
    # return False  # Not in restricted area
    return None
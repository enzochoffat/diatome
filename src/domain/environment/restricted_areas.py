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

    _restricted_area_map = np.genfromtxt(restricted_area_map_path, delimiter=",", skip_header=1)
    save_restricted_area_map(file_path="C:\\Users\\enzo.choffat\\Documents\\Stage\\code\\diatome\\Ecospace_outputs\\topology\\RestrictedAreasMap.csv",
                             restricted_area_map=_restricted_area_map)
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

    _restricted_area_vector = {}

    with open(restricted_area_vector_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                date_str, status_str = line.strip().split(';')
                date = datetime.strptime(date_str, '%d/%m/%Y').date()
                #print(f"Read wave height for date {date}: {wave_height_str}")
                status = int(status_str)
                _restricted_area_vector[date] = status
            except ValueError:
                # Handle the case where conversion to float fails
                #print(f"Warning: Could not convert wave height to float for line: {line.strip()}")
                continue
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
    #print(f"Checking restricted area status for position ({x}, {y}) on {date}.")
    if _restricted_area_map[int(y), int(x)] > 0.5:
        print(f"Position ({x}, {y}) is in a restricted area on {date}.")
        return True
    return False

def save_restricted_area_map(restricted_area_map: np.ndarray, file_path: str) -> None:
    """Saves the restricted area map to a CSV file.

    Args:
        restricted_area_map: The 2D boolean numpy array representing the
            restricted area map.
        file_path: The path to save the CSV file.
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        for row in restricted_area_map:
            row_str = ';'.join(str(value) for value in row)
            file.write(row_str + '\n')
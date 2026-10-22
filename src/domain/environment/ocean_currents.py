import numpy as np


def load_ocean_current_map(file_path: str) -> dict:
    """
    Load the ocean current map from a CSV file.

    Args:
        file_path (str): The path to the CSV file containing the ocean current data.
    
    Returns:
        dict: A dictionary where keys are (latitude, longitude) tuples and values are the corresponding ocean current values.
    """
    return None

def read_currents_map(date: str) -> np.ndarray:
    """
    Read the ocean current map for a specific date.

    Args:
        date (str): The date for which to read the ocean current map in 'YYYY-MM-DD' format.

    Returns:
        np.ndarray: A 2D numpy array representing the ocean current values for the specified date.
    """
    return None
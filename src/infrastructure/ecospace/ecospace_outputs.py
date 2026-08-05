"""Ecospace output utilities for the FIBE fishery model.

Provides functions to load, cache, and visualise spatial data from
Ecospace CSV exports (topology, wind-farm, and species maps).
"""

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import filedialog


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_ecospace_data_cache: Optional[Tuple[np.ndarray, List[str]]] = None
_cached_habitat_data: Optional[Tuple[np.ndarray, List[str]]] = None

_PROJECT_ROOT = Path(__file__).parent.parent

TOPOLOGY_MAP_PATH: str = str(
    _PROJECT_ROOT / "Ecospace_outputs/topology/EEC_NS_Mmermaid-Depth.csv"
)
WINDFARM_MAP_PATH: str = str(
    _PROJECT_ROOT
    / "Ecospace_outputs/topology/EEC_NS_Mmermaid-Windfarms.csv"
)
SPECIES_MAP_PATHS: Optional[Dict[str, str]] = None
SPECIES_MAP_NAMES: Optional[List[str]] = None
PORTS_MAP_PATH: str = str(
    _PROJECT_ROOT
    / "Ecospace_outputs/ports/PortsMap.csv"
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def configure_sources(
    topology_map_path: Optional[str] = None,
    wind_farm_map_path: Optional[str] = None,
    species_map_paths: Optional[Dict[str, str]] = None,
    ports_map_path: Optional[str] = None,
    habitat_map_path: Optional[Dict[str, str]] = None,
    restricted_area_map_path: Optional[str] = None,
    restricted_area_vector_path: Optional[str] = None,
) -> None:
    """Configures the CSV sources used by the module.

    Updates the relevant module-level path globals and refreshes the
    Ecospace data cache so subsequent calls use the new sources.

    Args:
        topology_map_path: Path to the topology CSV file. If None, the
            current value is kept.
        wind_farm_map_path: Path to the wind-farm CSV file. If None,
            the current value is kept.
        species_map_paths: Mapping of species name to CSV file path.
            If None, the current value is kept.
        ports_map_path: Path to the ports CSV file. If None, the current value is kept.
        habitat_map_path: Path to the habitat CSV file. If None, the current value is kept.
        restricted_area_map_path: Path to the restricted area CSV file. If None, the current value is kept.
        restricted_area_vector_path: Path to the restricted area vector CSV file. If None, the current value is kept.
    """
    global TOPOLOGY_MAP_PATH, WINDFARM_MAP_PATH, SPECIES_MAP_PATHS, PORTS_MAP_PATH, HABITAT_MAP_PATH, RESTRICTED_AREA_MAP_PATH, RESTRICTED_AREA_VECTOR_PATH
    global _ecospace_data_cache
    global _cached_habitat_data

    if topology_map_path is not None:
        TOPOLOGY_MAP_PATH = str(topology_map_path)
    if wind_farm_map_path is not None:
        WINDFARM_MAP_PATH = str(wind_farm_map_path)
    if species_map_paths is not None:
        SPECIES_MAP_PATHS = species_map_paths
    if ports_map_path is not None:
        PORTS_MAP_PATH = str(ports_map_path)
    if habitat_map_path is not None:
        HABITAT_MAP_PATH = habitat_map_path
    if restricted_area_map_path is not None:
        RESTRICTED_AREA_MAP_PATH = str(restricted_area_map_path)
    if restricted_area_vector_path is not None:
        RESTRICTED_AREA_VECTOR_PATH = str(restricted_area_vector_path)

    _ecospace_data_cache = get_ecospace_data()
    _cached_habitat_data = None


# ---------------------------------------------------------------------------
# File selection
# ---------------------------------------------------------------------------

def choose_csv_file() -> List[str]:
    """Opens a dialog for the user to select one or more CSV files.

    Returns:
        List of absolute paths to the selected files, or an empty list
        if the user cancels the dialog.
    """
    root = tk.Tk()
    root.withdraw()

    file_paths = filedialog.askopenfilenames(
        title="Sélectionnez un ou plusieurs fichiers CSV",
        filetypes=[
            ("Fichiers CSV", "*.csv"),
            ("Tous les fichiers", "*.*"),
        ],
    )

    return (
        [os.path.abspath(p) for p in file_paths] if file_paths else []
    )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def safe_float(value: str) -> float | str:
    """Converts a string to float, returning the original value on failure.

    Args:
        value: The string to convert.

    Returns:
        A ``float`` if conversion succeeds, otherwise the original
        string unchanged.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def get_ecospace_data() -> Optional[Tuple[np.ndarray, List[str]]]:
    """Returns the Ecospace data, loading it once and caching it.

    On the first call the data is loaded from ``SPECIES_MAP_PATHS``
    via ``pop_evol_over_time`` and stored in ``_ecospace_data_cache``.
    Subsequent calls return the cached result.

    Returns:
        A tuple of ``(global_map, species_names)`` where ``global_map``
        is a 3-D NumPy array of shape ``(rows, cols, num_species)``
        and ``species_names`` is the ordered list of species identifiers.
        Returns None if no species files are available.
    """
    global _ecospace_data_cache
    if _ecospace_data_cache is None:
        _ecospace_data_cache = pop_evol_over_time()
    return _ecospace_data_cache


def _detect_skip_header(file_path: str) -> int:
    """Detects the number of header lines in an Ecospace CSV grid file.

    Standard Ecospace exports start directly with the header row. Some
    exports prepend a bare index row (e.g. ``0`` or ``1``) before the
    header; in that case two lines must be skipped.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        first_line = f.readline()
    if first_line and "," not in first_line:
        return 2
    return 1


def _read_ecospace_grid(file_path: str) -> np.ndarray:
    """Reads an Ecospace grid CSV, dropping the index column."""
    skip = _detect_skip_header(file_path)
    return np.genfromtxt(
        file_path, delimiter=",", skip_header=skip
    )[:, 1:]


def pop_evol_over_time() -> Optional[Tuple[np.ndarray, List[str]]]:
    """Loads per-species population maps from CSV files.

    Species files are taken from ``SPECIES_MAP_PATHS`` if configured,
    otherwise the user is prompted via a file-chooser dialog.

    Each CSV is expected to have a header row and a leading index
    column, both of which are skipped. The remaining values represent
    fish concentration (g/L) on a spatial grid.

    Returns:
        A tuple ``(global_map, species_names)`` where:

        - ``global_map`` is a NumPy array of shape
          ``(rows, cols, num_species)`` stacking all species grids.
        - ``species_names`` is a list of species identifier strings in
          the same order as the third axis of ``global_map``.

        Returns None if no files are available or selected.
    """
    # Détermination de la source des fichiers
    if SPECIES_MAP_PATHS is not None:
        # Cas configuré : c'est un dictionnaire {nom: chemin}
        file_paths = SPECIES_MAP_PATHS
        use_dict = True
    else:
        # Cas manuel : c'est une liste [chemin1, chemin2, ...]
        file_paths = choose_csv_file()
        use_dict = False

    if not file_paths:
        return None

    species_names: List[str] = []
    species_data: List[np.ndarray] = []

    if use_dict:
        # Itération sur un dictionnaire
        for species_name, file_path in file_paths.items():
            species_names.append(species_name)
            grid = _read_ecospace_grid(file_path)
            species_data.append(grid*1000)
    else:
        # Itération sur une liste
        for file_path in file_paths:
            # On utilise le nom du fichier (sans extension) comme nom d'espèce
            species_name = Path(file_path).stem
            species_names.append(species_name)
            grid = _read_ecospace_grid(file_path)
            species_data.append(grid*1000)

    if not species_data:
        return None
        
    global_map = np.stack(species_data, axis=2)
    return global_map, species_names

def load_habitat_map(habitat_map_path: Optional[Dict[str, str]] = None) -> Tuple[np.ndarray, List[str]]:
    """Loads habitat maps from CSV files.

    Each CSV is expected to have a header row and a leading index
    column, both of which are skipped. The remaining values represent
    habitat suitability on a spatial grid.

    Returns:
        A tuple containing a NumPy array of shape ``(rows, cols, num_habitats)`` stacking all habitat grids and a list of habitat names.
    """

    global HABITAT_MAP_PATH, _cached_habitat_data
    if habitat_map_path is None:
        if HABITAT_MAP_PATH is None:
            raise ValueError("No habitat map path provided and no default configured.")
        habitat_map_path = HABITAT_MAP_PATH

    if _cached_habitat_data is not None:
        return _cached_habitat_data
 
    habitat_names: List[str] = []
    habitat_data: List[np.ndarray] = []

    for habitat_name, file_path in habitat_map_path.items():
        habitat_names.append(habitat_name)
        grid = np.genfromtxt(
            file_path, delimiter=",", skip_header=1
        )[:, 1:]
        habitat_data.append(grid)

    if not habitat_data:
        return np.array([]), []

    habitat_array = np.stack(habitat_data, axis=-1), habitat_names
    print(f"habitat 0 name: {habitat_array[1][0]}")
    _cached_habitat_data = habitat_array
    return _cached_habitat_data

def load_restricted_area_map(restricted_area_map_path: Optional[str] = None) -> np.ndarray:
    """Loads the restricted area map from a CSV file.

    Args:
        restricted_area_map_path: The path to the restricted area map CSV file.
    Returns:
        np.ndarray: A 2D boolean numpy array where True indicates a restricted area.
    """
    if restricted_area_map_path is None:
        raise ValueError("No restricted area map path provided.")

    grid = np.genfromtxt(restricted_area_map_path, delimiter=",", skip_header=1)[:, 1:]
    return grid > 0

def load_restricted_area_vector(restricted_area_vector_path: Optional[str] = None) -> np.ndarray:
    """Loads the restricted area vector from a CSV file.

    Args:
        restricted_area_vector_path: The path to the restricted area vector CSV file.
    Returns:
        np.ndarray: A 1D boolean numpy array where 0 indicates a restricted area is closed, 1 indicates open to navigation, and 2 indicates open.
    """
    if restricted_area_vector_path is None:
        raise ValueError("No restricted area vector path provided.")

    vector = np.genfromtxt(restricted_area_vector_path, delimiter=",", skip_header=1)[:, 1:]
    return vector.astype(int).flatten()

# ---------------------------------------------------------------------------
# Mask utilities
# ---------------------------------------------------------------------------

def masks(
    topology: bool = False,
    windfarm: bool = False,
    ports: bool = False,
) -> Dict[str, List]:
    """Reads one or more CSV files and returns them as numeric masks.

    The first header row and the leading index column of each file are
    skipped. Non-empty cells are converted to floats; empty cells are
    discarded.

    Args:
        topology: If True, reads the configured topology CSV.
        windfarm: If True, reads the configured wind-farm CSV.
            Ignored when ``topology`` is True.
            If both are False, a file-chooser dialog is shown.

    Returns:
        A dictionary with two keys:

        - ``"name of the masks"``: list of base filenames.
        - ``"masks"``: list of 2-D lists (one per file) containing
          the numeric cell values.
    """
    mask_list: List[List[List[float]]] = []
    name_list: List[str] = []

    if topology:
        file_paths = [TOPOLOGY_MAP_PATH]
    elif windfarm:
        file_paths = [WINDFARM_MAP_PATH]
    elif ports:
        file_paths = [PORTS_MAP_PATH]
    else:
        file_paths = choose_csv_file()

    for file_path in file_paths:
        name_list.append(os.path.basename(file_path))
        mask_grid: List[List[float]] = []

        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=",")
            next(reader, None)

            for row in reader:
                row_values = [
                    safe_float(cell)
                    for cell in row[1:]
                    if cell
                ]
                mask_grid.append(row_values)

        mask_list.append(mask_grid)

    return {
        "name of the masks": name_list,
        "masks": mask_list,
    }


def plot_masks(
    masks: Optional[List[np.ndarray]] = None,
    title: str = "Masks",
) -> None:
    """Displays one or more spatial masks using matplotlib.

    Args:
        masks: List of 2-D arrays to plot. If None, the topology and
            wind-farm masks are loaded and displayed.
        title: Title applied to each subplot.
    """
    if masks is None:
        raw = masks(topology=True, windfarm=True)
        masks = [np.array(m) for m in raw["masks"]]

    num_masks = len(masks)
    fig, axes = plt.subplots(1, num_masks, figsize=(5 * num_masks, 5))

    if num_masks == 1:
        axes = [axes]

    for ax, mask_array in zip(axes, masks):
        img = ax.imshow(mask_array, cmap="viridis", interpolation="nearest")
        ax.set_title(title)
        plt.colorbar(img, ax=ax)

    plt.tight_layout()
    plt.show()
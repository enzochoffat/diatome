import logging
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
from datetime import datetime

from src.core import config
from src.infrastructure.ecospace import ecospace_outputs

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

STATUS_ENCODING = {
    "fermé": 0,
    "closed": 0,
    "navigable": 1,
    "navigation": 1,
    "ouvert": 2,
    "open": 2,
}

def _rasterize_restricted_areas_from_shapes(
    zone_sources: Dict[str, str],
    spatial_extent: Optional[dict],
    grid_height: int,
    grid_width: int,
) -> np.ndarray:
    """Rasterizes geographic zone shapefiles onto the simulation grid.

    Each zone source is loaded as a vector geometry (EPSG:4326) and
    merged into a single union geometry. The mask is built by testing the
    centre of every grid cell against that geometry.

    Args:
        zone_sources: Mapping of zone name to absolute shapefile path.
        spatial_extent: Geographic reference of the grid with keys
            ``west``/``north`` (top-left corner in degrees) and either
            ``cell_size_deg`` or ``east``/``south``.
        grid_height: Number of grid rows (must match the topology).
        grid_width: Number of grid columns (must match the topology).

    Returns:
        np.ndarray: 2D float array of shape ``(grid_height, grid_width)``
        where 1.0 marks a cell inside a restricted zone, 0.0 otherwise.
    """
    try:
        import geopandas as gpd
        from shapely import contains, points
        from shapely.ops import unary_union
    except ImportError as exc:
        raise ValueError(
            "geopandas et shapely sont requis pour rasteriser les zones .shp."
        ) from exc

    if spatial_extent is None:
        raise ValueError(
            "Une référence spatiale (spatial_extent) est requise pour "
            "rasteriser les zones shapefile."
        )

    west = float(spatial_extent["west"])
    north = float(spatial_extent["north"])
    if "cell_size_deg" in spatial_extent:
        cell_size_deg = float(spatial_extent["cell_size_deg"])
        east = west + grid_width * cell_size_deg
        south = north - grid_height * cell_size_deg
    else:
        east = float(spatial_extent["east"])
        south = float(spatial_extent["south"])
        cell_size_deg = (east - west) / grid_width

    geometries = []
    for zone_name, shp_path in zone_sources.items():
        gdf = gpd.read_file(shp_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        geometries.append(gdf.geometry.unary_union)

    geometry = geometries[0] if len(geometries) == 1 else unary_union(geometries)

    xs = west + (np.arange(grid_width) + 0.5) * cell_size_deg
    ys = north - (np.arange(grid_height) + 0.5) * cell_size_deg
    gx, gy = np.meshgrid(xs, ys)

    in_zone = contains(geometry, points(gx.ravel(), gy.ravel()))
    return in_zone.reshape(grid_height, grid_width).astype(np.float64)

def load_restricted_area_map(
    restricted_area_map_path: Optional[Union[str, Dict[str, str]]],
    spatial_extent: Optional[dict] = None,
) -> np.ndarray:
    """Loads the restricted area map.

    Two input formats are supported:
        - a CSV file path (string), loaded with ``np.genfromtxt``;
        - a mapping of zone names to shapefile paths (dict), in which
          case the zones are rasterised onto the simulation grid.

    Args:
        restricted_area_map_path: Path to the restricted area map CSV
            file, or a mapping of zone name to shapefile path.
        spatial_extent: Geographic reference used when rasterising
            shapefiles (see :func:`__rasterize_restricted_areas_from_shapes`).

    Returns:
        np.ndarray: A 2D boolean numpy array where True indicates a restricted
        area.
    """
    global _restricted_area_map
    if restricted_area_map_path is None:
        raise ValueError("No restricted area map path provided.")

    if isinstance(restricted_area_map_path, dict):
        _restricted_area_map = _rasterize_restricted_areas_from_shapes(
            restricted_area_map_path,
            spatial_extent,
            grid_height=config.GRID_HEIGHT,
            grid_width=config.GRID_WIDTH,
        )
    else:
        _restricted_area_map = np.genfromtxt(restricted_area_map_path, delimiter=",", skip_header=1)
    save_restricted_area_map(
        file_path=(
            _PROJECT_ROOT / "Ecospace_outputs" / "topology"
            / "RestrictedAreasMap.csv"
        ),
        restricted_area_map=_restricted_area_map,
    )
    return _restricted_area_map

def load_restricted_area_vector(restricted_area_vector_path: Optional[str]) -> dict[str, np.ndarray]:
    """Loads the restricted area vector from a CSV file containing one table
    per fleet (flottille).

    The CSV format:
        Flottille_A;Jan;Feb;Mar;...;Dec
        Zone1;ouvert;fermé;navigable;...
        Zone2;fermé;navigable;ouvert;...
        ...
        Flottille_B;Jan;Feb;Mar;...;Dec
        Zone1;...

    Args:
        restricted_area_vector_path: The path to the restricted area vector CSV file.

    Returns:
        dict[str, np.ndarray]: A dictionary mapping each fleet name to a 2D numpy
        array of shape (n_zones, 12) with values 0 (fermé), 1 (navigable), or 2 (ouvert).
    """
    global _restricted_area_vector
    if restricted_area_vector_path is None:
        raise ValueError("No restricted area vector path provided.")

    _restricted_area_vector = {}

    with open(restricted_area_vector_path, 'r', encoding='latin-1') as file:
        lines = [line.strip() for line in file if line.strip()]

    i = 0
    while i < len(lines):
        parts = lines[i].split(';')
        fleet_name = parts[0]
        i += 1

        zone_rows = []
        while i < len(lines):
            next_parts = lines[i].split(';')
            if len(next_parts) < 2 or next_parts[1] in STATUS_ENCODING:
                zone_rows.append([STATUS_ENCODING[val] for val in next_parts[1:]])
                i += 1
            else:
                break

        _restricted_area_vector[fleet_name] = np.array(zone_rows)
    print(_restricted_area_vector)
    return _restricted_area_vector

def restricted_area_status(flottille: str, date: datetime, zone_index: int) -> str:
    """Returns the restricted area status for a given fleet, date and zone.

    Args:
        flottille: The fleet name.
        date: The date for which to check the restricted area status.
        zone_index: The index of the zone.

    Returns:
        str: The status: "Closed", "Navigation", or "Open".
    """
    global _restricted_area_vector
    month_index = date.month - 1
    val = _restricted_area_vector[flottille][zone_index, month_index]
    if val == 1:
        return "Navigation"
    elif val == 2:
        return "Open"
    else:
        return "Closed"
    
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
        logger.debug("Position (%d, %d) is in a restricted area on %s.", x, y, date)
        return True
    return False

def save_restricted_area_map(
    restricted_area_map: np.ndarray,
    file_path: Union[str, Path],
) -> None:
    """Saves the restricted area map to a CSV file.

    Args:
        restricted_area_map: The 2D boolean numpy array representing the
            restricted area map.
        file_path: The path to save the CSV file. Parent directories
            are created if missing.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        for row in restricted_area_map:
            row_str = ';'.join(str(value) for value in row)
            file.write(row_str + '\n')
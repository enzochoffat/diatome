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

_restricted_area_map: Optional[np.ndarray] = None
_restricted_area_vector: Optional[dict[str, np.ndarray]] = {}

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
            ``cell_size_deg`` (square cells) or ``east``/``south``
            (rectangular cells supported).
        grid_height: Number of grid rows (must match the topology).
        grid_width: Number of grid columns (must match the topology).

    Returns:
        np.ndarray: 2D float array of shape ``(grid_height, grid_width)``
        where 1.0 marks a cell inside a restricted zone, 0.0 otherwise.

    Raises:
        ValueError: If geopandas/shapely are unavailable or
            ``spatial_extent`` is missing.
    """
    try:
        import geopandas as gpd
        from shapely import box, contains, points
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
        x_cell_deg = y_cell_deg = cell_size_deg
        east = west + grid_width * cell_size_deg
        south = north - grid_height * cell_size_deg
    else:
        east = float(spatial_extent["east"])
        south = float(spatial_extent["south"])
        x_cell_deg = (east - west) / grid_width
        y_cell_deg = (south - north) / grid_height

    geometries = []
    grid_box = box(west, south, east, north)
    for zone_name, shp_path in zone_sources.items():
        gdf = gpd.read_file(shp_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        geometry = gdf.geometry.union_all
        if not geometry.intersects(grid_box):
            logger.warning(
                "Restricted zone %r (%s) does not intersect the grid "
                "extent (west=%.4f, north=%.4f, east=%.4f, south=%.4f)."
                "zone bounds: %s",
                zone_name, shp_path, west, north, east, south,
                [round(b, 4) for b in geometry.bounds],
            )
        geometries.append(geometry)

    geometry = geometries[0] if len(geometries) == 1 else unary_union(geometries)

    xs = west + (np.arange(grid_width) + 0.5) * cell_size_deg
    ys = north - (np.arange(grid_height) + 0.5) * cell_size_deg
    gx, gy = np.meshgrid(xs, ys)

    in_zone = contains(geometry, points(gx.ravel(), gy.ravel()))
    return in_zone.reshape(grid_height, grid_width).astype(np.float64)

def _grid_dimensions(
        grid_height: Optional[int],
        grid_width: Optional[int],
) -> tuple[int, int]:
    """Resolves grid dimensions from explicit values or model globals.

    Falls back to ``config.GRID_HEIGHT`` / ``config.GRID_WIDTH`` when the
    arguments are None. Raises early if dimensions are unknown or invalid
    instead of silently producing a misaligned mask.

    Args:
        grid_height: Explicit number of grid rows, or None.
        grid_width: Explicit number of grid columns, or None.

    Returns:
        A ``(grid_height, grid_width)`` tuple of positive integers.

    Raises:
        ValueError: If dimensions are missing or not positive, which means
            the spatial configuration has not been loaded yet.
    """
    height = grid_height if grid_height is not None else config.GRID_HEIGHT
    width = grid_width if grid_width is not None else config.GRID_WIDTH
    if height <= 0 or width <= 0:
        raise ValueError(
            f"Invalid grid dimensions {width}x{height}: "
            "reload_spatial_configuration must run before loading the "
            "restricted area map, or pass grid_height/grid_width explicitly."
        )
    return (height, width)

def _load_restricted_area_csv(file_path: str) -> np.ndarray:
    """Loads a restricted area mask from an Ecospace-style CSV grid.

    The header row and leading index column are dropped, and empty cells
    (NaN) are treated as non-restricted.

    Args:
        file_path: Path to the CSV raster.

    Returns:
        np.ndarray: 2D float mask where > 0.5 marks a restricted cell.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        has_index_row = "," not in file.readline()
    grid = np.genfromtxt(
        file_path, delimiter=",", skip_header=2 if has_index_row else 1
    )[:, 1:]
    return np.nan_to_num(grid, nan=0.0)

def load_restricted_area_map(
    restricted_area_map_path: Optional[Union[str, Dict[str, str]]],
    spatial_extent: Optional[dict] = None,
    grid_height: Optional[int] = None,
    grid_width: Optional[int] = None,
) -> np.ndarray:
    """Loads the restricted area map.

    Two input formats are supported:
        - a CSV file path (string), loaded as an Ecospace-style grid;
        - a mapping of zone names to shapefile paths (dict), in which
          case the zones are rasterised onto the simulation grid.

    Args:
        restricted_area_map_path: Path to the restricted area map CSV
            file, or a mapping of zone name to shapefile path.
        spatial_extent: Geographic reference used when rasterising
            shapefiles (see `_rasterize_restricted_areas_from_shapes`).
        grid_height: Explicit number of grid rows. If None, the value is
            taken from `config.GRID_HEIGHT` (requires the spatial
            configuration to be loaded first).
        grid_width: Explicit number of grid columns. Same fallback rule.

    Returns:
        np.ndarray: 2D float mask of shape ``(grid_height, grid_width)``
        where values > 0.5 indicate a restricted area.

    Raises:
        ValueError: If no source is provided, grid dimensions are invalid,
            or the loaded CSV mask does not match the grid dimensions.
    """
    global _restricted_area_map
    if restricted_area_map_path is None:
        raise ValueError("No restricted area map path provided.")

    height, width = _grid_dimensions(grid_height, grid_width)

    if isinstance(restricted_area_map_path, dict):
        _restricted_area_map = _rasterize_restricted_areas_from_shapes(
            restricted_area_map_path,
            spatial_extent,
            grid_height=height,
            grid_width=width,
        )
    else:
        _restricted_area_map = _load_restricted_area_csv(restricted_area_map_path)

    if _restricted_area_map.shape != (height, width):
        raise ValueError(
            f"Restricted area map shape {_restricted_area_map.shape} does not "
            f"match expected grid dimensions {(height, width)}."
        )

    if not np.any(_restricted_area_map > 0.5):
        logger.warning(
            "Restricted area map is empty (no restricted zones found)."
            "Check that the shapefiles overlap the grid spatial extent."
        )

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

    Raises:
        ValueError: If the fleet is unknown to the loaded vector.
    """
    if flottille not in _restricted_area_vector:
        raise ValueError(
            f"No restricted area vector for fleet {flottille} "
            f"Available fleets: {list(_restricted_area_vector.keys())}"
        )
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

    Out-of-bounds positions are treated as restricted; when no map has
    been loaded the position is treated as non-restricted.

    Args:
        x: The x-coordinate of the position.
        y: The y-coordinate of the position.
        date: The date for which to check the restricted area status
            (kept for interface compatibility).

    Returns:
        bool: True if the position is in a restricted area, False otherwise.
    """
    #print(f"Checking restricted area status for position ({x}, {y}) on {date}.")
    if _restricted_area_map is None:
        return False
    height, width = _restricted_area_map.shape
    if not (0 <= y < height and 0 <= x < width):
        return True
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
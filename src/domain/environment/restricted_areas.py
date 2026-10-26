import logging
from pathlib import Path
from typing import Dict, Optional, Union, List, Tuple
from datetime import datetime, date

import numpy as np

from src.core import config

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

STATUS_ENCODING = {
    "fermé": 0,
    "ferme": 0,
    "closed": 0,
    "navigable": 1,
    "navigation": 1,
    "ouvert": 2,
    "open": 2,
}

# Primary storage
_zone_id_map: Optional[np.ndarray] = None  # int[H,W] 0=free, 1..n=zone
_restricted_area_map: Optional[np.ndarray] = None  # legacy alias -> same as _zone_id_map (float/int)
_restricted_area_vector: Optional[dict] = {}  # fleet -> intervals list OR np.ndarray (old)
_zone_name_to_id: Dict[str, int] = {}
_zone_id_to_name: Dict[int, str] = {}
_habitat_masks: Dict[str, np.ndarray] = {}
_nav_mask_cache: Dict[Tuple[str,int,int], np.ndarray] = {}  # (fleet,year,month) -> bool
_fish_mask_cache: Dict[Tuple[str,int,int], np.ndarray] = {}

def _rasterize_restricted_areas_from_shapes(
    zone_sources: Dict[str, str],
    spatial_extent: Optional[dict],
    grid_height: int,
    grid_width: int,
) -> np.ndarray:
    """Rasterizes each zone shapefile with a distinct zone_id (dict order)."""
    try:
        import geopandas as gpd
        from shapely import box, contains, points
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
        y_cell_deg = (north - south) / grid_height
        cell_size_deg = x_cell_deg  # for mesh, assume square for simplicity
        # fallback: use x_cell_deg for both
        y_cell_deg = x_cell_deg

    grid_box = box(west, south, east, north)

    # Prepare zone_id map
    zone_id_map = np.zeros((grid_height, grid_width), dtype=np.int32)
    global _zone_name_to_id, _zone_id_to_name
    _zone_name_to_id = {}
    _zone_id_to_name = {}

    xs = west + (np.arange(grid_width) + 0.5) * x_cell_deg
    ys = north - (np.arange(grid_height) + 0.5) * y_cell_deg
    gx, gy = np.meshgrid(xs, ys)
    points_arr = points(gx.ravel(), gy.ravel())

    for zid, (zone_name, shp_path) in enumerate(zone_sources.items(), start=1):
        _zone_name_to_id[zone_name] = zid
        _zone_id_to_name[zid] = zone_name
        gdf = gpd.read_file(shp_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        geometry = gdf.geometry.union_all()
        if not geometry.intersects(grid_box):
            logger.warning(
                "Restricted zone %r (%s) does not intersect the grid "
                "extent (west=%.4f, north=%.4f, east=%.4f, south=%.4f)."
                "zone bounds: %s",
                zone_name, shp_path, west, north, east, south,
                [round(b, 4) for b in geometry.bounds],
            )
        in_zone = contains(geometry, points_arr)
        in_zone_2d = in_zone.reshape(grid_height, grid_width)
        # Assign zid where in_zone and not already assigned (first wins)
        # If overlap, last wins? We choose first wins to keep deterministic, log warning
        overlap = (zone_id_map != 0) & in_zone_2d
        if np.any(overlap):
            logger.warning("Zone %r (id %d) overlaps previous zones on %d cells (first wins kept)", zone_name, zid, np.sum(overlap))
            in_zone_2d = in_zone_2d & (zone_id_map == 0)
        zone_id_map[in_zone_2d] = zid

    return zone_id_map

def _grid_dimensions(
        grid_height: Optional[int],
        grid_width: Optional[int],
) -> tuple[int, int]:
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
    """Loads zone_id map from Ecospace CSV (ints, 0=free)."""
    with open(file_path, 'r', encoding='utf-8') as file:
        has_index_row = "," not in file.readline()
    grid = np.genfromtxt(
        file_path, delimiter=",", skip_header=2 if has_index_row else 1
    )[:, 1:]
    grid = np.nan_to_num(grid, nan=0.0)
    # Keep ints
    return grid.astype(np.int32)

def _parse_month_year(s: str) -> Tuple[int,int]:
    """Parse MM/YYYY or MM-YYYY or YYYY-MM."""
    s=s.strip()
    for fmt in ("%m/%Y", "%m-%Y", "%Y-%m", "%Y/%m"):
        try:
            dt=datetime.strptime(s, fmt)
            return dt.year, dt.month
        except ValueError:
            continue
    # try with datetime with day
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt=datetime.strptime(s, fmt)
            return dt.year, dt.month
        except ValueError:
            continue
    raise ValueError(f"Unparseable month/year: {s!r}")

def load_restricted_area_map(
    restricted_area_map_path: Optional[Union[str, Dict[str, str]]],
    spatial_extent: Optional[dict] = None,
    grid_height: Optional[int] = None,
    grid_width: Optional[int] = None,
) -> np.ndarray:
    global _zone_id_map, _restricted_area_map, _zone_name_to_id, _zone_id_to_name
    if restricted_area_map_path is None:
        raise ValueError("No restricted area map path provided.")

    height, width = _grid_dimensions(grid_height, grid_width)

    if isinstance(restricted_area_map_path, dict):
        _zone_id_map = _rasterize_restricted_areas_from_shapes(
            restricted_area_map_path,
            spatial_extent,
            grid_height=height,
            grid_width=width,
        )
    else:
        _zone_id_map = _load_restricted_area_csv(restricted_area_map_path)
        # Build name mapping for CSV: assume zone ids are ints, map zone_{id} -> id
        uniq = np.unique(_zone_id_map)
        uniq = uniq[uniq!=0]
        _zone_name_to_id = {f"zone_{int(v)}": int(v) for v in uniq}
        _zone_id_to_name = {int(v): f"zone_{int(v)}" for v in uniq}
        # also numeric string mapping for old vector table (1,2...)
        for v in uniq:
            _zone_name_to_id[str(int(v))] = int(v)

    if _zone_id_map.shape != (height, width):
        raise ValueError(
            f"Restricted area map shape {_zone_id_map.shape} does not "
            f"match expected grid dimensions {(height, width)}."
        )

    if not np.any(_zone_id_map != 0):
        logger.warning(
            "Restricted area map is empty (no restricted zones found)."
            "Check that the shapefiles overlap the grid spatial extent."
        )

    # legacy alias
    _restricted_area_map = _zone_id_map.astype(np.float64)

    # clear caches
    clear_cache()

    save_restricted_area_map(
        file_path=(
            _PROJECT_ROOT / "Ecospace_outputs" / "topology"
            / "RestrictedAreasMap.csv"
        ),
        restricted_area_map=_zone_id_map,
    )
    return _zone_id_map

def load_restricted_area_vector(restricted_area_vector_path: Optional[str]) -> dict:
    global _restricted_area_vector
    if restricted_area_vector_path is None:
        raise ValueError("No restricted area vector path provided.")

    _restricted_area_vector = {}
    clear_cache()

    # Detect format by header
    with open(restricted_area_vector_path, 'r', encoding='latin-1') as file:
        lines = [line.strip() for line in file if line.strip()]
    if not lines:
        return _restricted_area_vector

    header = lines[0].lower()
    # New format: flottille;zone;debut;fin;statut
    if "debut" in header and "fin" in header and "statut" in header:
        # new range format
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(';')]
            if len(parts) <5:
                continue
            flottille, zone, debut_s, fin_s, statut_s = parts[:5]
            flottille = flottille.strip().lower()
            zone = zone.strip()
            statut_key = statut_s.strip().lower()
            statut = STATUS_ENCODING.get(statut_key)
            if statut is None:
                logger.warning(f"Unknown statut {statut_s!r} for {flottille}/{zone}, skipping")
                continue
            try:
                y1,m1 = _parse_month_year(debut_s)
                y2,m2 = _parse_month_year(fin_s)
            except ValueError as e:
                logger.warning(f"Invalid date {debut_s}/{fin_s}: {e}")
                continue
            if flottille not in _restricted_area_vector:
                _restricted_area_vector[flottille] = []
            _restricted_area_vector[flottille].append({
                "zone": zone,
                "debut_year": y1,
                "debut_month": m1,
                "fin_year": y2,
                "fin_month": m2,
                "statut": statut,
                "statut_str": statut_s,
            })
        # Sort for deterministic
        for fleet in _restricted_area_vector:
            _restricted_area_vector[fleet].sort(key=lambda x: (x["zone"], x["debut_year"], x["debut_month"]))
        logger.info(f"Loaded restricted vector (range format): { {k: len(v) for k,v in _restricted_area_vector.items()} }")
        return _restricted_area_vector
    else:
        # Old table format: flotille;Jan;Feb;... or flottille;zone;... table per fleet
        # Fallback to previous parser but more robust
        i = 0
        while i < len(lines):
            parts = [p.strip() for p in lines[i].split(';')]
            fleet_name = parts[0].lower()
            # Header line contains month names? check if second col not in STATUS_ENCODING
            # Actually first line of fleet is header, next lines are zones
            i += 1
            zone_rows = []
            while i < len(lines):
                next_parts = [p.strip() for p in lines[i].split(';')]
                if len(next_parts) <2:
                    i+=1
                    continue
                # Detect new fleet header: first col is fleet name and second col is month name not status
                # Heuristic: if len(next_parts)>=2 and next_parts[1].lower() not in STATUS_ENCODING and not next_parts[1].isdigit():
                # But old fleet header has Jan etc.
                # Simpler: if next_parts[1].lower() in STATUS_ENCODING or next_parts[1].lower() in ["fermé","ferme","closed","navigable","navigation","ouvert","open"]:
                # then it's a zone row
                val_lower = next_parts[1].lower()
                is_zone_row = val_lower in STATUS_ENCODING
                # Also zone rows start with zone id like "1" or "zone_1" and second col is status
                # Fleet header second col would be "January" or "Janvier" not in STATUS_ENCODING? Actually old header is like "archipelago;January;February..." -> second col "January" not in STATUS_ENCODING, so is_zone_row False
                # But fleet name row second col would be month name not status, so False -> break to outer loop
                if is_zone_row:
                    # Handle both numeric zone and status columns
                    # Old code: [STATUS_ENCODING[val] for val in next_parts[1:]]
                    try:
                        encoded = [STATUS_ENCODING[v.lower()] for v in next_parts[1:]]
                    except KeyError as e:
                        logger.warning(f"Unknown status {e} in line {lines[i]!r}")
                        i+=1
                        continue
                    zone_rows.append(encoded)
                    i += 1
                else:
                    # Could be fleet header for next fleet: check if line looks like fleet;Month;... (second col is month name)
                    # If we are here and next_parts[0] lower not numeric and not in STATUS_ENCODING, treat as new fleet
                    break
            if zone_rows:
                _restricted_area_vector[fleet_name] = np.array(zone_rows, dtype=np.int32)
        logger.info(f"Loaded restricted vector (table format): { {k: v.shape if isinstance(v,np.ndarray) else len(v) for k,v in _restricted_area_vector.items()} }")
        return _restricted_area_vector

def restricted_area_status(flottille: str, date_obj: datetime, zone_index: int) -> str:
    if flottille.lower() not in _restricted_area_vector:
        raise ValueError(
            f"No restricted area vector for fleet {flottille} "
            f"Available fleets: {list(_restricted_area_vector.keys())}"
        )
    # Handle both storage types
    entry = _restricted_area_vector[flottille.lower()]
    if isinstance(entry, np.ndarray):
        month_index = date_obj.month - 1
        # zone_index 0-based
        if zone_index <0 or zone_index >= entry.shape[0]:
            return "Open"
        val = entry[zone_index, month_index]
    else:
        # interval list
        # Need zone name from id
        zone_name = _zone_id_to_name.get(zone_index+1, f"zone_{zone_index+1}")
        val = 2 # default open
        for rec in entry:
            if rec["zone"] == zone_name or rec["zone"] == str(zone_index+1):
                y=date_obj.year; m=date_obj.month
                if (rec["debut_year"], rec["debut_month"]) <= (y,m) <= (rec["fin_year"], rec["fin_month"]):
                    val = rec["statut"]
                    break
    if val == 1:
        return "Navigation"
    elif val == 2:
        return "Open"
    else:
        return "Closed"

def _get_vector_status(fleet: str, zone_name: str, zone_id: int, date_obj) -> int:
    """Returns 0/1/2 for fleet/zone/date, default 2 (open) if no rule."""
    if not fleet:
        return 2
    fleet_key = fleet.lower()
    if fleet_key not in _restricted_area_vector:
        return 2
    entry = _restricted_area_vector[fleet_key]
    if isinstance(entry, np.ndarray):
        # old table: need mapping zone_id -> row index (zid-1)
        # If zid 0 => not in zone
        if zone_id == 0:
            return 2
        row = zone_id -1
        if row <0 or row >= entry.shape[0]:
            return 2
        # handle date as month index (year ignored for old format)
        try:
            month_idx = date_obj.month -1
            return int(entry[row, month_idx])
        except Exception:
            return 2
    else:
        # new interval list
        # Find matching rec for zone
        # zone_name from _zone_id_to_name or zone_{id}
        zid_name = _zone_id_to_name.get(zone_id, f"zone_{zone_id}")
        # Try both zid_name and zone_name param
        candidates = [zid_name, zone_name, f"zone_{zone_id}", str(zone_id)]
        for rec in entry:
            if rec["zone"] in candidates:
                y = date_obj.year if hasattr(date_obj, 'year') else date_obj["year"]
                m = date_obj.month if hasattr(date_obj, 'month') else date_obj["month"]
                if (rec["debut_year"], rec["debut_month"]) <= (y,m) <= (rec["fin_year"], rec["fin_month"]):
                    return rec["statut"]
        return 2

def get_zone_id(x: int, y: int) -> int:
    if _zone_id_map is None:
        return 0
    h,w = _zone_id_map.shape
    if not (0 <= y < h and 0 <= x < w):
        return -1 # out of bounds treated as restricted
    return int(_zone_id_map[y, x])

def can_navigate(fleet: str, x: int, y: int, date_obj) -> bool:
    """Transit allowed if not in closed zone (statut 0)."""
    if _zone_id_map is None:
        return True
    h,w = _zone_id_map.shape
    if not (0 <= y < h and 0 <= x < w):
        return False
    zid = int(_zone_id_map[y, x])
    if zid == 0:
        return True
    # lookup vector
    # date_obj may be datetime/date
    status = _get_vector_status(fleet, _zone_id_to_name.get(zid, f"zone_{zid}"), zid, date_obj)
    return status != 0  # 1 or 2 allowed

def can_fish(fleet: str, x: int, y: int, date_obj) -> bool:
    """Fishing allowed if not habitat-forbidden and zone open (statut 2)."""
    # habitat check
    if fleet and fleet.lower() in _habitat_masks:
        mask = _habitat_masks[fleet.lower()]
        h,w = mask.shape
        if 0 <= y < h and 0 <= x < w:
            if mask[y, x]:
                return False
    # zone check
    if _zone_id_map is None:
        return True
    h,w = _zone_id_map.shape
    if not (0 <= y < h and 0 <= x < w):
        return False
    zid = int(_zone_id_map[y, x])
    if zid == 0:
        return True
    status = _get_vector_status(fleet, _zone_id_to_name.get(zid, f"zone_{zid}"), zid, date_obj)
    return status == 2

def get_navigation_mask(fleet: str, date_obj) -> np.ndarray:
    """Returns bool mask where True = can navigate."""
    if _zone_id_map is None:
        # fallback to all True
        h,w = _grid_dimensions(None, None)
        return np.ones((h,w), dtype=bool)
    key = (fleet.lower() if fleet else "", getattr(date_obj,'year',0), getattr(date_obj,'month',0))
    if key in _nav_mask_cache:
        return _nav_mask_cache[key]
    h,w = _zone_id_map.shape
    mask = np.ones((h,w), dtype=bool)
    # vectorize: for each unique zid, fill
    # simple loop over zones
    unique_zids = np.unique(_zone_id_map)
    unique_zids = unique_zids[unique_zids!=0]
    for zid in unique_zids:
        status = _get_vector_status(fleet, _zone_id_to_name.get(int(zid), f"zone_{int(zid)}"), int(zid), date_obj)
        can_nav = status != 0
        if not can_nav:
            mask[_zone_id_map == zid] = False
    _nav_mask_cache[key] = mask
    return mask

def get_fishing_mask(fleet: str, date_obj) -> np.ndarray:
    """Returns bool mask where True = can fish."""
    if _zone_id_map is None and not _habitat_masks:
        h,w = _grid_dimensions(None, None)
        return np.ones((h,w), dtype=bool)
    # determine shape
    if _zone_id_map is not None:
        h,w = _zone_id_map.shape
    elif _habitat_masks:
        # pick first habitat mask shape
        h,w = next(iter(_habitat_masks.values())).shape
    else:
        h,w = _grid_dimensions(None, None)
        return np.ones((h,w), dtype=bool)
    key = (fleet.lower() if fleet else "", getattr(date_obj,'year',0), getattr(date_obj,'month',0))
    if key in _fish_mask_cache:
        return _fish_mask_cache[key]
    # start with all True
    mask = np.ones((h,w), dtype=bool)
    # habitat forbids fishing (transit still allowed but this mask is fishing)
    if fleet and fleet.lower() in _habitat_masks:
        hab = _habitat_masks[fleet.lower()]
        # hab True = forbidden
        mask = mask & (~hab)
    if _zone_id_map is not None:
        unique_zids = np.unique(_zone_id_map)
        unique_zids = unique_zids[unique_zids!=0]
        for zid in unique_zids:
            status = _get_vector_status(fleet, _zone_id_to_name.get(int(zid), f"zone_{int(zid)}"), int(zid), date_obj)
            can_f = status == 2
            if not can_f:
                mask[_zone_id_map == zid] = False
    _fish_mask_cache[key] = mask
    return mask

def set_habitat_mask(fleet: str, mask: np.ndarray):
    global _habitat_masks
    if mask is None:
        return
    _habitat_masks[fleet.lower()] = mask.astype(bool) if isinstance(mask, np.ndarray) else mask
    clear_cache()

def clear_cache():
    _nav_mask_cache.clear()
    _fish_mask_cache.clear()

def is_restricted_area(x: int, y: int, date_obj) -> bool:
    """Legacy: True if in any restricted zone (ignores fleet/vector, for compat)."""
    # deprecated, use can_navigate
    import warnings
    warnings.warn("is_restricted_area is deprecated, use can_navigate/can_fish", DeprecationWarning, stacklevel=2)
    if _zone_id_map is None:
        return False
    h,w = _zone_id_map.shape
    if not (0 <= y < h and 0 <= x < w):
        return True
    return int(_zone_id_map[y, x]) != 0

def save_restricted_area_map(
    restricted_area_map: np.ndarray,
    file_path: Union[str, Path],
) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        for row in restricted_area_map:
            row_str = ';'.join(str(int(value)) for value in row)
            file.write(row_str + '\n')

# Keep legacy alias for external imports
# _restricted_area_map already set in load

from typing import List, Tuple, Optional, Dict
import numpy as np

from src.core import config
from src.infrastructure.ecospace import ecospace_outputs
from src.infrastructure.ecospace.ecospace_outputs import masks


def compute_land_coordinates(
    topo_matrix: List[List[float]],
) -> List[List[int]]:
    """Computes coordinates of all land cells in the topology matrix.

    A cell is considered land if its value is 0 or below the floating-point
    threshold 1e-29.

    Args:
        topo_matrix: 2-D grid of depth/topology values.

    Returns:
        List of [x, y] coordinate pairs for all land cells.
    """
    return [
        [x, y]
        for y in range(len(topo_matrix))
        for x in range(len(topo_matrix[y]))
        if topo_matrix[y][x] == 0 or topo_matrix[y][x] < 1e-29
    ]

def get_neighbors_by_euclidean_distance(
    matrix: List[List[int]],
    center_value: int,
    radius: int = 7,
) -> Tuple[List[Tuple[int, int]], List[int]]:
    """Finds all cells within a given Euclidean distance of a centre value.

    Identifies all grid cells whose value matches ``center_value``, then
    returns every other positive-valued cell within ``radius`` of at least
    one such centre.

    Args:
        matrix: 2-D integer grid.
        center_value: Grid value used to locate centre cells.
        radius: Maximum Euclidean distance from any centre cell.

    Returns:
        A tuple of (indices, values) where indices is a list of (row, col)
        pairs and values contains the corresponding grid values.
    """
    arr = np.array(matrix)
    centers = np.argwhere(arr == center_value)
    print(
        f"    [get_neighbors] Looking for center_value={center_value},"
        f" found {len(centers)} centers"
    )

    if centers.size == 0:
        unique_vals = sorted(
            {v for row in matrix for v in row if v > 0}
        )[:10]
        print(
            f"    [get_neighbors] WARNING: No centers found!"
            f" Unique values: {unique_vals}..."
        )
        return [], []

    rows, cols = arr.shape
    rr, cc = np.meshgrid(
        np.arange(rows), np.arange(cols), indexing="ij"
    )

    dists = np.sqrt(
        (rr[..., None] - centers[:, 0]) ** 2
        + (cc[..., None] - centers[:, 1]) ** 2
    )
    min_dist = np.min(dists, axis=2)
    mask = (min_dist <= radius) & (arr != center_value) & (arr > 0)

    indices = np.argwhere(mask)
    values = arr[mask]
    return indices.tolist(), values.tolist()


def get_neighbors_by_euclidean_distance_as_xy(
    matrix: List[List[int]],
    center_value: int,
    radius: int = 7,
) -> Tuple[List[List[int]], List[int]]:
    """Wraps ``get_neighbors_by_euclidean_distance`` returning (x, y) pairs.

    Args:
        matrix: 2-D integer grid.
        center_value: Grid value used to locate centre cells.
        radius: Maximum Euclidean distance from any centre cell.

    Returns:
        A tuple of (xy_indices, values) where xy_indices is a list of
        [col, row] pairs (i.e. [x, y]) and values contains the
        corresponding grid values.
    """
    indices, values = get_neighbors_by_euclidean_distance(
        matrix, center_value, radius
    )
    xy_indices = [[col, row] for row, col in indices]
    return xy_indices, values

def define_region(
    region_name: str,
    topology_matrix: Optional[List[List[int]]] = None,
) -> List[List[int]]:
    """Defines the set of grid cells belonging to a named fishing region.

    Region boundaries are derived from depth percentiles of the global
    topology. The four regions correspond to increasing depth bands:
    A (shallow) → D (deep).

    Args:
        region_name: One of ``"A"``, ``"B"``, ``"C"``, or ``"D"``.
        topology_matrix: Topology grid to use. Defaults to ``TOPOLOGY``.

    Returns:
        List of [x, y] cell coordinates that fall within the region.
    """
    if topology_matrix is None:
        topology_matrix, min_depth, max_depth = reload_spatial_configuration()
    else:
        topology_array = np.array(topology_matrix)
        positive_cells = topology_array[topology_array > 0]
        if positive_cells.size > 0:
            min_depth = int(np.min(positive_cells))
            max_depth = int(np.max(positive_cells))
        else:
            min_depth = 0
            max_depth = 0

    depth_range = max_depth - min_depth

    region_params: Dict[str, Tuple[float, float]] = {
        "A": (float(min_depth), depth_range / 3),
        "B": (depth_range / 3, depth_range / 6),
        "C": (6 * depth_range / 8 + min_depth, depth_range / 6),
        "D": (float(max_depth - 5), depth_range / 6),
    }

    center_value_f, radius = region_params[region_name]
    center_value = int(round(center_value_f))

    print(f"\n[DEBUG] Region {region_name}:")
    print(
        f"  center_value = {center_value}"
        f" (type: {type(center_value).__name__})"
    )
    print(f"  min_depth = {min_depth}, max_depth = {max_depth}")

    result_indices, result_values = get_neighbors_by_euclidean_distance_as_xy(
        topology_matrix, center_value, radius=radius
    )

    print(f"  Found {len(result_indices)} cells in the region")
    if result_indices:
        print(
            f"  Values in region:"
            f" min={min(result_values)}, max={max(result_values)}"
        )

    return result_indices


def reload_spatial_configuration(
    topology_map_path: Optional[str] = None,
    windfarm_map_path: Optional[str] = None,
    apply_windfarm: bool = False,
) -> List[List[int]]:
    """Loads and rebuilds all spatial globals from source files.

    Optionally merges a wind-farm mask into the base topology before
    deriving region definitions and depth statistics.

    Args:
        topology_map_path: Optional path to a custom topology raster.
        windfarm_map_path: Optional path to a wind-farm raster.
        apply_windfarm: If True, subtracts the wind-farm footprint from
            the topology, marking those cells as land.

    Returns:
        The updated TOPOLOGY grid as a 2-D list.
    """
    global TOPOLOGY, ORIGINAL_TOPOLOGY, LAND, WATER, GRID_HEIGHT, GRID_WIDTH
    global single_slice, y_min_water, all_water_depths
    global max_depth, min_depth, percentile_90_depth
    global REGION_A, REGION_B, REGION_C, REGION_D

    if topology_map_path is not None or windfarm_map_path is not None:
        ecospace_outputs.configure_sources(
            topology_map_path=topology_map_path,
            wind_farm_map_path=windfarm_map_path,
        )

    base_topology = np.array(
        masks(topology=True, windfarm=False, ports=False)["masks"][0]
    )
    original_topology = base_topology.copy()

    if apply_windfarm:
        wf = np.array(masks(topology=False, windfarm=True, ports=False)["masks"][0])
        h, w = base_topology.shape
        wf_resized = np.zeros_like(base_topology)
        h_wf, w_wf = wf.shape
        wf_resized[: min(h, h_wf), : min(w, w_wf)] = wf[:h, :w]
        base_topology = np.where(wf_resized == 1, 0, base_topology)

    TOPOLOGY = base_topology.tolist()
    ORIGINAL_TOPOLOGY = original_topology.tolist()

    GRID_HEIGHT, GRID_WIDTH = base_topology.shape
    single_slice = GRID_HEIGHT // 4

    positive_mask = base_topology > 0
    WATER = [
        row[row >= 0].tolist()
        for row in base_topology
        if np.any(row >= 0)
    ]
    all_water_depths = base_topology[positive_mask]
    y_min_water = int(np.min(WATER[-1])) if WATER else 0

    if all_water_depths.size > 0:
        max_depth = int(np.max(all_water_depths))
        min_depth = int(np.min(all_water_depths))
        percentile_90_depth = float(np.percentile(all_water_depths, 90))
    else:
        max_depth = min_depth = 0
        percentile_90_depth = 0.0

    LAND = compute_land_coordinates(TOPOLOGY)

    REGION_A = define_region("A", ORIGINAL_TOPOLOGY)
    REGION_B = define_region("B", ORIGINAL_TOPOLOGY)
    REGION_C = define_region("C", ORIGINAL_TOPOLOGY)
    REGION_D = define_region("D", ORIGINAL_TOPOLOGY)

    set_a = {tuple(cell) for cell in REGION_A}
    set_b = {tuple(cell) for cell in REGION_B}
    set_c = {tuple(cell) for cell in REGION_C}
    set_d = {tuple(cell) for cell in REGION_D}

    set_c -= set_d
    set_b -= set_c | set_d
    set_a -= set_b | set_c | set_d

    REGION_A = list(set_a)
    REGION_B = list(set_b)
    REGION_C = list(set_c)
    REGION_D = list(set_d)

    config.TOPOLOGY = TOPOLOGY
    config.ORIGINAL_TOPOLOGY = ORIGINAL_TOPOLOGY
    config.LAND = LAND
    config.WATER = WATER
    config.GRID_HEIGHT = GRID_HEIGHT
    config.GRID_WIDTH = GRID_WIDTH
    config.single_slice = single_slice
    config.y_min_water = y_min_water
    config.all_water_depths = all_water_depths
    config.max_depth = max_depth
    config.min_depth = min_depth
    config.percentile_90_depth = percentile_90_depth
    config.REGION_A = REGION_A
    config.REGION_B = REGION_B
    config.REGION_C = REGION_C
    config.REGION_D = REGION_D

    print("[DEBUG] After removing overlaps:")
    print(f"  REGION_A: {len(REGION_A)} cells")
    print(f"  REGION_B: {len(REGION_B)} cells")
    print(f"  REGION_C: {len(REGION_C)} cells")
    print(f"  REGION_D: {len(REGION_D)} cells")
    print(
        f"[DEBUG] Loaded topology:"
        f" GRID_WIDTH={GRID_WIDTH}, GRID_HEIGHT={GRID_HEIGHT}"
    )
    print("[DEBUG] Depth calculation:")
    print(f"  min_depth = {min_depth}, max_depth = {max_depth}")
    print(f"  percentile_90_depth = {percentile_90_depth}")
    print(f"  Total water cells: {all_water_depths.size}")

    return TOPOLOGY, min_depth, max_depth

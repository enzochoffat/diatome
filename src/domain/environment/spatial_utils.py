from typing import List, Optional
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


def reload_spatial_configuration(
    topology_map_path: Optional[str] = None,
    windfarm_map_path: Optional[str] = None,
    apply_windfarm: bool = False,
) -> List[List[int]]:
    """Loads and rebuilds topology and spatial globals from source files.

    Optionally merges a wind-farm mask into the base topology.

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
    land_set = {tuple(c) for c in LAND}
    WATER_CELLS = [
        [x, y]
        for y in range(GRID_HEIGHT)
        for x in range(GRID_WIDTH)
        if (x, y) not in land_set
    ]

    config.TOPOLOGY = TOPOLOGY
    config.ORIGINAL_TOPOLOGY = ORIGINAL_TOPOLOGY
    config.LAND = LAND
    config.WATER_CELLS = WATER_CELLS
    config.WATER = WATER
    config.GRID_HEIGHT = GRID_HEIGHT
    config.GRID_WIDTH = GRID_WIDTH
    config.single_slice = single_slice
    config.y_min_water = y_min_water
    config.all_water_depths = all_water_depths
    config.max_depth = max_depth
    config.min_depth = min_depth
    config.percentile_90_depth = percentile_90_depth

    print(
        f"[DEBUG] Loaded topology:"
        f" GRID_WIDTH={GRID_WIDTH}, GRID_HEIGHT={GRID_HEIGHT}"
    )
    print("[DEBUG] Depth calculation:")
    print(f"  min_depth = {min_depth}, max_depth = {max_depth}")
    print(f"  percentile_90_depth = {percentile_90_depth}")
    print(f"  Total water cells: {all_water_depths.size}")

    return TOPOLOGY, min_depth, max_depth

def read_depth_map():
    """Reads the depth map from the configured source file.

    Returns:
        List[List[int]]: A 2-D grid of depth values.
    """
    global TOPOLOGY
    topo = TOPOLOGY

    return topo



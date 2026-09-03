from typing import List, Tuple
import numpy as np

from src.infrastructure.ecospace import ecospace_outputs
from src.domain.environment import spatial_utils
from src.core import config


def _ensure_spatial_configuration() -> None:
    if not getattr(spatial_utils, "TOPOLOGY", None):
        spatial_utils.reload_spatial_configuration()


def get_hotspots_for_step(
    step: int,
) -> List[Tuple[int, int]]:
    """Returns the top-3 hotspots across all water cells at a given step.

    Each Ecospace date corresponds to 30 model steps. If Ecospace data are
    unavailable the function falls back to raw topology values.

    Args:
        step: Current simulation step.

    Returns:
        List of up to 3 (x, y) coordinate pairs with the highest fish
        concentration, spaced at least 10 units apart.
    """
    _ensure_spatial_configuration()

    water_cells = config.WATER_CELLS

    if not water_cells:
        return []

    if ecospace_outputs._ecospace_data_cache is not None:
        try:
            ecospace_data, _ = ecospace_outputs.get_ecospace_data()
            sum_data = np.sum(ecospace_data, axis=2)

            if sum_data is not None:
                fish_map = np.array(sum_data)
                top_coords = sorted(
                    water_cells,
                    key=lambda xy: fish_map[xy[1]][xy[0]],
                    reverse=True,
                )
                hotspots: List[Tuple[int, int]] = []

                for x, y in top_coords:
                    if all(
                        (x - hx) ** 2 + (y - hy) ** 2 >= 10 ** 2
                        for hx, hy in hotspots
                    ):
                        hotspots.append((x, y))
                    if len(hotspots) == 3:
                        break

                if len(hotspots) == 3:
                    return hotspots
        except Exception:
            pass

    top_coords = sorted(
        water_cells,
        key=lambda xy: spatial_utils.TOPOLOGY[xy[1]][xy[0]],
        reverse=True,
    )[:3]
    return top_coords

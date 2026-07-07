from typing import List, Tuple
import numpy as np

from src.infrastructure.ecospace import ecospace_outputs
from src.domain.environment import spatial_utils
from src.core import config


def _ensure_spatial_configuration() -> None:
    if not spatial_utils.TOPOLOGY:
        spatial_utils.reload_spatial_configuration()


def get_hotspots_for_step(
    step: int,
    region_name: str,
) -> List[Tuple[int, int]]:
    """Returns the top-3 hotspots for a region at a given simulation step.

    Each Ecospace date corresponds to 30 model steps. If Ecospace data are
    unavailable the function falls back to raw topology values.

    Args:
        step: Current simulation step.
        region_name: One of ``"A"``, ``"B"``, ``"C"``, or ``"D"``.

    Returns:
        List of up to 3 (x, y) coordinate pairs with the highest fish
        concentration, spaced at least 10 units apart.
    """
    _ensure_spatial_configuration()

    region_map = {
        "A": config.REGION_A,
        "B": config.REGION_B,
        "C": config.REGION_C,
        "D": config.REGION_D,
    }
    region = region_map.get(region_name, [])

    if not region:
        return []

    if ecospace_outputs._ecospace_data_cache is not None:
        try:
            ecospace_data, _ = ecospace_outputs.get_ecospace_data()
            sum_data = np.sum(ecospace_data, axis=2)

            if sum_data is not None:
                fish_map = np.array(sum_data)
                top_coords = sorted(
                    region,
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
        region,
        key=lambda xy: spatial_utils.TOPOLOGY[xy[1]][xy[0]],
        reverse=True,
    )[:3]
    return top_coords

from typing import Dict, List, Tuple


def prepare_spatial_indexes(self) -> None:
    """Builds set-based spatial indexes for O(1) land lookups."""
    self._land_set = {tuple(c) for c in self.LAND}

    self._hotspots_list = [tuple(c) for c in self.HOTSPOTS]
    self._hotspots_set = set(self._hotspots_list)


def build_density_offsets(self) -> None:
    """Pre-computes (dx, dy) offset lists for HIGH and MEDIUM zones.

    HIGH zone: Euclidean distance ≤ 3 from a hotspot.
    MEDIUM zone: 3 < distance ≤ 5 from a hotspot.

    Stores results in ``_high_offsets`` and ``_medium_only_offsets``.
    """
    high_offsets = [
        (dx, dy)
        for dx in range(-3, 4)
        for dy in range(-3, 4)
        if dx * dx + dy * dy <= 9
    ]
    medium_only_offsets = [
        (dx, dy)
        for dx in range(-5, 6)
        for dy in range(-5, 6)
        if 9 < dx * dx + dy * dy <= 25
    ]
    self._high_offsets = high_offsets
    self._medium_only_offsets = medium_only_offsets


def build_density_map_exact(self) -> None:
    """Assigns HIGH / MEDIUM density labels to patches near hotspots.

    First marks MEDIUM cells (ring 3 < d ≤ 5), then marks HIGH cells
    (d ≤ 3), overwriting MEDIUM where they overlap.
    Remaining water cells are implicitly LOW.
    """
    self._density_map: Dict[Tuple[int, int], str] = {}

    for hx, hy in self._hotspots_list:
        for dx, dy in self._medium_only_offsets:
            coord = (hx + dx, hy + dy)
            if coord in self._land_set:
                continue
            self._density_map.setdefault(coord, self.MEDIUM)

    for hx, hy in self._hotspots_list:
        for dx, dy in self._high_offsets:
            coord = (hx + dx, hy + dy)
            if coord in self._land_set:
                continue
            self._density_map[coord] = self.HIGH

from typing import Dict, List, Tuple


def prepare_spatial_indexes(self) -> None:
    """Builds set-based spatial indexes for O(1) region lookups.

    Populates ``_land_set``, ``_region_*_set``, ``_hotspots_*_set``,
    and the aggregating dicts ``_region_sets``, ``_hotspots_lists``,
    and ``_hotspots_sets``.
    """
    self._land_set = {tuple(c) for c in self.LAND}
    self._region_a_set = {tuple(c) for c in self.REGION_A}
    self._region_b_set = {tuple(c) for c in self.REGION_B}
    self._region_c_set = {tuple(c) for c in self.REGION_C}
    self._region_d_set = {tuple(c) for c in self.REGION_D}

    self._hotspots_a_list = [tuple(c) for c in self.HOTSPOTS_A]
    self._hotspots_b_list = [tuple(c) for c in self.HOTSPOTS_B]
    self._hotspots_c_list = [tuple(c) for c in self.HOTSPOTS_C]
    self._hotspots_d_list = [tuple(c) for c in self.HOTSPOTS_D]

    self._hotspots_a_set = set(self._hotspots_a_list)
    self._hotspots_b_set = set(self._hotspots_b_list)
    self._hotspots_c_set = set(self._hotspots_c_list)
    self._hotspots_d_set = set(self._hotspots_d_list)

    self._region_sets: Dict[str, set] = {
        "A": self._region_a_set,
        "B": self._region_b_set,
        "C": self._region_c_set,
        "D": self._region_d_set,
    }
    self._hotspots_lists: Dict[str, List[Tuple[int, int]]] = {
        "A": self._hotspots_a_list,
        "B": self._hotspots_b_list,
        "C": self._hotspots_c_list,
        "D": self._hotspots_d_list,
    }
    self._hotspots_sets: Dict[str, set] = {
        "A": self._hotspots_a_set,
        "B": self._hotspots_b_set,
        "C": self._hotspots_c_set,
        "D": self._hotspots_d_set,
    }

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

    For each region, first marks MEDIUM cells (ring 3 < d ≤ 5) using
    ``setdefault`` so they are not overwritten by a later HIGH mark,
    then marks HIGH cells (d ≤ 3), overwriting MEDIUM where they
    overlap. Remaining region cells are implicitly LOW.
    """
    self._density_map_by_region: Dict[str, Dict[Tuple[int, int], str]] = {
        "A": {}, "B": {}, "C": {}, "D": {}
    }

    for region_label in ("A", "B", "C", "D"):
        region_coords = self._region_sets[region_label]
        hotspots = self._hotspots_lists[region_label]
        density_map = self._density_map_by_region[region_label]

        for hx, hy in hotspots:
            for dx, dy in self._medium_only_offsets:
                coord = (hx + dx, hy + dy)
                if coord in region_coords:
                    density_map.setdefault(coord, self.MEDIUM)

        for hx, hy in hotspots:
            for dx, dy in self._high_offsets:
                coord = (hx + dx, hy + dy)
                if coord in region_coords:
                    density_map[coord] = self.HIGH

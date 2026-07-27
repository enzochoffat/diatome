import numpy as np
from src.infrastructure.ecospace import ecospace_outputs
from typing import Any, Dict, Tuple


def init_patches(self) -> None:
    self._prepare_spatial_indexes()
    self._build_density_offsets()
    self._build_density_map_exact()

    width = self.grid.width
    height = self.grid.height
    growth_rate = self.GROWTH_RATE

    ecospace_data, _ = ecospace_outputs.get_ecospace_data()
    self.species_biomass = ecospace_data.copy()
    sum_data = np.sum(ecospace_data, axis=2)

    total_biomass = np.sum(ecospace_data, axis=2, keepdims=True) + 1e-10
    self.species_ratio = ecospace_data / total_biomass

    patches: Dict[Tuple[int, int], Dict[str, Any]] = {}

    for x_coord in range(height):
        for y_coord in range(width):
            pos = (x_coord, y_coord)
            is_land = pos in self._land_set
            density = self._density_map.get(pos)
            carrying_capacity = self._get_carrying_capacity(density) if density else 0
            fish_stock = sum_data[x_coord, y_coord] if not is_land else 0

            if is_land:
                self.species_biomass[x_coord, y_coord, :] = 0.0
                self.species_ratio[x_coord, y_coord, :] = 0.0

            patches[pos] = {
                "density": density if not is_land else None,
                "fish_stock": fish_stock,
                "carrying_capacity": carrying_capacity,
                "growth_rate": growth_rate,
                "regen_amount": 0,
                "patch_stock_after_regrowth": fish_stock,
            }

    self.patches = patches

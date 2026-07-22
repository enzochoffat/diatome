import numpy as np
from src.infrastructure.ecospace import ecospace_outputs
from src.domain.environment import regions
from typing import Any, Dict, Tuple

def init_patches(self) -> None:
        """Initialises all grid patches with region, density, and stock.

        Builds spatial indexes and density maps, then loads the initial
        fish stock from Ecospace data (or falls back to the carrying
        capacity-based formula for non-fishing cells).

        The 3D species biomass array is stored on the model as
        ``self.species_biomass``. ``patch["fish_stock"]`` is the sum
        across all species for backward compatibility.
        """
        self._prepare_spatial_indexes()
        self._build_density_offsets()
        self._build_density_map_exact()

        width = self.grid.width
        height = self.grid.height
        growth_rate = self.GROWTH_RATE

        ecospace_data, _ = ecospace_outputs.get_ecospace_data()
        # Keep 3D array (H, W, N) as source of truth
        self.species_biomass = ecospace_data.copy()
        sum_data = np.sum(ecospace_data, axis=2)

        # Species ratio for per-species carrying capacity derivation
        total_biomass = np.sum(ecospace_data, axis=2, keepdims=True) + 1e-10
        self.species_ratio = ecospace_data / total_biomass

        patches: Dict[Tuple[int, int], Dict[str, Any]] = {}

        for x_coord in range(height):
            for y_coord in range(width):
                region = self.get_region(x_coord, y_coord)
                density = self.get_density(x_coord, y_coord, region)
                carrying_capacity = self.get_carrying_capacity(
                    region, density
                )
                fish_stock = (
                    sum_data[x_coord, y_coord]
                    if region not in ("LAND", "NULL")
                    else 0
                )
                # LAND/NULL cells get zero species_biomass
                if region in ("LAND", "NULL"):
                    self.species_biomass[x_coord, y_coord, :] = 0.0
                    self.species_ratio[x_coord, y_coord, :] = 0.0

                patches[(x_coord, y_coord)] = {
                    "region": region,
                    "density": density,
                    "fish_stock": fish_stock,
                    "carrying_capacity": carrying_capacity,
                    "growth_rate": growth_rate,
                    "regen_amount": 0,
                    "patch_stock_after_regrowth": fish_stock,
                }

        self.patches = patches
from typing import Dict, List, Tuple, Any

import numpy as np


def reduce_stock(
        self, x: int, y: int, catch_amount: float
    ) -> float:
    pos = (x, y)
    if pos in self.patches:
        current_stock = self.patches[pos]["fish_stock"]
        actual_catch = min(catch_amount, current_stock)
        self._set_patch_fish_stock(pos, current_stock - actual_catch)
        return actual_catch
    return 0


def reduce_stock_by_species(
    self, x: int, y: int, catch_vector: np.ndarray
) -> np.ndarray:
    pos = (x, y)
    if pos not in self.patches:
        return np.zeros_like(catch_vector)

    if pos in self._land_set:
        return np.zeros_like(catch_vector)

    available = self.species_biomass[x, y, :]
    actual_catch = np.minimum(catch_vector, available)
    self.species_biomass[x, y, :] -= actual_catch
    self.patches[pos]["fish_stock"] = float(np.sum(self.species_biomass[x, y, :]))
    return actual_catch


def update_patches(
    self, new_fish_stocks: Dict[Tuple[int, int], float]
) -> None:
    for (x_coord, y_coord), stock in new_fish_stocks.items():
        pos = (x_coord, y_coord)
        if pos in self.patches:
            self._set_patch_fish_stock(pos, stock)


def update_patches_species(
    self, species_biomass: np.ndarray, species_names: List[str]
) -> None:
    self.species_biomass = species_biomass.copy()

    total_biomass = np.sum(species_biomass, axis=2, keepdims=True) + 1e-10
    self.species_ratio = species_biomass / total_biomass

    for (x, y), patch in self.patches.items():
        if (x, y) not in self._land_set:
            patch["fish_stock"] = float(np.sum(self.species_biomass[x, y, :]))

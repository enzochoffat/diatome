from typing import Dict, List, Tuple, Any

import numpy as np


def reduce_stock(
        self, x: int, y: int, catch_amount: float
    ) -> float:
    """Reduces fish stock at a location due to fishing.

    Args:
        x: Column index.
        y: Row index.
        catch_amount: Desired catch quantity.

    Returns:
        Actual catch (capped at the available stock).
    """
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
    """Reduces species biomass at a location by a per-species catch vector.

    Args:
        x: Column index.
        y: Row index.
        catch_vector: Desired catch per species, shape (N,).

    Returns:
        Actual catch per species, capped at available biomass per species.
    """
    pos = (x, y)
    if pos not in self.patches:
        return np.zeros_like(catch_vector)

    region = self.patches[pos].get("region")
    if region in ("LAND", "NULL"):
        return np.zeros_like(catch_vector)

    available = self.species_biomass[x, y, :]
    actual_catch = np.minimum(catch_vector, available)
    self.species_biomass[x, y, :] -= actual_catch
    # Sync the summed fish_stock
    self.patches[pos]["fish_stock"] = float(np.sum(self.species_biomass[x, y, :]))
    return actual_catch

def update_patches(
    self, new_fish_stocks: Dict[Tuple[int, int], float]
) -> None:
    """Replaces patch fish stocks with values from a coupling update.

    Args:
        new_fish_stocks: Mapping of ``(x, y)`` to new stock values.
    """
    sum_a = 0.0
    for (x_coord, y_coord), stock in new_fish_stocks.items():
        pos = (x_coord, y_coord)
        region = self.get_region(x_coord, y_coord)
        if region == "A":
            sum_a += stock
        if pos in self.patches:
            self._set_patch_fish_stock(pos, stock)
    print(f"Total stock for region A after update: {sum_a}")


def update_patches_species(
    self, species_biomass: np.ndarray, species_names: List[str]
) -> None:
    """Replaces the model's species_biomass 3D array with coupling data.

    Args:
        species_biomass: New 3D array (H, W, N).
        species_names: List of species IDs.
    """
    self.species_biomass = species_biomass.copy()

    # Recompute species_ratio
    total_biomass = np.sum(species_biomass, axis=2, keepdims=True) + 1e-10
    self.species_ratio = species_biomass / total_biomass

    # Sync all patch fish_stock
    for (x, y), patch in self.patches.items():
        if patch["region"] not in ("LAND", "NULL"):
            patch["fish_stock"] = float(np.sum(self.species_biomass[x, y, :]))

# ------------------------------------------------------------------
# Regional capacity recalculation
# ------------------------------------------------------------------

def _recalculate_regional_capacities(self) -> None:
    """Recomputes regional carrying capacities from actual patch stocks.

    Updates ``CARRYING_CAPACITY_*`` and ``MSY_STOCK_*`` attributes
    based on the current sum of fish stocks per region.
    """
    for region in ("A", "B", "C", "D"):
        total_capacity = sum(
            patch["fish_stock"]
            for patch in self.patches.values()
            if patch["region"] == region
        )
        msy = round(total_capacity / 2)

        if region == "A":
            self.CARRYING_CAPACITY_A = total_capacity
            self.MSY_STOCK_A = msy
        elif region == "B":
            self.CARRYING_CAPACITY_B = total_capacity
            self.MSY_STOCK_B = msy
        elif region == "C":
            self.CARRYING_CAPACITY_C = total_capacity
            self.MSY_STOCK_C = msy
        elif region == "D":
            self.CARRYING_CAPACITY_D = total_capacity
            self.MSY_STOCK_D = msy

def validate_regional_stocks(self) -> List[Dict[str, Any]]:
    """Checks that no region exceeds its carrying capacity.

    Returns:
        List of violation dicts (empty if all regions are within
        bounds). Each dict has keys ``region``, ``current``,
        ``max``, ``excess``, and ``percentage``.
    """
    violations: List[Dict[str, Any]] = []
    for region in ("A", "B", "C", "D"):
        current_stock = self.get_region_stock(region)
        max_capacity = self.get_region_carrying_capacity(region)
        if current_stock > max_capacity:
            violations.append({
                "region": region,
                "current": current_stock,
                "max": max_capacity,
                "excess": current_stock - max_capacity,
                "percentage": (current_stock / max_capacity) * 100,
            })
    return violations
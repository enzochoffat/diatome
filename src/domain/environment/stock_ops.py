from typing import Dict, List, Tuple, Any


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
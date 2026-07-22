import numpy as np


def _grow_species_at_patch(
    model, x: int, y: int, effective_rate: float, species_indices: slice
) -> float:
    """Applies logistic growth per species at a single patch.

    Carrying capacity per species is derived from the total patch
    carrying capacity proportionally to initial species ratio.
    """
    region = model.patches[(x, y)]["region"]
    if region in ("LAND", "NULL"):
        return 0.0

    total_cc = model.patches[(x, y)]["carrying_capacity"]
    ratio = model.species_ratio[x, y, :]
    biomass = model.species_biomass[x, y, :]

    total_growth = 0.0
    for s in range(model.species_biomass.shape[2]):
        cc_s = total_cc * ratio[s]
        if cc_s <= 0 or biomass[s] <= 0:
            continue
        growth = biomass[s] * effective_rate * (1.0 - biomass[s] / cc_s)
        model.species_biomass[x, y, s] = max(0.0, biomass[s] + growth)
        total_growth += growth

    model._sync_patch_fish_stock(x, y)
    return total_growth


def update_fish_stock(model, time_step_days: int = 1) -> None:
    effective_rate = model.GROWTH_RATE * (time_step_days / model.YEAR)

    for pos in model.patches:
        _grow_species_at_patch(model, pos[0], pos[1], effective_rate, slice(None))


def update_fish_stock_yearly(model) -> None:
    effective_rate = model.GROWTH_RATE

    for pos in model.patches:
        patch = model.patches[pos]
        if patch["region"] in ("LAND", "NULL"):
            continue

        total_growth = _grow_species_at_patch(
            model, pos[0], pos[1], effective_rate, slice(None)
        )
        patch["regen_amount"] = total_growth
        patch["patch_stock_after_regrowth"] = patch["fish_stock"]
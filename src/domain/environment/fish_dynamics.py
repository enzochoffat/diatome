import numpy as np


def _grow_species_at_patch(
    model, x: int, y: int, effective_rate: float, species_indices: slice
) -> float:
    if (x, y) in model._land_set:
        return 0.0

    total_cc = model.patches[(x, y)]["carrying_capacity"]
    ratio = model.species_ratio[x, y, :]
    biomass = model.species_biomass[x, y, :]

    total_growth = 0.0
    for s in range(model.species_biomass.shape[2]):
        cc_s = total_cc * ratio[s]
        if cc_s <= 0:
            continue
        if biomass[s] <= 0:
            growth = 0.01 * cc_s * effective_rate * 365
            model.species_biomass[x, y, s] = max(0.0, growth)
            total_growth += growth
            continue
        growth = biomass[s] * effective_rate * (1.0 - biomass[s] / cc_s)
        model.species_biomass[x, y, s] = max(0.0, biomass[s] + growth)
        total_growth += growth

    model._sync_patch_fish_stock(y, x)
    return total_growth


def update_fish_stock(model, time_step_days: int = 1) -> None:
    effective_rate = model.GROWTH_RATE * (time_step_days / model.YEAR)

    for pos in model.patches:
        _grow_species_at_patch(model, pos[0], pos[1], effective_rate, slice(None))


def update_fish_stock_yearly(model) -> None:
    effective_rate = model.GROWTH_RATE

    for pos in model.patches:
        if pos in model._land_set:
            continue

        total_growth = _grow_species_at_patch(
            model, pos[0], pos[1], effective_rate, slice(None)
        )
        patch = model.patches[pos]
        patch["regen_amount"] = total_growth
        patch["patch_stock_after_regrowth"] = patch["fish_stock"]

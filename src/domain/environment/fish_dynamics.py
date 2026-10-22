import numpy as np


def _grow_species_at_patch(
    model, x: int, y: int, effective_rate: float, species_indices: slice
) -> float:
    if (x, y) in model._land_set:
        return 0.0

    total_cc = model.patches[(x, y)]["carrying_capacity"]
    ratio = model.species_ratio[y, x, :]
    biomass = model.species_biomass[y, x, :]

    total_growth = 0.0
    for s in range(model.species_biomass.shape[2]):
        cc_s = total_cc * ratio[s]
        if not np.isfinite(cc_s) or cc_s <= 0:
            continue
        old_biomass = max(0.0, float(biomass[s]))
        if old_biomass <= 0:
            new_biomass = 0.01 * cc_s * effective_rate * 365
        else:
            new_biomass = old_biomass + old_biomass * effective_rate * (
                1.0 - old_biomass / cc_s
            )
        new_biomass = max(0.0, new_biomass)
        model.species_biomass[y, x, s] = new_biomass
        total_growth += new_biomass - old_biomass

    model._sync_patch_fish_stock(x, y)
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

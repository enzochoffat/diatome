def update_fish_stock(model, time_step_days: int = 1) -> None:

    effective_rate = model.GROWTH_RATE * (time_step_days / model.YEAR)

    density_factor = {
        model.HIGH: 2.0,
        model.MEDIUM: 1.25,
        model.LOW: 1.0,
    }

    growth_by_region = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}

    for patch in model.patches.values():
        region = patch["region"]

        if region in ("LAND", "NULL"):
            continue

        current_stock = patch["fish_stock"]
        carrying_capacity = patch["carrying_capacity"]

        factor = density_factor.get(patch["density"], 1.0)

        regen_amount = (
            current_stock
            * effective_rate
            * factor
            * (1 - current_stock / carrying_capacity)
        )

        patch["regen_amount"] = regen_amount
        growth_by_region[region] += regen_amount

    for region in ("A", "B", "C", "D"):

        current_regional_stock = model.get_region_stock(region)
        regional_capacity = model.get_region_carrying_capacity(region)

        proposed_stock = current_regional_stock + growth_by_region[region]

        if proposed_stock > regional_capacity:

            raw_growth = growth_by_region[region]

            scale_factor = (
                max(
                    0.0,
                    min(
                        1.0,
                        (regional_capacity - current_regional_stock)
                        / raw_growth,
                    ),
                )
                if raw_growth > 0
                else 0.0
            )

            for pos, patch in model.patches.items():

                if patch["region"] == region:
                    patch["regen_amount"] = round(
                        patch["regen_amount"] * scale_factor
                    )

                    model._set_patch_fish_stock(
                        pos,
                        patch["fish_stock"] + patch["regen_amount"],
                    )

                    patch["patch_stock_after_regrowth"] = (
                        patch["fish_stock"]
                    )

        else:
            for pos, patch in model.patches.items():

                if patch["region"] == region:

                    model._set_patch_fish_stock(
                        pos,
                        patch["fish_stock"] + patch["regen_amount"],
                    )

                    patch["patch_stock_after_regrowth"] = (
                        patch["fish_stock"]
                    )


def update_fish_stock_yearly(model) -> None:

    for pos, patch in model.patches.items():

        if patch["region"] in ("LAND", "NULL"):
            continue

        current_stock = patch["fish_stock"]
        carrying_capacity = patch["carrying_capacity"]

        regen_amount = round(
            current_stock
            * model.GROWTH_RATE
            * (1 - current_stock / carrying_capacity)
        )

        patch["regen_amount"] = regen_amount

        model._set_patch_fish_stock(
            pos,
            current_stock + regen_amount,
        )

        patch["patch_stock_after_regrowth"] = patch["fish_stock"]
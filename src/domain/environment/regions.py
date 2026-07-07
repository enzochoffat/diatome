from typing import Optional


def get_region(model, x: int, y: int) -> str:
    coord = (x, y)

    if coord in model._land_set:
        return "LAND"
    if coord in model._region_a_set:
        return "A"
    if coord in model._region_b_set:
        return "B"
    if coord in model._region_c_set:
        return "C"
    if coord in model._region_d_set:
        return "D"

    return "NULL"


def get_density(model, x: int, y: int, region: str) -> Optional[str]:
    if region in ("LAND", "NULL"):
        return None

    return model._density_map_by_region[region].get(
        (x, y), model.LOW
    )


def get_carrying_capacity(model, region: str, density: Optional[str]) -> int:
    if region in ("LAND", "NULL") or density is None:
        return 0

    density_upper = (
        density.upper() if isinstance(density, str) else str(density).upper()
    )

    base_capacity_map = {
        "HIGH": model.HIGH_CARRYING_CAPACITY,
        "MEDIUM": model.MEDIUM_CARRYING_CAPACITY,
        "LOW": model.LOW_CARRYING_CAPACITY,
    }

    if density_upper not in base_capacity_map:
        print(f"WARNING: Unknown density '{density}' for region {region}")
        return 0

    base_capacity = base_capacity_map[density_upper]
    sd = model.SD_CARCAP * base_capacity

    import numpy as np

    random_capacity = np.random.normal(base_capacity, sd)

    return max(1, round(random_capacity))
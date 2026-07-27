from typing import Tuple, Dict, Any


def set_patch_fish_stock(model, pos: Tuple[int, int], new_stock: float) -> float:
    patch = model.patches[pos]

    old_stock = patch["fish_stock"]
    new_stock = max(0.0, new_stock)

    delta = new_stock - old_stock
    patch["fish_stock"] = new_stock

    if delta:
        model._region_stock_cache["TOTAL"] += delta

    return patch["fish_stock"]


def adjust_patch_fish_stock(model, pos: Tuple[int, int], delta: float) -> float:
    current_stock = model.patches[pos]["fish_stock"]
    return set_patch_fish_stock(model, pos, current_stock + delta)


def get_patch_info(model, x: int, y: int) -> Dict[str, Any]:
    return model.patches.get((x, y))

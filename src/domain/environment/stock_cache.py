from typing import Dict


def initialize_region_stock_cache(self) -> None:
    """Rebuilds the regional stock cache from scratch.

    Iterates over all patches, summing fish stocks per region into
    ``_region_stock_cache``.
    """
    cache: Dict[str, float] = {
        "A": 0, "B": 0, "C": 0, "D": 0, "TOTAL": 0
    }
    for patch in self.patches.values():
        region = patch["region"]
        if region in ("A", "B", "C", "D"):
            fish_stock = patch["fish_stock"]
            cache[region] += fish_stock
            cache["TOTAL"] += fish_stock
    self._region_stock_cache = cache

def _refresh_region_stocks_cache(self) -> None:
    """Alias for ``_initialize_region_stock_cache``."""
    self._initialize_region_stock_cache()

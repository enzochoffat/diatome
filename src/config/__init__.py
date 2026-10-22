"""Configuration package alias.

Canonical source is ``src.core.config``. This package re-exports it so
``from src import config`` and ``import src.config`` keep working while
always seeing live values (e.g. WATER_CELLS populated by
reload_spatial_configuration).

The former divergent ``src/config/default.py`` and empty
``src/config/spatial.py`` were removed on 2026-09-11 to leave a single
source of truth.
"""

import sys

from src.core import config as _core_config

sys.modules[__name__] = _core_config

"""Compatibility package for configuration imports.

This package is an alias for src.core.config so legacy imports like
``from src import config`` keep working while always seeing the live
values (e.g. WATER_CELLS populated by reload_spatial_configuration).
"""

import sys

from src.core import config as _core_config

sys.modules[__name__] = _core_config

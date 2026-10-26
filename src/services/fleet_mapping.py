"""EwE fleet ↔ FIBE flotilla mapping (coupling interface).

At coupling step 1, Ecospace exports ``Couplage/Data/fibe_fleets.json``
listing the EwE fleets managed by FIBE with their FIBE flotilla type::

    {"fleets": [
        {"fleet_index": 1, "fleet_name": "Small boats", "flottille": "archipelago"},
        ...
    ]}

FIBE uses this mapping to:

- route its per-flotilla fishing mortality back to the right EwE fleet
  (the "flottille" column of ``F_<count>.csv`` holds the 1-based EwE
  fleet index), and
- pick the right catchability/price column for each flotilla
  (the converted EwE tables use the EwE fleet index as column label).

Without the file, a positional fallback is used: flotilla i (internal
0-based order archipelago, coastal, trawler) maps to EwE fleet i+1.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

#: Canonical FIBE flotilla types, in internal 0-based matrix order
#: (catchability/price rows, monthly catch arrays).
FLOTTILLA_TYPES = ["archipelago", "coastal", "trawler"]

#: Positional fallback: EwE fleets are 1-based, flotilla i -> EwE fleet i+1.
DEFAULT_EWE_FLEET_INDEX = {
    "archipelago": 1,
    "coastal": 2,
    "trawler": 3,
}

#: Expected location of the Ecospace-exported mapping, relative to the
#: FIBE working directory (Couplage/FIBE) or the config file location.
MAPPING_RELATIVE_PATH = "../Data/fibe_fleets.json"


def resolve_mapping_file(config_loader: Optional[Any] = None) -> Optional[Path]:
    """Locate the Ecospace-exported ``fibe_fleets.json``, if it exists.

    Args:
        config_loader: Optional ``ConfigLoader`` used to resolve the
            relative path the same way as the other coupling maps
            (handles config dir, parent dir and WSL/Windows paths).

    Returns:
        Path to the mapping file, or None when not found.
    """
    if config_loader is not None and hasattr(config_loader, "_resolve_config_path"):
        try:
            resolved = config_loader._resolve_config_path(MAPPING_RELATIVE_PATH)
        except Exception:
            resolved = None
        if resolved and Path(resolved).exists():
            return Path(resolved)

    candidate = Path.cwd() / MAPPING_RELATIVE_PATH
    if candidate.exists():
        return candidate
    return None


def load_ewe_fleet_mapping(config_loader: Optional[Any] = None) -> Dict[str, int]:
    """Build the flotilla → EwE fleet index map (EwE fleets are 1-based).

    Args:
        config_loader: Optional ``ConfigLoader`` to locate the mapping file.

    Returns:
        Dict with one entry per canonical flotilla. Entries absent from
        the exported file (or from the file itself) fall back to the
        positional default (archipelago=1, coastal=2, trawler=3).
    """
    result: Dict[str, int] = dict(DEFAULT_EWE_FLEET_INDEX)

    path = resolve_mapping_file(config_loader)
    if path is None:
        logger.info(
            "No fibe_fleets.json found; using positional EwE fleet mapping "
            "(archipelago=1, coastal=2, trawler=3)"
        )
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(
            "Could not read %s (%s); using positional EwE fleet mapping",
            path, exc,
        )
        return result

    for entry in data.get("fleets", []):
        if not isinstance(entry, dict):
            continue
        flotilla = str(entry.get("flottille", "")).strip().lower()
        try:
            fleet_index = int(entry.get("fleet_index", -1))
        except (TypeError, ValueError):
            logger.warning(
                "Ignoring malformed fleet mapping entry: %s", entry,
            )
            continue
        if flotilla not in FLOTTILLA_TYPES:
            logger.warning(
                "Ignoring unknown flotilla '%s' in %s", flotilla, path,
            )
            continue
        if fleet_index < 1:
            logger.warning(
                "Ignoring non-positive EwE fleet index %s for flotilla '%s'",
                fleet_index, flotilla,
            )
            continue
        if flotilla in result and result[flotilla] != DEFAULT_EWE_FLEET_INDEX[flotilla]:
            logger.warning(
                "Duplicate flotilla '%s' in %s; keeping first entry (fleet %s)",
                flotilla, path, result[flotilla],
            )
            continue
        result[flotilla] = fleet_index

    logger.info("EwE fleet mapping loaded from %s: %s", path, result)
    return result

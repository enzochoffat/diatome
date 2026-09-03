#!/usr/bin/env python3
"""
Run a single FIBE fishery simulation.
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path


# Add parent directory to path to import source modules
sys.path.insert(0, str(Path(__file__).parent.parent))


from src.infrastructure.loader import load_config  # noqa: E402
from src.core.model import FisheryModel  # noqa: E402


logger = logging.getLogger(__name__)


def run_from_config(config_path: str, run_id: int = 0) -> FisheryModel:
    """
    Run a simulation from a JSON configuration file.

    Args:
        config_path: Path to config file
        run_id: Simulation run identifier

    Returns:
        Configured FisheryModel instance
    """
    logger.info(
        "Starting simulation run",
        extra={"config": config_path, "run_id": run_id},
    )

    try:
        config_loader = load_config(config_path)

        config_loader.apply_map_configuration()

        model_params = config_loader.get_model_params()

        logger.debug("Model parameters loaded", extra=model_params)

        model = FisheryModel(**model_params, config_loader=config_loader)

        logger.info("Model initialized")

        model.run_model()

        logger.info("Simulation completed successfully")

        output_params = config_loader.get_output_params()
        if output_params.get("export_data", False):
            prefix = output_params.get("filename_prefix", "fibe_output")
            model.export_data(filename_prefix=prefix)

        return model

    except Exception:
        logger.exception("Simulation failed")
        raise


def main() -> None:
    """Parse command-line arguments and run the simulation."""

    #setup_logging(log_level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Run FIBE simulation from JSON configuration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("config", type=str, help="Path to config file")
    parser.add_argument(
        "--run-id",
        type=int,
        default=0,
        help="Run identifier",
    )

    args = parser.parse_args()

    logger.info("CLI arguments parsed", extra=vars(args))

    try:
        run_from_config(args.config, args.run_id)

    except Exception:
        logger.exception("Fatal error in simulation")
        sys.exit(1)


if __name__ == "__main__":
    main()

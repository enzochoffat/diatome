#!/usr/bin/env python3
"""Run a single FIBE fishery simulation.

Example:
    python scripts/run_simulation.py config.json
    python scripts/run_simulation.py config.json --run-id 3
"""

import argparse
import sys
import traceback
from pathlib import Path

# Add parent directory to path to import source modules.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ecospace_outputs import (  # noqa: E402
    configure_sources,
    get_ecospace_data,
    plot_masks,
)
from src.loader import load_config  # noqa: E402
from src.model import FisheryModel  # noqa: E402


def run_from_config(config_path: str, run_id: int = 0) -> FisheryModel:
    """Run a simulation from a JSON configuration file.

    Args:
        config_path: Path to the JSON configuration file.
        run_id: Identifier used when running multiple repetitions.

    Returns:
        A completed ``FisheryModel`` instance.
    """
    loader = load_config(config_path)

    loader.apply_map_configuration()

    metadata = loader.get_metadata()
    model_params = loader.get_model_params()
    output_params = loader.get_output_params()

    if model_params["verbose"]:
        print("=" * 80)
        print(f"FIBE SIMULATION: {metadata['name']}")

        if "description" in metadata:
            print(metadata["description"])

        print("=" * 80)
        print(f"Duration: {model_params['end_of_sim'] // 365} years")
        print(
            f"Agents: {model_params['num_archipelago']} archipelago, "
            f"{model_params['num_coastal']} coastal, "
            f"{model_params['num_trawler']} trawler"
        )
        print("=" * 80)
        print()

    model = FisheryModel(**model_params, config_loader=loader)

    loader.apply_custom_parameters(model)

    model.run_model()

    if output_params["export_data"]:
        prefix = output_params["filename_prefix"]

        if run_id > 0:
            prefix = f"{prefix}_run{run_id:03d}"

        timestamp = model.export_data(filename_prefix=prefix)

        config_output = f"{prefix}_config_{timestamp}.json"
        loader.save_config(config_output)

        if model_params["verbose"]:
            print(f"Configuration saved: {config_output}")

    return model


def main() -> None:
    """Parse command-line arguments and run the simulation."""
    parser = argparse.ArgumentParser(
        description="Run FIBE simulation from JSON configuration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "config",
        type=str,
        help="Path to JSON configuration file",
    )

    parser.add_argument(
        "--run-id",
        type=int,
        default=0,
        help="Run identifier for batch experiments",
    )

    args = parser.parse_args()

    try:
        model = run_from_config(args.config, args.run_id)

        if model.verbose:
            print("\nSimulation completed successfully")

    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    except ValueError as exc:
        print(
            f"ERROR: Invalid configuration - {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    except Exception as exc:
        print(f"ERROR: Simulation failed - {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
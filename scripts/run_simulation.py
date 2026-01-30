#!/usr/bin/env python3
"""
Run a single FIBE fishery simulation

Usage:
    python scripts/run_simulation.py --years 25 --archipelago 30 --coastal 30 --trawler 30
"""

import argparse
import sys
import traceback
from pathlib import Path

# Add parent directory to path to import code module
sys.path.insert(0, str(Path(__file__).parent.parent))

from code.model import FisheryModel
from code.loader import load_config

def run_from_config(config_path, run_id=0):
    """
    Run simulation from JSON configuration.
    
    Args:
        config_path: Path to JSON configuration file
        run_id: Run identifier (for multiple repetitions)
        
    Returns:
        FisheryModel: Completed model instance
    """
    loader = load_config(config_path)
    metadata = loader.get_metadata()
    model_params = loader.get_model_params()
    output_params = loader.get_output_params()
    
    if model_params["verbose"]:
        print("="*80)
        print(f"FIBE SIMULATION: {metadata['name']}")
        if "description" in metadata:
            print(f"{metadata['description']}")
        print("="*80)
        print(f"Duration: {model_params['end_of_sim']//365} years")
        print(f"Agents: {model_params['num_archipelago']} archipelago, "
              f"{model_params['num_coastal']} coastal, "
              f"{model_params['num_trawler']} trawler")
        print("="*80 + "\n")
        
    model = FisheryModel(**model_params)
    
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

def main():
    """
    Command-line interface.
    """
    parser = argparse.ArgumentParser(
        description='Run FIBE simulation from JSON configuration',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        'config',
        type=str,
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--run-id',
        type=int,
        default=0,
        help='Run identifier (for batch experiments)'
    )
    
    args = parser.parse_args()
    
    try:
        model = run_from_config(args.config, args.run_id)
        
        if model.verbose:
            print("\n Simulation completed successfully")
            
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: Invalid configuration - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Simulation failed - {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
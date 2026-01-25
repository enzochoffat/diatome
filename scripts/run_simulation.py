#!/usr/bin/env python3
"""
Run a single FIBE fishery simulation

Usage:
    python scripts/run_simulation.py --years 25 --archipelago 30 --coastal 30 --trawler 30
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to import code module
sys.path.insert(0, str(Path(__file__).parent.parent))

from code.model import FisheryModel


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run FIBE fishery simulation',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Simulation duration
    parser.add_argument(
        '--years', 
        type=int, 
        default=25,
        help='Number of years to simulate'
    )
    
    # Agent counts
    parser.add_argument(
        '--archipelago', 
        type=int, 
        default=30,
        help='Number of archipelago fishers'
    )
    parser.add_argument(
        '--coastal', 
        type=int, 
        default=30,
        help='Number of coastal fishers'
    )
    parser.add_argument(
        '--trawler', 
        type=int, 
        default=30,
        help='Number of trawler fishers'
    )
    
    # Output
    parser.add_argument(
        '--output', 
        type=str, 
        default='fibe_output',
        help='Output filename prefix for exported data'
    )
    
    # Verbosity
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress output'
    )
    
    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_args()
    
    # Calculate total simulation days
    total_days = args.years * 365
    
    # Print configuration
    if not args.quiet:
        print("="*60)
        print("FIBE Fishery Simulation")
        print("="*60)
        print(f"Duration: {args.years} years ({total_days} days)")
        print(f"Agents: {args.archipelago} archipelago, {args.coastal} coastal, {args.trawler} trawler")
        print(f"Total agents: {args.archipelago + args.coastal + args.trawler}")
        print(f"Output prefix: {args.output}")
        print("="*60)
        print()
    
    # Create model
    model = FisheryModel(
        end_of_sim=total_days,
        num_archipelago=args.archipelago,
        num_coastal=args.coastal,
        num_trawler=args.trawler,
        verbose=not args.quiet
    )
    
    # Run simulation
    try:
        model.run_model()
        
        # Export data
        if not args.quiet:
            print("\nExporting data...")
        model.export_data(filename_prefix=args.output)
        
        # Print summary
        if not args.quiet:
            print("\n" + "="*60)
            print("SIMULATION COMPLETED SUCCESSFULLY")
            print("="*60)
            summary = model.get_model_summary()
            print(f"Final year: {summary['current_year']}")
            print(f"Total catch: {summary['total_catch']:,.0f}")
            print(f"Final stock: {summary['total_stock']:,.0f}")
            print(f"Active agents: {summary['num_agents']}")
            print("="*60)
            
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Simulation failed")
        print(f"{type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
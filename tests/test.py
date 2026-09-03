"""
Script to run the FIBE fishery simulation for 5 years and save results
"""

from model import FisheryModel
import pandas as pd
import json
from datetime import datetime
import os



if __name__ == "__main__":
    # Simple run
    print("Starting FIBE Fishery Simulation")
    print("=" * 80)
    
    # Run single simulation
    model = FisheryModel(
        num_archipelago=28,
        num_coastal=45,
        num_trawler=0,
        end_of_sim=365*25,
    )
    
    model.run_model(steps=365*25)
    
    # Uncomment to run multiple scenarios
    # results = run_multiple_scenarios()
    
    print("\n✓ All simulations completed successfully!")
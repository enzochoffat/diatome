import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from . import config as default_config
 
class ConfigLoader:
    """Load and validate experiment configuration from JSON files"""
    
    def __init__(self, config_dir="configs"):
        """
        Initialize configuration loader.
        
        Args:
            config_dir: Path to configuration directory
        """
        
        self.config_dir = Path(config_dir)
        self.loaded_config = None
        
    def load(self, config_path):
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to JSON config file (relative to config_dir or absolute)
            
        Returns:
            Dict containing configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        
        if not os.path.isabs(config_path):
            config_path = self.config_dir / config_path
            
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            
        self._validate_config(config_data)
        
        config_data = self._merge_with_defaults(config_data)
        
        self.loaded_config = config_data
        
        return config_data
    
    def _validate_config(self, config):
        """
        Validate configuration structure.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If configuration is invalid
        """
        
        required_section = ["metadata", "simulation", "agents", "output"]
        
        for section in required_section:
            if section not in config:
                raise ValueError(f"Missing required section: {section}")
            
        sim = config["simulation"]
        if "duration_years" not in sim:
            raise ValueError(f"Missing 'duration_years' in simulation section")
        
        if sim["duration_years"] <= 0:
            raise ValueError("duration_years must be positive")
        
        agents = config["agents"]
        required_agents = ["num_archipelago", "num_coastal", "num_trawler"]
        for agent_type in required_agents:
            if agent_type not in agents:
                raise ValueError(f"Missing agent count: {agent_type}")
            if agents[agent_type] < 0:
                raise ValueError(f"{agent_type} must be non-negative")
            
    def _merge_with_defaults(self, config):
        """
        Merge configuration with default values.
        
        Args:
            config: User configuration
            
        Returns:
            Merged configuration
        """
    
        defaults = {
            "simulation": {
                "verbose": True,
                "random_seed": None,
                "repetitions": 1
            },
            "output": {
                "export_data": True,
                "filename_prefix": "fibe_output",
                "save_final_state": False,
                "export_yearly_only": False
            },
            "parameters": {}
        }
        
        for section, values in defaults.items():
            if section not in config:
                config[section] = values
            else:
                for key, default_value in values.items():
                    if key not in config[section]:
                        config[section][key] = default_value
        
        return config
    
    def get_model_params(self):
        """
        Extract parameters for FisheryModel initialization.
        
        Returns:
            Dict with model parameters
        """
        
        if self.loaded_config is None:
            raise ValueError("No configuration loaded. Call load() first.")
        
        config = self.loaded_config
        
        return{
            "end_of_sim": config["simulation"]["duration_years"] * 365,
            "num_archipelago": config["agents"]["num_archipelago"],
            "num_coastal": config["agents"]["num_coastal"],
            "num_trawler": config["agents"]["num_trawler"],
            "verbose": config["simulation"]["verbose"]
        }
    
    def get_output_params(self):
        """Get output configuration parameters"""
        if self.loaded_config is None:
            raise ValueError("No configuration loaded")
        
        return self.loaded_config["output"]
    
    def get_metadata(self):
        """Get experiment metadata"""
        if self.loaded_config is None:
            raise ValueError("No configuration loaded")
        
        return self.loaded_config["metadata"]
    
    def apply_custom_parameters(self, model):
        """
        Apply custom parameter overrides to model.
        
        Args:
            model: FisheryModel instance
        """
        if self.loaded_config is None or "parameters" not in self.loaded_config:
            return
        
        params = self.loaded_config["parameters"]
        
        if "fish_dynamics" in params:
            fish_params = params["fish_dynamics"]
            if "growth_rate" in fish_params:
                model.GROWTH_RATE = fish_params["growth_rate"]
                
        if "economics" in params:
            eco_params = params["economics"]
            if "fish_price" in eco_params:
                model.FISH_PRICE = eco_params["fish_price"]
                
        if "weather" in params:
            weather_params = params["weather"]
            if "bad_weather_probability" in weather_params:
                model.bad_weather_probability = weather_params["bad_weather_probability"]
                
    def save_config(self, output_path):
        """
        Save current configuration to file (for reproducibility).
        
        Args:
            output_path: Path to save configuration
        """
        if self.loaded_config is None:
            raise ValueError("No configuration loaded")
        
        config_copy = self.loaded_config.copy()
        config_copy["execution"] = {
            "timestamp": datetime.now().isoformat(),
            "config_loader_version": "1.0"
        }
        
        with open(output_path, 'w') as f:
            json.dump(config_copy, f, indent=2)
            
def load_config(config_path):
    """
    Convenience function to load a configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ConfigLoader instance with loaded configuration
    """
    loader = ConfigLoader()
    loader.load(config_path)
    return loader
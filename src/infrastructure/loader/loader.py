"""Configuration loader for FIBE fishery model experiments.

Provides utilities to load, validate, merge, and apply JSON-based
experiment configurations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.core import config as default_config
from src.infrastructure.ecospace import ecospace_outputs
from src.infrastructure.ports.ports_loader import load_ports_map
from src.domain.environment import spatial_utils
from src.domain.environment.weather import read_wave_height_vector
from src.domain.environment.ocean_currents import load_ocean_current_map
from src.domain.environment.restricted_areas import load_restricted_area_map, load_restricted_area_vector


class ConfigLoader:
    """Loads and validates experiment configuration from JSON files.

    Attributes:
        config_dir: Directory used to resolve relative config paths.
        loaded_config: The configuration dict after loading, or None.
        config_path: Resolved absolute path to the loaded file, or None.
    """

    _REQUIRED_SECTIONS = ["metadata", "simulation", "agents", "output"]
    _REQUIRED_AGENT_KEYS = ["num_archipelago", "num_coastal", "num_trawler"]
    _VALID_STOCK_SIZES = {
        "random",
        "carryingCap",
        "halfCarryingCap",
        "quartCarryingCap",
    }

    def __init__(self, config_dir: str = "configs_json") -> None:
        """Initialises the configuration loader.

        Args:
            config_dir: Path to the directory containing config files.
        """
        self.config_dir = Path(config_dir)
        self.loaded_config: Optional[Dict[str, Any]] = None
        self.config_path: Optional[Path] = None

    def load(self, config_path: str) -> Dict[str, Any]:
        """Loads a configuration from a JSON file.

        The path may be absolute or relative. Relative paths are
        resolved first against the current working directory, then
        against ``config_dir``.

        Args:
            config_path: Path to the JSON config file.

        Returns:
            Dictionary containing the merged configuration.

        Raises:
            FileNotFoundError: If the config file cannot be found.
            json.JSONDecodeError: If the file contains invalid JSON.
            ValueError: If the configuration structure is invalid.
        """
        resolved = self._find_config_file(Path(config_path))
        self.config_path = resolved.resolve()

        with open(resolved, "r") as f:
            config_data = json.load(f)

        self._validate_config(config_data)
        config_data = self._merge_with_defaults(config_data)
        self.loaded_config = config_data
        return config_data

    def _find_config_file(self, config_path: Path) -> Path:
        """Locates a config file from an absolute or relative path.

        Args:
            config_path: Candidate path (absolute or relative).

        Returns:
            Resolved ``Path`` to an existing config file.

        Raises:
            FileNotFoundError: If the file cannot be found at any
                candidate location.
        """
        if config_path.is_absolute():
            if not config_path.exists():
                raise FileNotFoundError(
                    f"Configuration file not found: {config_path}"
                )
            return config_path

        candidates = [config_path, self.config_dir / config_path]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validates the top-level structure of a configuration dict.

        Args:
            config: Configuration dictionary to validate.

        Raises:
            ValueError: If any required section or key is missing, or
                if a value violates its constraint.
        """
        for section in self._REQUIRED_SECTIONS:
            if section not in config:
                raise ValueError(f"Missing required section: {section}")

        sim = config["simulation"]
        if "duration_years" not in sim:
            raise ValueError(
                "Missing 'duration_years' in simulation section"
            )
        if sim["duration_years"] <= 0:
            raise ValueError("duration_years must be positive")

        agents = config["agents"]
        for agent_key in self._REQUIRED_AGENT_KEYS:
            if agent_key not in agents:
                raise ValueError(f"Missing agent count: {agent_key}")
            if agents[agent_key] < 0:
                raise ValueError(f"{agent_key} must be non-negative")

    def _merge_with_defaults(
        self, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merges a user configuration with built-in default values.

        Missing top-level sections are added wholesale; missing keys
        within existing sections are filled individually.

        Args:
            config: User-supplied configuration dictionary.

        Returns:
            Configuration dictionary with defaults applied.
        """
        defaults: Dict[str, Any] = {
            "simulation": {
                "verbose": True,
                "random_seed": None,
                "repetitions": 1,
                "coupling": False,
            },
            "output": {
                "export_data": True,
                "filename_prefix": "fibe_output",
                "save_final_state": False,
                "export_yearly_only": False,
            },
            "parameters": {},
        }

        for section, values in defaults.items():
            if section not in config:
                config[section] = values
            else:
                for key, default_value in values.items():
                    if key not in config[section]:
                        config[section][key] = default_value

        return config

    def _resolve_config_path(
        self, relative_path: Optional[str]
    ) -> Optional[str]:
        """Resolves a path from the loaded JSON configuration file location.

        Tries the config file's directory, its parent, and the current
        working directory in order, returning the first match found.

        Args:
            relative_path: A path string from the JSON config, which
                may be absolute, relative, or None.

        Returns:
            Absolute path string if the file exists somewhere, or the
            best-guess absolute path if it does not. Returns None if
            ``relative_path`` is None.
        """
        if relative_path is None:
            return None

        path = Path(relative_path)
        if path.is_absolute():
            return str(path)

        candidates: List[Path] = []
        if self.config_path is not None:
            candidates.append(self.config_path.parent / path)
            candidates.append(self.config_path.parent.parent / path)
        candidates.append(Path.cwd() / path)

        for candidate in candidates:
            if candidate.exists():
                return str(candidate.resolve())

        return (
            str(candidates[0].resolve())
            if candidates
            else str(path.resolve())
        )

    def get_map_params(self) -> Dict[str, Any]:
        """Extracts map-related configuration parameters.

        Returns:
            Dictionary with keys ``topology_map``, ``wind_farm_map``,
            and ``species_map`` (a dict of species-name → path).

        Raises:
            ValueError: If no configuration has been loaded.
        """
        self._require_loaded()

        maps = self.loaded_config.get("maps", {})
        species_map = maps.get("species_map") or {}
        habitat_map = maps.get("habitat_map") or {}
        restricted_area_map = maps.get("restricted_area_map")
        if isinstance(restricted_area_map, dict):
            restricted_area_map = {
                zone_name: self._resolve_config_path(zone_path)
                for zone_name, zone_path in restricted_area_map.items()
            }
        else:
            restricted_area_map = self._resolve_config_path(restricted_area_map)

        return {
            "topology_map": self._resolve_config_path(
                maps.get("spatial_map")
            ),
            "wind_farm_map": self._resolve_config_path(
                maps.get("wind_farm_map")
            ),
            "species_map": {
                species_name: self._resolve_config_path(species_path)
                for species_name, species_path in species_map.items()
            },
            "ports_map": self._resolve_config_path(
                maps.get("ports_map")
            ),
            "habitat_map": {
                habitat_name: self._resolve_config_path(habitat_path)
                for habitat_name, habitat_path in habitat_map.items()
            },
            "wave_height_vector": self._resolve_config_path(
                maps.get("wave_height_vector")
            ),
            "restricted_area_vector": self._resolve_config_path(
                maps.get("restricted_area_vector")
            ),
            "restricted_area_map": restricted_area_map,
            "spatial_extent": maps.get("spatial_extent"),
        }

    def get_model_params(self) -> Dict[str, Any]:
        """Extracts parameters for ``FisheryModel`` initialisation.

        Returns:
            Dictionary with model constructor parameters.

        Raises:
            ValueError: If no configuration has been loaded.
        """
        self._require_loaded()

        config = self.loaded_config
        agent_names: List[str] = config["agents"]["names"]
        num_archipelago: int = config["agents"]["num_archipelago"]
        num_coastal: int = config["agents"]["num_coastal"]

        species_params = self.get_species_params()

        return {
            "end_of_sim": config["simulation"]["duration_years"] * 365,
            "num_archipelago": num_archipelago,
            "num_coastal": num_coastal,
            "num_trawler": config["agents"]["num_trawler"],
            "verbose": config["simulation"]["verbose"],
            "coupling": config["simulation"]["coupling"],
            "archipelago_names": agent_names[:num_archipelago],
            "coastal_names": agent_names[
                num_archipelago: num_archipelago + num_coastal
            ],
            "trawler_names": agent_names[num_archipelago + num_coastal:],
            "start_date": config["simulation"].get("start_date"),
            "catchability_matrix": species_params["catchability_matrix"],
            "price_matrix": species_params["price_matrix"],
            "species_names": species_params["species_names"],
        }

    def get_output_params(self) -> Dict[str, Any]:
        """Returns the output configuration parameters.

        Returns:
            Dictionary from the ``output`` section of the config.

        Raises:
            ValueError: If no configuration has been loaded.
        """
        self._require_loaded()
        return self.loaded_config["output"]

    def get_metadata(self) -> Dict[str, Any]:
        """Returns the experiment metadata section.

        Returns:
            Dictionary from the ``metadata`` section of the config.

        Raises:
            ValueError: If no configuration has been loaded.
        """
        self._require_loaded()
        return self.loaded_config["metadata"]
    
    def get_port_assignments(self) -> Dict[str, List[int]]:
        """Returns the port assignments for each agent type.

        Returns:
            Dictionary with keys ``archipelago_ports``, ``coastal_ports``,
            and ``trawler_ports``, each mapping to a list of port indices.
        """
        #ConfigLoader._require_loaded(self)
        agents = self.loaded_config["agents"]
        return {
            "archipelago_ports": agents.get("archipelago_ports", []),
            "coastal_ports": agents.get("coastal_ports", []),
            "trawler_ports": agents.get("trawler_ports", []),
        }
    
    def _load_species_flotilla_matrix(
        self,
        csv_path: str,
        species_names: List[str],
        sep: str = ",",
        normalize_price_per_ton: bool = False,
    ) -> np.ndarray:
        """Loads a species × flotilla CSV into a (F, N) numpy array.

        Expected CSV format:
          - First row: header with flotilla names (e.g. archipelago, coastal, trawler)
          - First column: species IDs matching ``species_names`` order.
          - Values: catchability or price.

        The returned array is indexed as ``array[flotilla_index, species_index]``.

        Args:
            normalize_price_per_ton: If True and any value exceeds 1000,
                the matrix is assumed to hold prices in €/tonne and is
                divided by 1000 to convert it to €/kg.
        """
        df = pd.read_csv(csv_path, sep=sep, index_col=0)
        species_ids = [
            s for s in species_names if s in df.index
        ] or species_names

        num_index = pd.to_numeric(df.index.copy())
        if num_index.notna().all():
            try:
                species_ids = [int(s) for s in species_names]
            except ValueError:
                species_ids = [
                    s for s in species_names if s in df.index
                ] or list(species_names)
        df = df.reindex(index=species_ids, fill_value=0.0)
        matrix = df.to_numpy(dtype=np.float64).T

        if normalize_price_per_ton and matrix.max() > 1000.0:
            matrix = matrix / 1000.0

        return matrix 

    def get_species_params(self) -> Dict[str, Any]:
        """Loads and returns species-related parameters.

        Reads the catchability and price CSV paths from the loaded
        config, resolves them, and loads them into numpy arrays.

        Returns:
            Dict with keys ``catchability_matrix`` (F, N), ``price_matrix`` (F, N),
            and ``species_names`` (List[str]).
        """
        maps = self.loaded_config.get("maps", {})
        species_maps = maps.get("species_map", {})
        species_names = list(species_maps.keys())

        species_tables = maps.get("species_tables", {})
        catchability_path = self._resolve_config_path(
            species_tables.get("catchability")
        )
        price_path = self._resolve_config_path(
            species_tables.get("price")
        )

        catchability_matrix = (
            self._load_species_flotilla_matrix(catchability_path, species_names)
            if catchability_path
            else np.zeros((3, len(species_names)), dtype=np.float64)
        )
        price_matrix = (
            self._load_species_flotilla_matrix(
                price_path, species_names, normalize_price_per_ton=True
            )
            if price_path
            else np.ones((3, len(species_names)), dtype=np.float64)
        )

        for f_name, f_idx in [
            ("archipelago", 1),
            ("coastal", 2),
            ("trawler", 3),
        ]:
            print(
                f"[debug] flottille '{f_name}' (idx {f_idx}) "
                f"price (€/kg)  : {np.round(price_matrix[f_idx], 4)}"
            )
            print(
                f"[debug] flottille '{f_name}' (idx {f_idx}) "
                f"catchability  : {np.round(catchability_matrix[f_idx], 6)}"
            )

        return {
            "catchability_matrix": catchability_matrix,
            "price_matrix": price_matrix,
            "species_names": species_names,
        }

    def get_habitat_assignments(self) -> Dict[str, List[str]]:
        """Returns the habitat assignments for each agent type.

        Returns:
            Dictionary with keys ``archipelago_habitats``, ``coastal_habitats``,
            and ``trawler_habitats``, each mapping to a list of habitat names.
        """
        #ConfigLoader._require_loaded(self)
        agents = self.loaded_config["agents"]
        return {
            "archipelago_habitats": agents.get("archipelago_habitats", []),
            "coastal_habitats": agents.get("coastal_habitats", []),
            "trawler_habitats": agents.get("trawler_habitats", []),
        }

    def apply_custom_parameters(self, model: Any) -> None:
        """Applies custom parameter overrides from the config to a model.

        Overrides ``default_config`` module globals and the
        corresponding model attributes where applicable.

        Args:
            model: A ``FisheryModel`` instance to update.

        Raises:
            ValueError: If ``initial_stock_size`` is not a recognised
                option.
        """
        if not self.loaded_config or "parameters" not in self.loaded_config:
            return

        params = self.loaded_config["parameters"]

        fish_dynamics = params.get("fish_dynamics", {})
        if "growth_rate" in fish_dynamics:
            default_config.GROWTH_RATE = fish_dynamics["growth_rate"]

        if "initial_stock_size" in fish_dynamics:
            value = fish_dynamics["initial_stock_size"]
            if value not in self._VALID_STOCK_SIZES:
                raise ValueError(
                    f"Invalid initial_stock_size '{value}'. "
                    f"Allowed values: {sorted(self._VALID_STOCK_SIZES)}"
                )
            default_config.INIT_STOCK_SIZE = value
            model.init_stock_size = value

        eco_params = params.get("economics", {})
        if "fish_price" in eco_params:
            default_config.FISH_PRICE = eco_params["fish_price"]
            model.FISH_PRICE = eco_params["fish_price"]

        weather_params = params.get("weather", {})
        if "bad_weather_probability" in weather_params:
            prob = weather_params["bad_weather_probability"]
            default_config.BAD_WEATHER_PROBABILITY = prob
            model.bad_weather_probability = prob

    def apply_effort_quotas(self):
        if not self.loaded_config or "quotas" not in self.loaded_config:
            return None

        params = self.loaded_config["quotas"]
        effort = params.get("effort")
        if not effort:
            return None

        if isinstance(effort, str):
            df = pd.read_csv(effort, sep=";", index_col=0)
            return df.to_numpy(dtype=np.float64)

        if isinstance(effort, dict):
            return effort

        return None

    def apply_landings_quotas(self) -> Dict:
        if not self.loaded_config or "quotas" not in self.loaded_config:
            return {}

        params = self.loaded_config["quotas"]
        landings = params.get("landings")
        if not landings:
            return {}

        if isinstance(landings, str):
            species_maps = self.loaded_config.get("maps", {}).get("species_map", {})
            species_names = list(species_maps.keys())
            matrix = self._load_species_flotilla_matrix(landings, species_names, sep=";")
            return {
                "archipelagos": matrix[0],
                "coastal": matrix[1],
                "trawler": matrix[2],
            }

        if isinstance(landings, dict):
            return landings

        return {}

    def apply_map_configuration(self) -> None:
        """Applies map sources from the loaded configuration.

        Configures ``ecospace_outputs`` and reloads the spatial
        configuration in ``default_config``.

        Raises:
            ValueError: If no configuration has been loaded.
        """
        if self.loaded_config is None:
            return

        map_params = self.get_map_params()
        print(f"Applying map configuration: {map_params.get('restricted_area_map')}, {map_params.get('restricted_area_vector')}")

        ecospace_outputs.configure_sources(
            topology_map_path=map_params["topology_map"],
            wind_farm_map_path=map_params["wind_farm_map"],
            species_map_paths=map_params["species_map"],
            ports_map_path=map_params["ports_map"],
            habitat_map_path=map_params["habitat_map"],  # Not used in current model
        )
        spatial_utils.reload_spatial_configuration(
            topology_map_path=map_params["topology_map"],
            windfarm_map_path=map_params["wind_farm_map"],
            apply_windfarm=map_params["wind_farm_map"] is not None
        )

        load_ports_map(
            ports_map_path=map_params["ports_map"]
        )

        ecospace_outputs.load_habitat_map(
            habitat_map_path=map_params["habitat_map"]
        )
        read_wave_height_vector(
            wave_height_vector_path=map_params["wave_height_vector"]
        )
        load_ocean_current_map(
            file_path=map_params.get("ocean_current_map")
        )
        load_restricted_area_map(
            restricted_area_map_path=map_params.get("restricted_area_map"),
            spatial_extent=map_params.get("spatial_extent"),
        )
        load_restricted_area_vector(
            restricted_area_vector_path=map_params.get("restricted_area_vector")
        )

    def save_config(self, output_path: str) -> None:
        """Saves the current configuration to a JSON file.

        Adds an ``execution`` block with a timestamp for reproducibility.

        Args:
            output_path: Destination file path.

        Raises:
            ValueError: If no configuration has been loaded.
        """
        self._require_loaded()

        config_copy = self.loaded_config.copy()
        config_copy["execution"] = {
            "timestamp": datetime.now().isoformat(),
            "config_loader_version": "1.0",
        }

        with open(output_path, "w") as f:
            json.dump(config_copy, f, indent=2)

    def _require_loaded(self) -> None:
        """Raises ``ValueError`` if no configuration has been loaded.

        Raises:
            ValueError: If ``loaded_config`` is None.
        """
        if self.loaded_config is None:
            raise ValueError(
                "No configuration loaded. Call load() first."
            )


def load_config(config_path: str) -> ConfigLoader:
    """Convenience function to load a configuration from a file.

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        A ``ConfigLoader`` instance with the configuration already loaded.
    """
    loader = ConfigLoader()
    loader.load(config_path)
    return loader
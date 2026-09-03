from typing import Any, Optional, Tuple, Dict, List
import json
import os
import time
from time import sleep
import csv

import numpy as np

def _read_config_snapshot(
        json_path: str,
) -> Optional[Tuple[Dict[str, str], int, Optional[Dict[str, int]]]]:
    """Reads config.json
    
    Args:
        json_path: Path to the coupling JSON configuration file.

    Returns:
        ''(species_maps, step, num_agents)'' if successful, else None.
        Any exceptions, decide to wait. ``num_agents`` may be None if not
        present in the config (backward compatibility).
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            species_maps = config["maps"]["species_map"]
            step = int(config["simulation"]["step"])
            # New dynamic fleet counts: agents.num_agents
            num_agents = config.get("agents", {}).get("num_agents", None)
            if num_agents is not None:
                # Validate and normalize to int
                num_agents = {
                    "num_archipelago": int(num_agents.get("num_archipelago", 0)),
                    "num_coastal": int(num_agents.get("num_coastal", 0)),
                    "num_trawler": int(num_agents.get("num_trawler", 0)),
                }
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
        json.JSONDecodeError, 
        KeyError, 
        TypeError, 
        ValueError
        ) as e:
        return None
    return species_maps, step, num_agents

def wait_for_coupling_update(
    self,
    json_path: str = "configs_json/config.json",
    poll_interval: float = 0.5,
    timeout: Optional[float] = 350.0,
) -> Tuple[Any, Any, Optional[Dict[str, int]]]:
    """Blocks until a NEW coupling sequence is available.

        Synchronizes by the step number in the JSON config. The first call (bootstrap) consumes the existing file immediately, even if it was written before our start.
        This prevents deadlock when Ecospace writes steps 1 and 2 before FIBE has armed its listening loop. 
        Subsequent calls only accept the file if ``simulation.step > last consumed step``.:

        Args:
            json_path: Path to the JSON config monitored.
            poll_interval: Polling interval in seconds.
            timeout: Maximum time to wait in seconds. ``None`` waits
                indefinitely. A ``TimeoutError`` is raised when the
                deadline expires without any new sequence.

        Returns:
            A tuple ``(species_maps, coupling_step, num_agents)`` from the config.
            ``num_agents`` is ``None`` if not present.

        Raises:
            TimeoutError: If no new sequence appears within ``timeout``.
        """
    last_mtime = None
    deadline = None if timeout is None else time.monotonic() + timeout
    warned_missing = False
    warned_stale = False
    # Étape 4 - Pour ne pas spammer "missing or invalid" à chaque poll (0.5s)
    # on ne log qu'après 2s d'attente continue.
    first_missing_time = None

    while True:
        try:
            mtime = os.path.getmtime(json_path)
        except OSError:
            mtime = None

        # Étape 1 - Fix atomicité : on ne met à jour last_mtime qu'après avoir
        # vérifié que le JSON est lisible. Sinon un Move-Item en cours donne
        # PermissionError/JSONDecodeError → snapshot=None, mais on avait déjà
        # marqué ce mtime comme "vu" → la prochaine écriture valide à la même
        # seconde (NTFS 1s) est ignorée comme mtime==last_mtime → boucle
        # "missing or invalid" + "already consumed" vue dans les logs.
        if mtime is not None and mtime != last_mtime:
            snapshot = _read_config_snapshot(json_path)

            if snapshot is not None:
                # Maintenant seulement, on valide ce mtime
                last_mtime = mtime
                species_maps, step, num_agents = snapshot
                last_consumed = getattr(
                    self, "_coupling_step_consumed", None
                )

                # Étape 1 - Fix bootstrap stale + restart : si Ecospace redémarre à 1
                # alors qu'on attendait >60, on détecte step < last_consumed et on reset.
                is_restart = (
                    last_consumed is not None
                    and step < last_consumed
                    and (last_consumed - step) > 5
                )
                if last_consumed is None or step > last_consumed or is_restart:
                    if is_restart and self.verbose:
                        print(
                            f"Coupling restart detected: last {last_consumed} -> new {step}, resetting"
                        )
                    self._coupling_step_consumed = step
                    if self.verbose:
                        print(
                            f"Coupling config accepted:"
                            f" simulation.step={step}"
                            f" (previously consumed={last_consumed})"
                            f" num_agents={num_agents}"
                        )
                    return species_maps, step, num_agents

                if self.verbose and not warned_stale:
                    warned_stale = True
                    print(
                        f"Coupling step {step} already consumed"
                        f" (last: {last_consumed}). Waiting for new step..."
                    )
        else:
            # Étape 4 - Log allégé : on attend 2s avant de spammer, et on ne log qu'une fois par cycle
            if self.verbose:
                if first_missing_time is None:
                    first_missing_time = time.monotonic()
                if not warned_missing and (time.monotonic() - first_missing_time) > 2.0:
                    warned_missing = True
                    print(
                        f"Coupling config missing or invalid at {json_path}. "
                        f"Waiting for valid config... (step {getattr(self, '_coupling_step_consumed', None)})"
                    )
        # Si on a un snapshot valide, on reset le timer missing
        if 'snapshot' in locals() and snapshot is not None:
            first_missing_time = None
            warned_missing = False

        if deadline is not None and time.monotonic() > deadline:
            expected = (
                f"> {last_consumed}"
                if last_consumed is not None
                else "any valid config (bootstrap)"
            )    
            raise TimeoutError(
                f"Coupling config '{json_path}' was not updated"
                f" within {timeout} seconds (model step"
                f" {self.current_step}, expecting coupling step"
                f" {expected}). Is the Ecospace side running?"
            )
        sleep(poll_interval)

def read_csv_biomass(
    self,
    json_path: str = "configs_json/config.json",
) -> Tuple[Dict[str, str], int]:
    """Reads the JSON configuration to retrieve species map file paths.

    This method loads the configuration file to extract species maps
    and the simulation time step, without running the simulation.

    Args:
        json_path: Path to the coupling JSON configuration file.

    Returns:
        A tuple containing:
            - A dictionary mapping species IDs to their CSV file paths.
            - The simulation time step.
    """
    with open(json_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
        species_maps = config["maps"]["species_map"]
        step = config["simulation"]["step"]

    return species_maps, step

def update_biomass(self, species_maps: Dict[str, str]) -> Dict[Tuple[int, int], float]:
    """Updates fish stocks by reading biomass CSV files.

    Iterates through specified CSV files, cleans data (handling empty or 
    non-numeric values), and aggregates biomass per grid cell (x, y).

    Args:
        species_maps: Dictionary associating species IDs with their CSV file paths.

    Returns:
        A dictionary where keys are tuples (x, y) representing coordinates,
        and values are the summed float biomass for that cell.
    """
    new_fish_stocks: Dict[Tuple[int, int], float] = {}

    for species_id, path in species_maps.items():
        with open(path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=',')
            all_rows: List[List[str]] = []
            
            for row in reader:
                new_row: List[float] = []
                for cell in row:
                    cell = cell.strip()
                    if not cell:
                        new_row.append(0.0)
                    else:
                        try:
                            new_row.append(float(cell))
                        except ValueError:
                            print(f"Warning: Non-numeric value '{cell}' in file {path}, treating as 0")
                            new_row.append(0.0)
                all_rows.append(new_row)

            # Skip header and first column (assumed to be metadata)
            # Take rows starting from index 2 and ignore the first column (index 0)
            data_rows = [row[1:] for row in all_rows[2:]]

            for x, row in enumerate(data_rows):
                for y, cell_value in enumerate(row):
                    # Option A: Sum biomass of all species per cell
                    current_value = new_fish_stocks.get((x, y), 0.0)
                    new_fish_stocks[(x, y)] = current_value + cell_value * 1000.0

                    # Option B (commented): Keep data separated by species
                    # if (x, y) not in new_fish_stocks:
                    #     new_fish_stocks[(x, y)] = {}
                    # new_fish_stocks[(x, y)][species_id] = cell_value

    return new_fish_stocks


def update_biomass_species(
    self, species_maps: Dict[str, str], species_names: List[str]
) -> np.ndarray:
    """Reads biomass CSV files and returns a 3D array (H, W, N).

    Replaces the old summed approach: each species CSV is loaded into
    a 2D grid, then all are stacked along axis=2.

    Args:
        species_maps: Dict mapping species ID → CSV file path.
        species_names: Ordered list of species IDs matching the
            model's ``species_names``.

    Returns:
        ``np.ndarray`` of shape ``(H, W, N)``.
    """
    species_data: List[np.ndarray] = []
    for species_id in species_names:
        path = species_maps.get(species_id, "")
        if not path or not os.path.exists(path):
            species_data.append(
                np.zeros((self.grid.height, self.grid.width), dtype=np.float64)
            )
            continue
        grid = np.genfromtxt(path, delimiter=",", skip_header=2)[:, 1:]
        # Replace NaN with 0
        grid = np.nan_to_num(grid, nan=0.0)
        grid = grid * 1000.0
        species_data.append(grid)

    if not species_data:
        return np.zeros((self.grid.height, self.grid.width, 1), dtype=np.float64)

    return np.stack(species_data, axis=2)

def update_num_agents(self, num_agents: Dict[str, int]) -> Dict[str, int]:
    """Updates the number of agents based on the provided configuration.

    Args:
        num_agents: Dictionary containing the number of each agent type.

    Returns:
        A dictionary with updated agent counts.
    """
    updated_agents = {
        "num_archipelago": int(num_agents.get("num_archipelago", 0)),
        "num_coastal": int(num_agents.get("num_coastal", 0)),
        "num_trawler": int(num_agents.get("num_trawler", 0))
    }
    return updated_agents


def read_desired_num_agents(
    json_path: str = "configs_json/config.json",
) -> Optional[Dict[str, int]]:
    """Non-blocking read of desired fleet sizes.

    Used when ``coupling`` is False or for testing without Ecospace.

    Args:
        json_path: Path to the JSON config.

    Returns:
        Dict with ``num_archipelago``, ``num_coastal``, ``num_trawler`` or
        None if file missing / invalid / key absent.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            num_agents = config.get("agents", {}).get("num_agents", None)
            if num_agents is None:
                return None
            return {
                "num_archipelago": int(num_agents.get("num_archipelago", 0)),
                "num_coastal": int(num_agents.get("num_coastal", 0)),
                "num_trawler": int(num_agents.get("num_trawler", 0)),
            }
    except (FileNotFoundError, PermissionError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
from typing import Any, Optional, Tuple, Dict, List
import json
import os
import time
from time import sleep
import csv

import numpy as np

def _read_config_snapshot(
        json_path: str,
) -> Optional[Tuple[Dict[str, str], int]]:
    """Reads config.json
    
    Args:
        json_path: Path to the coupling JSON configuration file.

    Returns:
        ''(species_maps, step)'' if successful, else None.
        Any exceptions, decide to wait
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            species_maps = config["maps"]["species_map"]
            step = int(config["simulation"]["step"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        return None
    return species_maps, step

def wait_for_coupling_updates(
    self,
    json_path: str = "configs_json/config.json",
    poll_interval: float = 0.5,
    timeout: Optional[float] = 60.0,
) -> Tuple[Any, Any]:
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
            A tuple ``(species_maps, coupling_step)`` from the config.

        Raises:
            TimeoutError: If no new sequence appears within ``timeout``.
        """
    deadline = None if timeout is None else time.monotonic() + timeout
    warned_missing = False
    warned_stale = False

    while True:
        snapshot = _read_config_snapshot(json_path)

        if snapshot is not None:
            species_maps, step = snapshot
            last_consumed = getattr(
                self, "_coupling_step_consumed", None
            )

            if last_consumed is None or step > last_consumed:
                self._coupling_step_consumed = step
                if self.verbose:
                    print(
                        f"Coupling config accepted:"
                        f" simulation.step={step}"
                        f" (previously consumed={last_consumed})"
                    )
                return species_maps, step

            if self.verbose and not warned_stale:
                warned_stale = True
                print(
                    f"Coupling step {step} already consumed"
                    f" (last: {last_consumed}). Waiting for new step..."
                )
        else:
            if self.verbose and not warned_missing:
                warned_missing = True
                print(
                    f"Coupling config missing or invalid at {json_path}. "
                    f"Waiting for valid config..."
                )

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
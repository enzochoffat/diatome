from typing import Any, Tuple, Dict, List
import json
import os
from time import sleep
import csv

import numpy as np

def wait_for_coupling_update(
        self,
        json_path: str = "configs_json/config.json",
        poll_interval: float = 0.5,
    ) -> Tuple[Any, Any]:
        """Blocks until the coupling config file is updated.

        Polls ``json_path`` for modification-time changes and returns
        the updated biomass maps once a change is detected.

        Args:
            json_path: Path to the JSON config monitored for changes.
            poll_interval: Polling interval in seconds.

        Returns:
            A tuple ``(species_maps, current_step_val)`` from the
            updated Ecospace CSV.
        """
        species_maps, last_step = read_csv_biomass(self)
        current_step_val = last_step

        last_modified_time = 0.0
        current_modified_time = 0.0

        if os.path.exists(json_path):
            last_modified_time = os.path.getmtime(json_path)
            current_modified_time = last_modified_time

        while (
            current_modified_time <= last_modified_time
            and self.current_step != 28
        ):
            sleep(poll_interval)
            if os.path.exists(json_path):
                current_modified_time = os.path.getmtime(json_path)
                if current_modified_time > last_modified_time:
                    species_maps, current_step_val = (
                        read_csv_biomass(self)
                    )
                    if self.verbose:
                        print(
                            f"File {json_path} updated. Proceeding with"
                            f" biomass update for step {current_step_val}."
                        )
            elif self.verbose:
                print(
                    f"File {json_path} not found."
                    " Waiting for the file to be created..."
                )

        return species_maps, current_step_val

def read_csv_biomass(self) -> Tuple[Dict[str, str], int]:
    """Reads the JSON configuration to retrieve species map file paths.

    This method loads the configuration file to extract species maps
    and the simulation time step, without running the simulation.

    Returns:
        A tuple containing:
            - A dictionary mapping species IDs to their CSV file paths.
            - The simulation time step.
    """
    json_path = "configs_json/config.json"
    
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
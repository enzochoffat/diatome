import csv
import json
from typing import Any, Dict, List, Tuple


class Coupling:
    """Class managing the coupling between the model and biomass data."""

    def __init__(self, model: Any) -> None:
        """Initializes the Coupling instance.

        Args:
            model: The model object associated with this coupling.
        """
        self.model = model

    def read_csv_biomass(self) -> Tuple[Dict[str, str], int]:
        """Reads the JSON configuration to retrieve species map file paths.

        This method loads the configuration file to extract species maps
        and the simulation time step, without running the simulation.

        Returns:
            A tuple containing:
                - A dictionary mapping species IDs to their CSV file paths.
                - The simulation time step.
        """
        json_path = "configs/config.json"
        
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
                        new_fish_stocks[(x, y)] = current_value + cell_value

                        # Option B (commented): Keep data separated by species
                        # if (x, y) not in new_fish_stocks:
                        #     new_fish_stocks[(x, y)] = {}
                        # new_fish_stocks[(x, y)][species_id] = cell_value

        return new_fish_stocks
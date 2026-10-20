import os
import numpy as np
import datetime
import pandas as pd


def export_data(
    self,
    filename_prefix: str = "fibe_output",
    directory: str = "./results/",
) -> None:
    """Exports collected data to timestamped CSV files.

    Writes model-level, agent-level, and yearly summary data to a
    subdirectory of ``directory`` named after the current timestamp.

    Args:
        filename_prefix: Prefix for all output filenames.
        directory: Root output directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = os.path.join(directory, timestamp)
    os.makedirs(export_dir, exist_ok=True)

    model_df = self.datacollector.get_model_vars_dataframe()
    model_path = os.path.join(
        export_dir, f"{filename_prefix}_model_{timestamp}.csv"
    )
    model_df.to_csv(model_path, index=False)

    agent_df = self.datacollector.get_agent_vars_dataframe()
    agent_path = os.path.join(
        export_dir, f"{filename_prefix}_agent_{timestamp}.csv"
    )
    agent_df.to_csv(agent_path, index=False)

    if self.yearly_data:
        yearly_df = pd.DataFrame(self.yearly_data)
        yearly_path = os.path.join(
            export_dir, f"{filename_prefix}_yearly_{timestamp}.csv"
        )
        yearly_df.to_csv(yearly_path, index=False)
        self.save_output_map(
            export_dir, f"{filename_prefix}_stock_{timestamp}.csv"
        )


    if self.verbose:
        print(f"\nAll data exported with timestamp: {timestamp}")

def get_output_map(self) -> np.ndarray:
    """Returns a 2-D array of current fish stocks for visualisation.

    Returns:
        Integer NumPy array of shape ``(height, width)``.
    """
    stock_map = np.zeros(
        (self.grid.height, self.grid.width), dtype=int
    )
    for (x_coord, y_coord), patch in self.patches.items():
        stock_map[x_coord, y_coord] = int(patch["fish_stock"])
    return stock_map

def save_output_map(self, directory: str, filename: str) -> None:
    """Saves the current fish-stock map to a CSV file.

    Args:
        directory: Target directory (created if it does not exist).
        filename: Output filename.
    """
    stock_map = self.get_output_map()
    os.makedirs(directory, exist_ok=True)
    np.savetxt(
        os.path.join(directory, filename),
        stock_map, fmt="%d", delimiter=",",
    )
"""Module for preprocessing and handling various data sources."""

import os
import pandas as pd

CACHE_DIR = "cache"
POP_GRID_URL = "https://www.zensus2022.de/static/Zensus_Veroeffentlichung/Zensus2022_Bevoelkerungszahl.zip"  # Datenlizenz Deutschland – Namensnennung – Version 2.0


def get_pop_grid() -> pd.DataFrame:
    """Get the population grid data.

    Parameters:
        None

    Returns:
        pd.DataFrame: The population grid data.

    Raises:
        None
    """

    # Build the file path
    file_path = os.path.join(CACHE_DIR, "Zensus2022_Bevoelkerungszahl_100m-Gitter.csv")

    # Check if the file exists, otherwise download it
    if not os.path.exists(file_path):
        pass


def dont_know_what():
    pass

"""A module for working with German administrative areas.

Every administrative area in Germany is identified by a unique regional key (Regionalschlüssel).
While its usual form is a 12-digit key capable of identifying all administrative levels down to single villages,
a 5-digit key is often used to identify counties and county-level cities (Kreise and kreisfreie Städte) and
a 2-digit key to identify the Bundesländer (states).
More information: https://de.wikipedia.org/wiki/Regionalschl%C3%BCssel

Classes:
    

Functions:
    
"""

import importlib.resources as res
import lzma
import warnings
import pyogrio as pgr
import geopandas as gpd
import pandas as pd
from typing import Union


class Area:
    """An Area object representing a German administrative area.

    Attributes:
        regkey (str): The regional key (Regionalschlüssel) identifying the area.
        level (str): The administrative level of the area (staat, land, kreis, gemeinde).
        full_name (str): The official name of the area (including the title).
        geo_name (str): The geographical name of the area.
        title (str): The title of the area.
        geometry (shapely.geometry): The geometry of the area.
        population (int): The population of the area.

    Methods:
    """

    __slots__ = (
        "regkey",
        "level",
        "full_name",
        "geo_name",
        "title",
        "geometry",
        "population",
    )

    def __init__(self, identifier: str) -> None:
        """Initialize an Area object.

        Parameters:
            identifier (str): A valid regkey value or area name.

        Returns:
            None

        Raises:
            None
        """

        # infer a regkey from the given identifier
        regkey = self.infer_regkey(identifier)

        # get the data for the specified area
        area = get_area(regkey)

        # set the regkey, name, population and level attributes
        self.regkey = regkey
        self.level = area.level
        self.full_name = area.full_name
        self.geo_name = area.geo_name
        self.title = area.title
        self.geometry = area.geometry
        self.population = area.population

    def __str__(self) -> str:
        """Return information about the Area object."""
        return f"{self.full_name} ({self.regkey})"

    def infer_regkey(self, input: str) -> str:
        """Try to infer a valid regkey from input.

        Parameters:
            input (str): The input to be inferred.

        Returns:
            regkey (str): The inferred regkey.

        Raises:
            TypeError: If the input is not a RegKey or a name string.
        """

        # If the input is a regkey, validate and return it as a full 12-digit regkey
        # by padding with trailing zeros if necessary
        if isinstance(input, str) and self.validate_regkey(input):
            return f"{input:0<12}"

        # If the input could be an area name instead, try to convert it to a regkey
        if isinstance(input, str):
            return self.name_to_regkey(input)

        # If none of the above apply, raise an error
        raise TypeError("No regkey could be inferred from input.")

    def validate_regkey(regkey: str) -> bool:
        """Check if a given RegKey is valid.

        Parameters:
            regkey (str): The RegKey to be checked.

        Returns:
            valid (bool): True if the RegKey is valid, False otherwise.

        Raises:
            TypeError: If the RegKey is not a string.
            ValueError: If the RegKey is not either 2, 5 or 12 digits long.
            ValueError: If the first two digits of the RegKey are not between 01 and 16.
            ValueError: If the RegKey is not a valid RegKey.
        """

        # Check if the RegKey is a string
        if not isinstance(regkey, str):
            raise TypeError("RegKey must be a string.")

        # Edge case: DG (Deutschland Gesamt) is a valid RegKey
        if regkey in ["DG", "DG0000000000"]:
            return True

        # If the regkey contains characters other than digits, try to resolve as a RegKey name.
        if not regkey.isdigit():
            return False

        # Check if the RegKey is either 2, 5 or 12 digits long
        if not len(regkey) in [2, 5, 12]:
            raise ValueError("RegKey must be either 2, 5 or 12 digits long.")

        # Check if the first two digits are within the valid range of 01-16.
        # The first two digits of a RegKey identify the Bundesland.
        if not int(regkey[:2]) in range(1, 17):
            raise ValueError(
                "First two digits of the RegKey must be between 01 and 16."
            )

        # Check if the RegKey is valid by looking it up in the list of RegKeys
        # Get the list of RegKeys
        regkey_list = get_regkeys()

        # Prepare the RegKey for lookup by adding trailing zeros to keys shorter than 12 digits
        regkey = f"{regkey:0<12}"

        # Check if the RegKey is in the list
        if regkey in regkey_list:
            return True
        else:
            raise ValueError("RegKey is not a valid RegKey.")

    def name_to_regkey(name: str) -> str:
        """Get the RegKey of an administrative area from its name.

        Parameters:
            name (str): A name intended to resolve to a RegKey.

        Returns:
            regkey (str): The RegKey of the area with the given name.

        Raises:
            ValueError: If no RegKey is found for the given name.
            ValueError: If multiple RegKeys are found for the given name.
        """

        # Get the list of all area names
        area_names = get_area_names()

        matches = area_names[area_names.str.contains(name, case=False)]

        # if no regkeys are found, raise an error
        if matches.empty:
            raise ValueError("No RegKey found for given name.")

        # if multiple regkeys are found, raise an error
        if len(matches) > 1:
            raise ValueError(
                f"Multiple RegKeys found for given name: \n{matches.to_string(header=False)}."
            )

        # if only one regkey is found, return it
        regkey = matches.index[0]

        return regkey


def get_regkeys() -> list:
    """Get a list of all valid German Regionalschlüssel (regkeys).

    Data source is an aggregated list of all German administrative areas.
    For more information, see: sources/admin_areas.

    Parameters:
        None

    Returns:
        regkeys (list): A list containing all valid German Regionalschlüssel.

    Raises:
        None
    """

    # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
    # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

    # compressed admin_areas GeoPackage in the sources subfolder
    path = res.files(__package__).joinpath("sources", "admin_areas.gpkg.xz")

    # Decompress with lzma, then access with pyogrio.
    # Output will be a simple DataFrame because no Geometries are read
    with lzma.open(path, "rb") as archive:
        regkeys = pgr.read_dataframe(
            archive, layer="admin_areas", columns=["regkey"], read_geometry=False
        )

    # Transform the DataFrame to a list
    regkeys = regkeys["regkey"].tolist()

    return regkeys


def get_area_names() -> pd.DataFrame:
    """Get a DataFrame containing the names of all German administrative areas.

    Data source is an aggregated list of all German administrative areas.
    For more information, see: sources/admin_areas.

    Parameters:
        None

    Returns:
        names (pd.DataFrame): A DataFrame containing name and regkey for all areas.

    Raises:
        None
    """

    # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
    # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

    # compressed admin_areas GeoPackage in the sources subfolder
    path = res.files(__package__).joinpath("sources", "admin_areas.gpkg.xz")

    # Decompress with lzma, then access with pyogrio.
    # Output will be a simple DataFrame because no Geometries are read
    with lzma.open(path, "rb") as archive:
        names = pgr.read_dataframe(
            archive,
            layer="admin_areas",
            columns=["regkey", "full_name"],
            read_geometry=False,
        )

    names = names.set_index("regkey")

    return names["full_name"]


def get_areas() -> gpd.GeoDataFrame:
    """Get information about all German administrative areas.

    Data source is an aggregated list of all German administrative areas.
    For more information, see: sources/admin_areas.

    Parameters:
        None

    Returns:
        areas (gpd.GeoDataFrame): A GeoDataFrame containing all German administrative areas.

    Raises:
        None
    """

    # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
    # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

    # compressed admin_areas GeoPackage in the sources subfolder
    path = res.files(__package__).joinpath("sources", "admin_areas.gpkg.xz")

    # Decompress with lzma, then access with geopandas.
    # Output is a GeoDataFrame
    with lzma.open(path, "rb") as archive:
        areas = gpd.read_file(archive, layer="admin_areas")

    # Set index to regkey to allow for quick filtering
    areas = areas.set_index("regkey")

    return areas


def get_area(regkey: str) -> pd.Series:
    """Get information about a German administrative area.

    Data source is an aggregated list of all German administrative areas.
    For more information, see: sources/admin_areas.

    Parameters:
        regkey (str): The regkey of the area to be retrieved.

    Returns:
        area (pd.Series): A Series containing information about the requested area.

    Raises:
        None
    """

    # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
    # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

    # compressed admin_areas GeoPackage in the sources subfolder
    path = res.files(__package__).joinpath("sources", "admin_areas.gpkg.xz")

    # Decompress with lzma, then access with pyogrio.
    with lzma.open(path, "rb") as archive:
        area = gpd.read_file(archive, layer="admin_areas", where=f"regkey = '{regkey}'")

    # Check if area_data is a GeoDataFrame (= multiple entries for the regkey)
    if type(area) == gpd.GeoDataFrame:
        # Sort entries by level value in the order of "bundesland", "kreis", "gemeinde"
        area = area.sort_values(
            "level", key=lambda x: x.map({"bundesland": 1, "kreis": 2, "gemeinde": 3})
        )

        # Return the entry with the highest level value as a Series
        area = area.iloc[0]

    return area

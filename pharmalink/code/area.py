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
import zipfile as zip
import pandas as pd
from typing import Union


class Area:
    """An Area object representing a German administrative area.

    Attributes:
        regkey (str): The regional key (Regionalschlüssel) identifying the area.
        name (str): The name of the area.
        population (int): The population of the area.
        level (str): The administrative level of the area.

    Methods:
    """

    __slots__ = ("_regkey", "_name", "_population", "_level")

    def __init__(self, identifier: str) -> None:
        """Initialize a Area object.

        Parameters:
            identifier (str): A valid regkey value or area name.

        Returns:
            None

        Raises:
            None
        """

        # try to infer a regkey from the input
        regkey = infer_regkey(identifier)

        # get the data for the specified area
        area_data = get_area(regkey)

        # set the regkey, name, population and level attributes
        self._regkey = regkey
        self._name = area_data["name"]
        self._population = area_data["population"]
        self._level = area_data["level"]

    def __str__(self) -> str:
        """Return information about the Area object."""
        return f"{self.name} ({self.regkey})"

    def __repr__(self) -> str:
        """Return all information about the Area object."""
        return f"Area object for {self.name} ({self.regkey}). Population: {self.population}"

    def to_dict(self) -> dict:
        """Return a dictionary representation of the Area object."""
        return {"regkey": self.regkey, "name": self.name, "population": self.population}

    @property
    def regkey(self):
        """Value of the regional key (Regionalschlüssel)."""
        return self._regkey

    @regkey.setter
    def regkey(self, regkey: str) -> None:
        """Set the regkey value."""

        # try to infer a regkey from the input
        new_regkey = infer_regkey(regkey)

        self._regkey = new_regkey

        # get the list of regkeys and the entry for the given regkey
        area_data = get_area()
        entry = area_data.loc[new_regkey]

        # set the name, population and level attributes
        self._name = entry["name"]
        self._population = entry["population"]
        self._level = entry["level"]

    @regkey.deleter
    def regkey(self) -> None:
        """Protect regkey from being deleted and warn user."""
        raise AttributeError(
            "Area.regkey value must not be deleted, change it instead."
        )

    @property
    def name(self):
        """Name of the area defined by regkey."""
        return self._name

    @name.setter
    def name(self, value) -> None:
        """Protect the name of the regkey from being changed."""
        raise AttributeError(
            f'Area.name cannot be changed to "{value}", change value of regkey instead.'
        )

    @name.deleter
    def name(self) -> None:
        """Protect name from being deleted and warn user."""
        raise AttributeError(
            "Area.name must not be deleted, change value of regkey instead."
        )

    @property
    def population(self):
        """Population size of the area defined by regkey."""
        return self._population

    @population.setter
    def population(self, value) -> None:
        """Protect the population of the regkey from being changed."""
        raise AttributeError(
            f'Area.population cannot be changed to "{value}", change value of regkey instead.'
        )

    @population.deleter
    def population(self) -> None:
        """Protect population from being deleted and warn user."""
        raise AttributeError(
            "Area.population must not be deleted, change value of regkey instead."
        )

    @property
    def level(self):
        """Administrative level of the area defined by regkey."""
        return self._level

    @level.setter
    def level(self, value) -> None:
        """Protect the level of the regkey from being changed."""
        raise AttributeError(
            f'Area.level cannot be changed to "{value}", change value of regkey instead.'
        )

    @level.deleter
    def level(self) -> None:
        """Protect level from being deleted and warn user."""
        raise AttributeError(
            "Area.level must not be deleted, change value of regkey instead."
        )


def get_regkey_list() -> list:
    """Read the list of RegKeys from a dedicated file.

    Data source is an aggregated list of all German administrative areas based on
    Zensus 2022 data. For more information, see: Quellen/bevoelkerung.

    Parameters:
        None

    Returns:
        regkey_list (list): A DataFrame containing the Areas.

    Raises:
        None
    """

    # Read the list of Areas from the file
    path = res.files(__package__).joinpath("zensus2022-files.zip")

    with res.as_file(path) as zipfile:
        with zip.ZipFile(zipfile, mode="r") as archive:
            with archive.open(
                "zensus2022-files/Zensus2022_Bevoelkerungszahl_regkey.csv"
            ) as csvfile:
                regkey_list = pd.read_csv(
                    csvfile,
                    sep=";",
                    index_col=False,
                    header=0,
                    dtype={
                        "regkey": "str",  # String because of leading zeros
                    },
                    usecols=["regkey"],
                )

    # Return a simple list of all regkeys in the file
    return list(regkey_list["regkey"])


def get_area(regkey: str) -> pd.Series:
    """Read the list of Areas and their data from a dedicated file.

    Data source is an aggregated list of all German administrative areas based on
    Zensus 2022 data. For more information, see: Quellen/bevoelkerung.

    Parameters:
        None

    Returns:
        regkey_list (pd.DataFrame): A DataFrame containing the Areas.

    Raises:
        None
    """

    # Read the list of Areas from the file
    path = res.files(__package__).joinpath("zensus2022-files.zip")

    with res.as_file(path) as zipfile:
        with zip.ZipFile(zipfile, mode="r") as archive:
            with archive.open(
                "zensus2022-files/Zensus2022_Bevoelkerungszahl_regkey.csv"
            ) as csvfile:
                all_data = pd.read_csv(
                    csvfile,
                    sep=";",
                    index_col=0,
                    dtype={
                        "regkey": "str",  # String because of leading zeros
                        "name": "str",
                        "population": "int64",
                        "level": "str",
                    },
                )

    area_data = all_data.loc[regkey]

    # Check if area_data is a DataFrame (= multiple entries for the regkey)
    if type(area_data) == pd.DataFrame:
        # Sort entries by level value in the order of "bundesland", "kreis", "gemeinde"
        area_data = area_data.sort_values(
            "level", key=lambda x: x.map({"bundesland": 1, "kreis": 2, "gemeinde": 3})
        )

        # Return the entry with the highest level value as a Series
        area_data = area_data.iloc[0]

    return area_data


def get_all_areas() -> pd.DataFrame:
    """Read the list of Areas from a dedicated file.

    Data source is an aggregated list of all German administrative areas based on
    Zensus 2022 data. For more information, see: Quellen/bevoelkerung.

    Parameters:
        None

    Returns:
        areas (pd.DataFrame): A DataFrame containing the Areas.

    Raises:
        None
    """

    # Read the list of Areas from the file
    path = res.files(__package__).joinpath("zensus2022-files.zip")

    with res.as_file(path) as zipfile:
        with zip.ZipFile(zipfile, mode="r") as archive:
            with archive.open(
                "zensus2022-files/Zensus2022_Bevoelkerungszahl_regkey.csv"
            ) as csvfile:
                areas = pd.read_csv(
                    csvfile,
                    sep=";",
                    index_col=0,
                    dtype={
                        "regkey": "str",  # String because of leading zeros
                        "name": "str",
                        "population": "int64",
                        "level": "str",
                    },
                )

    return areas


def infer_regkey(input: Union[Area, str]) -> str:
    """Try to infer a valid regkey from input.

    Parameters:
        input (RegKey or str): The input to be inferred.

    Returns:
        regkey (str): The inferred regkey.

    Raises:
        TypeError: If the input is not a RegKey or a string.
    """

    # If the input is a RegKey Object, return its regkey value
    if isinstance(input, Area):
        return input.regkey

    # If the input is a regkey, validate and return it as a full 12-digit regkey
    # by padding with trailing zeros if necessary
    if isinstance(input, str) and validate_regkey(input):
        return f"{input:0<12}"

    # If the input could be a name, try to convert it to a regkey and return it
    if isinstance(input, str):
        return name_to_regkey(input)

    # If none of the above apply, raise an error
    raise TypeError("No regkey could be inferred from input.")


def validate_regkey(regkey: str) -> bool:
    """Check if a RegKey is valid.

    Parameters:
        regkey (str): The RegKey to be checked.

    Returns:
        valid (bool): True if the RegKey is valid, False otherwise.

    Raises:
        TypeError: If the RegKey is not a string.
        ValueError: If the RegKey is not at least 5 digits long.
        ValueError: If the first two digits of the RegKey are not between 01 and 16.
        ValueError: If the RegKey contains characters other than digits and is not a valid RegKey name.
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
        try:
            regkey = name_to_regkey(regkey)
        except ValueError as error:
            raise error

    # Check if the RegKey is either 2, 5 or 12 digits long
    if not len(regkey) in [2, 5, 12]:
        raise ValueError("RegKey must be either 2, 5 or 12 digits long.")

    # Check if the first two digits are within the valid range of 01-16.
    # The first two digits of a RegKey identify the Bundesland.
    if not 1 <= int(regkey[:2]) <= 16:
        raise ValueError("First two digits of the RegKey must be between 01 and 16.")

    # Check if the RegKey is valid by looking it up in the list of RegKeys
    # Get the list of RegKeys
    regkey_list = get_regkey_list()

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

    # Get the list of RegKeys
    regkey_list = get_regkey_list()

    # get the regkeys of all areas which contain the given name
    regkeys = regkey_list[regkey_list.name.str.contains(name)].index.tolist()

    # if no regkeys are found, raise an error
    if not regkeys:
        raise ValueError("No RegKey found for given name.")

    # if multiple regkeys are found, raise an error
    if len(regkeys) > 1:
        output = []
        # get the name for each regkey and raise an error with all possible names
        for regkey in regkeys:
            name = regkey_list.loc[regkey, "name"]
            output.append(f"{name} ({regkey})")

        raise ValueError(
            f"Multiple RegKeys found for given name: {',\n'.join(output)}."
        )

    # if only one regkey is found, return it
    regkey = regkeys[0]

    return regkey


def area_to_bundesland(area: Area) -> Area:
    """Get the Bundesland (state) of an administrative area from its RegKey.

    Parameters:
        regkey (RegKey): A RegKey intended to resolve to a Bundesland.

    Returns:
        bundesland (RegKey): The name of the Bundesland of the area with the given RegKey.

    Raises:
        None
    """

    # Form the RegKey for the Bundesland from the first two digits of the input RegKey
    bl_regkey = f"{area.regkey[:2]}0000000000"
    # Create a RegKey object for the Bundesland
    bundesland = Area(bl_regkey)

    return bundesland

"""Module for working with keys from the German Regionalschlüssel (regional key) system.

A Regionalschlüssel identifies a politically independent area in Germany.
While its usual form is a 12-digit key capable of identifying all administrative levels down to single villages,
due to the unnecessary amount of precision this module uses a 5-digit version representing counties and county-level cities.
More information: https://de.wikipedia.org/wiki/Regionalschl%C3%BCssel

Classes:
    RegKey: A German Regionalschlüssel.

Functions:
    get_regkey_list: Return a list of all valid RegKeys.
    validate_regkey: Check if a string is a valid RegKey.
    regkey_to_name: Return the name of an area identified by a RegKey.
    name_to_regkey: Return the RegKey of an area identified by a name.
    infer_regkey: Return a RegKey from a string.
"""

import importlib.resources as res
import zipfile as zip
import pandas as pd
from typing import Union


class RegKey:
    """A German Regionalschlüssel.

    Attributes:
        regkey (str): The regional key.
        name (str): The name of the area identified by the regkey.
        population (int): The population of the area identified by the regkey.

    Methods:
        __init__: Initialize a RegKey object.
        __str__: Return information about the RegKey object.
        __repr__: Return all information about the RegKey object.
        to_dict: Return a dictionary representation of the RegKey object.
    """

    __slots__ = ("_regkey", "_name", "_population")

    def __init__(self, regkey: str) -> None:
        """Initialize a RegKey object.

        Parameters:
            regkey (str): A valid regkey value or area name.

        Returns:
            None

        Raises:
            None
        """

        # try to infer a regkey from the input
        regkey = infer_regkey(regkey)

        # set the regkey, name and population attributes
        self._regkey = regkey
        self._name = regkey_to_name(regkey)
        self._population = regkey_to_population(regkey)

    def __str__(self) -> str:
        """Return information about the RegKey object."""
        return f"{self.name} ({self.regkey})"

    def __repr__(self) -> str:
        """Return all information about the RegKey object."""
        return f"RegKey object for {self.name} ({self.regkey}). Population: {self.population}"

    def to_dict(self) -> dict:
        """Return a dictionary representation of the RegKey object."""
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

        # update the name attribute if the regkey changes
        self._name = regkey_to_name(regkey)
        self._population = regkey_to_population(regkey)

    @regkey.deleter
    def regkey(self) -> None:
        """Protect regkey from being deleted and warn user."""
        raise AttributeError(
            "RegKey.regkey value must not be deleted, change it instead."
        )

    @property
    def name(self):
        """Name of the area defined by regkey."""
        return self._name

    @name.setter
    def name(self, value) -> None:
        """Protect the name of the regkey from being changed."""
        raise AttributeError(
            f'RegKey.name cannot be changed to "{value}", change value of regkey instead.'
        )

    @name.deleter
    def name(self) -> None:
        """Protect name from being deleted and warn user."""
        raise AttributeError(
            "RegKey.name must not be deleted, change value of regkey instead."
        )

    @property
    def population(self):
        """Population size of the area defined by regkey."""
        return self._population

    @population.setter
    def population(self, value) -> None:
        """Protect the population of the regkey from being changed."""
        raise AttributeError(
            f'RegKey.population cannot be changed to "{value}", change value of regkey instead.'
        )

    @population.deleter
    def population(self) -> None:
        """Protect population from being deleted and warn user."""
        raise AttributeError(
            "RegKey.population must not be deleted, change value of regkey instead."
        )


def get_regkey_list(drop_population: bool = True) -> pd.DataFrame:
    """Read the list of RegKeys from a dedicated file.

    Data is taken from the German Regionalatlas database (regionalstatistik.de).
    It contains the 5-digit RegKeys for all German counties and county-level cities.

    Parameters:
        drop_population (bool): Whether to drop the 'population' column from the DataFrame.

    Returns:
        regkey_list (pd.DataFrame): A DataFrame containing the RegKeys.

    Raises:
        None
    """

    # Read the list of RegKeys from the file
    path = res.files(__package__).joinpath("files.zip")

    with res.as_file(path) as zipfile:
        with zip.ZipFile(zipfile, mode="r") as archive:
            with archive.open("files/regkey_data.csv") as csvfile:
                regkey_list = pd.read_csv(
                    csvfile,
                    sep=";",
                    encoding="utf-8",
                    header=0,
                    index_col=0,
                    engine="python",
                    converters={"regional_key": str},
                )

    # If not negated, drop the unnecessary 'population' column containing population data
    if drop_population:
        regkey_list.drop(columns=["population"])

    # drop rows where the index value is not a valid RegKey
    regkey_list = regkey_list[regkey_list.index.str.len() == 5]

    return regkey_list


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

    # If the regkey contains characters other than digits, try to resolve as a RegKey name.
    if not regkey.isdigit():
        try:
            regkey = name_to_regkey(regkey)
        except ValueError as error:
            raise error

    # Check if the RegKey is shorter than 5 digits and therefore invalid
    if len(regkey) < 5:
        raise ValueError("RegKey must be at least 5 digits long.")

    # If the RegKey is longer than 5 digits, convert it to a short RegKey
    if len(regkey) > 5:
        regkey = regkey[:5]

    # Check if the first two digits are within the valid range of 01-16.
    # The first two digits of a RegKey identify the Bundesland.
    if not 1 <= int(regkey[:2]) <= 16:
        raise ValueError("First two digits of the RegKey must be between 01 and 16.")

    # Although possible, it is impractical to check digits 3-5 due to the large number of plausible values needed for some large Bundesländer.

    # Check if the RegKey is valid by looking it up in the list of RegKeys
    # Get the list of RegKeys
    regkey_list = get_regkey_list()

    # Check if the RegKey is in the list
    if regkey in regkey_list.index:
        return True
    else:
        raise ValueError("RegKey is not a valid RegKey.")


def regkey_to_name(regkey: str) -> str:
    """Get the name of an administrative area from its RegKey.

    Parameters:
        regkey (str): A RegKey intended to resolve to a name.

    Returns:
        name (str): The name of the area with the given RegKey.

    Raises:
        None
    """

    # Check if the RegKey is valid
    validate_regkey(regkey)

    # Get the list of RegKeys
    regkey_list = get_regkey_list()

    # Get the name of the area with the given RegKey
    name = regkey_list.loc[regkey, "name"]

    return name


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

        raise ValueError(f"Multiple RegKeys found for given name: {', '.join(output)}.")

    # if only one regkey is found, return it
    regkey = regkeys[0]

    return regkey


def regkey_to_population(regkey: str) -> int:
    """Get the population of an administrative area from its RegKey.

    Parameters:
        regkey (str): A RegKey intended to resolve to a population.

    Returns:
        population (int): The population of the area with the given RegKey.

    Raises:
        None
    """

    # Check if the RegKey is valid
    validate_regkey(regkey)

    # Get the list of RegKeys
    regkey_list = get_regkey_list()

    # Get the population of the area with the given RegKey
    population = regkey_list.loc[regkey, "population"]

    return population


def infer_regkey(input: Union[RegKey, str]) -> str:
    """Try to infer a valid regkey from input.

    Parameters:
        input (RegKey or str): The input to be inferred.

    Returns:
        regkey (str): The inferred regkey.

    Raises:
        TypeError: If the input is not a RegKey or a string.
    """

    # If the input is a RegKey Object, return its regkey value
    if isinstance(input, RegKey):
        return input.regkey

    # If the input is a regkey, validate and return it
    if isinstance(input, str) and input.isdigit():
        validate_regkey(input)
        return input

    # If the input could be a name, try to convert it to a regkey and return it
    if isinstance(input, str):
        return name_to_regkey(input)

    # If none of the above apply, raise an error
    raise TypeError("No regkey could be inferred from input.")

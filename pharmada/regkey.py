"""Module for working with keys from the German Regionalschlüssel (regional key) system.

The Regionalschlüssel system is a hierarchical system for identifying
administrative areas in Germany.

"""

from math import inf
import pandas as pd

class RegKey:
    """A German Regionalschlüssel."""

    __slots__ = ('_regkey', '_name')

    def __init__(self, regkey) -> None:
        """Initialize a RegKey object.

        Args:
            regkey (str): A valid regkey value or area name."""
        
        # try to infer a regkey from the input
        regkey = infer_regkey(regkey)   
        
        self._regkey = regkey
        self._name = regkey_to_name(regkey)

    def __str__(self) -> str:
        """Return information about the RegKey object."""
        return f'{self.name} ({self.regkey}))'
    
    def __repr__(self) -> str:
        """Return all information about the RegKey object."""
        class_name = type(self).__name__
        return f'{class_name}: {self.name} ({self.regkey}))'
    
    def __eq__(self, other) -> bool:
        """Check if two RegKey objects are equal."""
        return self.regkey == other.regkey
    
    def __hash__(self) -> int:
        """Return the hash of the RegKey object."""
        return hash(self.regkey)
    
    @property
    def regkey(self):
        """Return the regkey value."""
        return self._regkey
    
    @property
    def name(self):
        """Return the name of the regkey."""
        return self._name

def get_regkey_list(file='./data/kreise_data.csv'):
    """Read the list of RegKeys from a dedicated file.
    
    The data is taken from the German Regionalatlas database (regionalstatistik.de).
    It contains the 5-digit RegKeys for all German counties and county-level cities."""

    # Read in the data from a dedicated csv file
    regkey_list = pd.read_csv(file, sep=';',
                    header=0, index_col=0, encoding='utf-8',
                    converters={'regional_key': str}, engine='python')
    
    # Drop the unnecessary 'total' column containing population data
    regkey_list.drop(columns=['total'])

    return regkey_list

def validate_regkey(regkey):
    """Check if a RegKey is valid."""

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
        return True, regkey
    else:
        raise ValueError("RegKey is not a valid RegKey.")

def regkey_to_name(regkey):
    """Get the name of an administrative area from its RegKey."""

    # Check if the RegKey is valid
    validate_regkey(regkey)

    # Get the list of RegKeys
    regkey_list = get_regkey_list()
    
    # Get the name of the area with the given RegKey
    name = regkey_list.loc[regkey, 'name']

    return name

def name_to_regkey(name):
    """Get the RegKey of an administrative area from its name."""

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
            name = regkey_list.loc[regkey, 'name']
            output.append(f"{name} ({regkey})")
        
        raise ValueError(f"Multiple RegKeys found for given name, please choose one: {', '.join(output  )}.")
    
    # if only one regkey is found, return it
    regkey = regkeys[0]

    return regkey

def infer_regkey(input):
    """Try to infer a valid regkey from input.
    
    Input can be a RegKey object, a regkey, or a name."""

    # If the input is a RegKey Object, return its regkey value
    if isinstance(input, RegKey):
        return input.regkey
    
    # If the input is a regkey, validate and return it
    if isinstance(input, str) and input.isdigit():
        validate_regkey(input)
        return input
    
    # If the input is a name, convert it to a regkey and return it
    if isinstance(input, str) and not input.isdigit():
        return name_to_regkey(input)
    
    # If none of the above apply, raise an error
    raise TypeError("No regkey could be inferred from imput.")
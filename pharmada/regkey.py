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

import pandas as pd

class RegKey:
    """A German Regionalschlüssel.
    
    Attributes:
        regkey (str): The regkey value.
        name (str): The name of the area identified by the regkey.
        
    Methods:
        __init__: Initialize a RegKey object.
        __str__: Return information about the RegKey object.
        __repr__: Return all information about the RegKey object.
        __eq__: Check if two RegKey objects are equal.
        __hash__: Return the hash of the RegKey object.
    """

    __slots__ = ('_regkey', '_name')

    def __init__(self, regkey: str) -> None:
        """Initialize a RegKey object.

        Parameters:
            regkey (str): A valid regkey value or area name."""
        
        # try to infer a regkey from the input
        regkey = infer_regkey(regkey)   
        
        self._regkey = regkey
        self._name = regkey_to_name(regkey)

    def __str__(self) -> str:
        """Return information about the RegKey object."""
        return f'{self.name} ({self.regkey})'
    
    def __repr__(self) -> str:
        """Return all information about the RegKey object."""
        return f'RegKey for {self.name} ({self.regkey})'
    
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
    
    @regkey.setter
    def regkey(self, regkey: str) -> None:
        """Set the regkey value.
        
        Parameters:
            regkey (str): A valid regkey value or area name.
            
        Raises:
            None
        """

        # try to infer a regkey from the input
        regkey = infer_regkey(regkey)

        self._regkey = regkey

        # update the name attribute if the regkey changes
        self._name = regkey_to_name(regkey)

    @regkey.deleter
    def regkey(self) -> None:
        """Protect the regkey value from deletion."""
        raise AttributeError("RegKey value cannot be deleted.")
    
    @property
    def name(self):
        """Return the name of the regkey."""
        return self._name
    
    @name.setter
    def name(self) -> None:
        """Protect the name of the regkey from being changed."""
        raise AttributeError("RegKey name cannot be changed, change value of regkey instead.")
    
    @name.deleter
    def name(self) -> None:
        """Protect the name of the regkey from deletion."""
        raise AttributeError("RegKey name cannot be deleted, change value of regkey instead.")

def get_regkey_list(file: str = './data/kreise_data.csv') -> pd.DataFrame:
    """Read the list of RegKeys from a dedicated file.
    
    Data is taken from the German Regionalatlas database (regionalstatistik.de).
    It contains the 5-digit RegKeys for all German counties and county-level cities.
    
    Parameters:
        file (str): The path to the file containing the RegKeys.
    
    Returns:
        regkey_list (pd.DataFrame): A DataFrame containing the RegKeys.
    
    Raises:
        TypeError: If the file path is not a string.
        FileNotFoundError: If the file does not exist.
    """

    # Check if the file path is valid
    if not isinstance(file, str):
        raise TypeError("File path must be a string.")
    
    # Check if the file exists
    try:
        open(file)
    except FileNotFoundError:
        raise FileNotFoundError("File not found.")
    

    # Read in the data from a dedicated csv file
    regkey_list = pd.read_csv(file, sep=';',
                    header=0, index_col=0, encoding='utf-8',
                    converters={'regional_key': str}, engine='python')
    
    # Drop the unnecessary 'total' column containing population data
    regkey_list.drop(columns=['total'])

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
        ValueError: If the RegKey is not 5 digits long.
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
    name = regkey_list.loc[regkey, 'name']

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
            name = regkey_list.loc[regkey, 'name']
            output.append(f"{name} ({regkey})")
        
        raise ValueError(f"Multiple RegKeys found for given name: {', '.join(output  )}.")
    
    # if only one regkey is found, return it
    regkey = regkeys[0]

    return regkey

def infer_regkey(input: [RegKey, str]) -> str:
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
    if isinstance(input, str) and not input.isdigit():
        return name_to_regkey(input)
    
    # If none of the above apply, raise an error
    raise TypeError("No regkey could be inferred from input.")
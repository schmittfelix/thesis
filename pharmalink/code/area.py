"""A module for working with German administrative areas.

Every administrative area in Germany is identified by a unique regional key (Regionalschlüssel).
While its usual form is a 12-digit key capable of identifying all administrative levels down to single villages,
a 5-digit key is often used to identify counties and county-level cities (Kreise and kreisfreie Städte) and
a 2-digit key to identify the Bundesländer (states).
More information: https://de.wikipedia.org/wiki/Regionalschl%C3%BCssel
"""

from pharmalink.code.sources import AdminAreas
import folium as fl
from statistics import mean


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
        "bundesland",
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
        regkey = self._infer_regkey(identifier)

        # get the data for the specified area
        area = AdminAreas.get_area(regkey)

        self.regkey = regkey
        self.level = area["level"].values[0]
        self.bundesland = self._regkey_to_bundesland()
        self.full_name = area["full_name"].values[0]
        self.geo_name = area["geo_name"].values[0]
        self.title = area["title"].values[0]
        self.population = area["population"].values[0]
        self.geometry = area.filter(["regkey", "full_name", "geometry"])

    def __str__(self) -> str:
        """Return information about the Area object."""
        return f"{self.full_name} ({self.regkey})"

    def plot(self, **kwargs) -> fl.Map:
        """Plot the area geometry.

        Args:
            **kwargs: Keyword arguments passed to the plot functions.

        Returns:
            None

        Raises:
            None
        """

        geometry = self.geometry

        # Set CRS to EPSG:4326 for folium
        geometry = geometry.to_crs(epsg=4326)

        # Setup of the map's bounds
        bounds = geometry.total_bounds
        x = mean([bounds[0], bounds[2]])
        y = mean([bounds[1], bounds[3]])
        viewport_center = (y, x)

        # Setup of the map
        map_args = {
            "location": viewport_center,
            "width": "100%",
            "height": "100%",
            "tiles": "cartodbpositron",
            "min_zoom": 8,
            "max_zoom": 18,
            "control_scale": False,
            "zoom_control": False,
            "prefer_canvas": True,
        }

        map = fl.Map(**map_args)

        # fit map to bounds for nice display
        map.fit_bounds(
            [[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(10, 10)
        )

        style_args = {}

        # Setup of the map content
        area_args = {
            "data": geometry,
            "name": self.full_name,
            "regkey": self.regkey,
        }

        fl.GeoJson(**area_args, **style_args).add_to(map)

        # Return the map
        return map

    def _infer_regkey(self, input: str) -> str:
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
        if isinstance(input, str) and self._validate_regkey(input):
            return f"{input:0<12}"

        # If the input could be an area name instead, try to convert it to a regkey
        if isinstance(input, str):
            return self._name_to_regkey(input)

        # If none of the above apply, raise an error
        raise TypeError("No regkey could be inferred from input.")

    def _validate_regkey(self, regkey: str) -> bool:
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

        # If the regkey contains characters other than digits, try to resolve as a RegKey name.
        if not regkey.isdigit():
            return False

        # Check if the RegKey is either 2, 5 or 12 digits long
        if not len(regkey) in [2, 5, 12]:
            raise ValueError("RegKey must be either 2, 5 or 12 digits long.")

        # Check if the first two digits are within the valid range of 01-16.
        # The first two digits of a RegKey identify the Bundesland.
        if not int(regkey[:2]) in range(0, 17):
            raise ValueError(
                "First two digits of the RegKey must be between 00 and 16."
            )

        # Check if the RegKey is valid by looking it up in the list of RegKeys
        # Get the list of RegKeys
        regkey_list = AdminAreas.get_regkeys()

        # Prepare the RegKey for lookup by adding trailing zeros to keys shorter than 12 digits
        regkey = f"{regkey:0<12}"

        # Check if the RegKey is in the list
        if regkey in regkey_list:
            return True
        else:
            raise ValueError("RegKey is not a valid RegKey.")

    def _name_to_regkey(self, name: str) -> str:
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
        area_names = AdminAreas.get_area_names()

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

    def _regkey_to_bundesland(self) -> str:
        """Determine the Bundesland of an area from its RegKey."""

        two_digits = f"{self.regkey[:2]}"

        # Handle the edge case of looking up the Bundesland for the whole country
        if two_digits == "00":
            return "Deutschland"

        # Source: admin_areas filtered for bundesland level
        bundeslaender = {
            "01": "Schleswig-Holstein",
            "02": "Hamburg",
            "03": "Niedersachsen",
            "04": "Bremen",
            "05": "Nordrhein-Westfalen",
            "06": "Hessen",
            "07": "Rheinland-Pfalz",
            "08": "Baden-Württemberg",
            "09": "Bayern",
            "10": "Saarland",
            "11": "Berlin",
            "12": "Brandenburg",
            "13": "Mecklenburg-Vorpommern",
            "14": "Sachsen",
            "15": "Sachsen-Anhalt",
            "16": "Thüringen",
        }

        bundesland = bundeslaender[two_digits]

        return bundesland

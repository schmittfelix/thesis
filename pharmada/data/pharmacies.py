"""Module for retrieval and presentation of information about pharmacies within a given area.

Classes:
    Pharmacies
    
Functions:
    pharmacies_in_area:     Get all pharmacies within an area.
    calculate_area_radius:  Calculate minimum bounding radius of given area.
    fetch_pharmacies:       Fetch pharmacies from Overpass API.
"""

import pharmada.data.geometry as geo
import pharmada.data.overpass as op
import geopandas as gpd
from shapely.geometry import Point


class Pharmacies:
    """Class for Storing and manipulating data about pharmacies in a given area.

    Parameters:
        AreaGeometry:   AreaGeometry object for the area.

    Attributes:
        AreaGeometry:   AreaGeometry object for the area.
        pharmacies:     GeoDataFrame containing all pharmacies in the area.

    Methods:
        __str__:   Return information about the Pharmacies object.
        __repr__:  Return all information about the Pharmacies object.
    """

    __slots__ = ("_AreaGeometry", "_pharmacies")

    def __init__(self, AreaGeometry: geo.AreaGeometry) -> None:
        """Initialize Pharmacies object.

        Parameters:
            AreaGeometry:   AreaGeometry object for the area.

        Returns:
            None

        Raises:
            None
        """

        # check if AreaGeometry is valid
        if not isinstance(AreaGeometry, geo.AreaGeometry):
            raise TypeError("AreaGeometry must be an instance of AreaGeometry.")

        self._AreaGeometry = AreaGeometry
        self._pharmacies = fetch_pharmacies(AreaGeometry)

    def __str__(self) -> str:
        """Return information about the Pharmacies object."""
        return f"Pharmacies in {self.AreaGeometry.RegKey}"

    def __repr__(self) -> str:
        """Return all information about the Pharmacies object."""
        return f"Pharmacies in {self.AreaGeometry.RegKey}.\n{self.pharmacies.info()}"

    @property
    def AreaGeometry(self) -> geo.AreaGeometry:
        """AreaGeometry object defining the area to collect pharmacies for."""
        return self._AreaGeometry

    @AreaGeometry.setter
    def AreaGeometry(self, AreaGeometry: geo.AreaGeometry) -> None:
        """Set the area to collect pharmacies for."""

        # check if AreaGeometry is valid
        if not isinstance(AreaGeometry, geo.AreaGeometry):
            raise TypeError("AreaGeometry must be an instance of AreaGeometry.")

        self._AreaGeometry = AreaGeometry
        self._pharmacies = fetch_pharmacies(AreaGeometry)

    @AreaGeometry.deleter
    def AreaGeometry(self) -> None:
        """Protect AreaGeometry object from being deleted and warn user."""
        raise AttributeError(
            "Pharmacies.AreaGeometry must not be deleted, change it instead."
        )

    @property
    def pharmacies(self) -> gpd.GeoDataFrame:
        """Pharmacies within the area."""
        return self._pharmacies

    @pharmacies.setter
    def pharmacies(self, value) -> None:
        """Protect pharmacies from being set and warn user."""
        raise AttributeError(
            f'Pharmacies.pharmacies cannot be changed to "{value}", change AreaGeometry instead.'
        )

    @pharmacies.deleter
    def pharmacies(self) -> None:
        """Protect pharmacies GeoDataFrame from being deleted and warn user."""
        raise AttributeError(
            "Pharmacies.pharmacies must not be deleted, change AreaGeometry instead."
        )

def fetch_pharmacies(AreaGeometry: geo.AreaGeometry) -> gpd.GeoDataFrame:
    """Get pharmacies within area from Overpass API.

    Parameters:
        AreaGeometry:   AreaGeometry object for the area.

    Returns:
        pharmacies:     GeoDataFrame of pharmacies within the area.

    Raises:
        None
    """

    # build query to get pharmacies within area
    query = f"""
    [out:json];
        
    //set up area given by regional_key as search boundary
    (
    relation({AreaGeometry.osm_id});
    map_to_area;
    ) ->.boundary;
    
    //nodes within the search area with 'amenity' tag set to 'pharmacy'
    node(area.boundary)["amenity"="pharmacy"]->.results;

    // output full geometry of the results set     
    .results out geom qt;
    """

    response = op.query_overpass(query)

    # Raise error if no pharmacies were found
    if len(response["elements"]) == 0:
        raise ValueError("No pharmacies found in area.")

    pharmacies = []

    for pharmacy in response["elements"]:
        tags = pharmacy["tags"]

        # build address in regular german format
        address = {}
        for tag in ["addr:street", "addr:housenumber", "addr:postcode", "addr:city"]:
            # Remove 'addr:' from the tag name
            clean_tag = tag.replace("addr:", "")

            # If tag is present, add it to the address, else add empty string
            if tag in tags:
                address[clean_tag] = tags[tag]
            else:
                address[clean_tag] = ""

        formatted_address = f"{address['street']} {address['housenumber']}, {address['postcode']} {address['city']}"

        # If name is present, add it to the address, else add empty string
        if "name" in tags:
            name = f"{tags['name']}"
        else:
            name = ""

        # collect pharmacy data
        pharmacy_dict = {
            "id": pharmacy["id"],
            "name": name,
            "address": formatted_address,
            "location": Point(pharmacy["lon"], pharmacy["lat"]),
        }
        pharmacies.append(pharmacy_dict)

    # convert to GeoDataFrame
    pharmacies = gpd.GeoDataFrame(
        pharmacies, geometry="location", crs=AreaGeometry.geometry.crs
    )

    return pharmacies

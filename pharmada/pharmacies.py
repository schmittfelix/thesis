"""Module for retrieval and presentation of information about pharmacies within a given area.

Area geometry is extracted from OSM.
Pharmacy data is retreived from GMaps.

Classes:
    Pharmacies
    Pharmacy
    
Functions:
    pharmacies_in_area:     Get all pharmacies within an area.
    calculate_area_radius:  Calculate minimum bounding radius of given area.
    fetch_pharmacies:       Fetch pharmacies from GMaps.
    filter_pharmacies:      Filter pharmacies by area geometry."""

import pharmada.geometry as geo
import time
import ftfy
import requests as req
import geopandas as gpd
from shapely.geometry import Point

class PharmaciesInArea:
    """Class for Storing and manipulating data about pharmacies in a given area.
    
    Parameters:
        AreaGeometry:   AreaGeometry object for the area.
        gmaps_key:      Google Maps API key.

    Attributes:
        AreaGeometry:   AreaGeometry object for the area.
        gmaps_key:      Google Maps API key.
        pharmacies:     GeoDataFrame containing all pharmacies in the area.

    Methods:
        __str__:   Return information about the Pharmacies object.
        __repr__:  Return all information about the Pharmacies object.
    """

    __slots__ = ('_AreaGeometry', '_gmaps_key', '_pharmacies')

    def __init__(self, AreaGeometry: geo.AreaGeometry, gmaps_key: str) -> None:
        """Initialize Pharmacies object.
        
        Parameters:
            AreaGeometry:   AreaGeometry object for the area.
            gmaps_key:      Google Maps API key.
            
        Returns:
            None
            
        Raises:
            None
        """

        self._AreaGeometry = AreaGeometry
        self._gmaps_key = gmaps_key
        self._pharmacies = pharmacies_in_area(AreaGeometry, gmaps_key)

    def __str__(self) -> str:
        """Return information about the Pharmacies object."""
        return f"Pharmacies in {self.AreaGeometry.RegKey.name}."
    
    def __repr__(self) -> str:
        """Return all information about the Pharmacies object."""
        return f"Pharmacies in {self.AreaGeometry.RegKey.name}.\n{self.pharmacies.info()}"
    


    @property
    def AreaGeometry(self) -> geo.AreaGeometry:
        """AreaGeometry object for the area."""
        return self._AreaGeometry
    
    @AreaGeometry.setter
    def AreaGeometry(self, AreaGeometry: geo.AreaGeometry) -> None:
        """Set AreaGeometry object for the area and update Pharmacies GeoDataFrame."""
        self._AreaGeometry = AreaGeometry
        self._pharmacies = pharmacies_in_area(AreaGeometry, self.gmaps_key)

    @AreaGeometry.deleter
    def AreaGeometry(self) -> None:
        """Protect AreaGeometry object and warn user."""
        raise AttributeError("AreaGeometry object must not be deleted.")
    
    @property
    def gmaps_key(self) -> str:
        """Google Maps API key."""
        return self._gmaps_key
    
    @gmaps_key.setter
    def gmaps_key(self, gmaps_key: str) -> None:
        """Set Google Maps API key."""
        self._gmaps_key = gmaps_key

    @gmaps_key.deleter
    def gmaps_key(self) -> None:
        """Protect Google Maps API key and warn user."""
        raise AttributeError("Google Maps API key must not be deleted.")
    
    @property
    def pharmacies(self) -> gpd.GeoDataFrame:
        """GeoDataFrame of pharmacies within the area."""
        return self._pharmacies
    
    @pharmacies.setter
    def pharmacies(self) -> None:
        """Protect pharmacies GeoDataFrame and warn user."""
        raise AttributeError("Pharmacies Attribute must not be deleted. Change AreaGeometry instead.")
    
    @pharmacies.deleter
    def pharmacies(self) -> None:
        """Protect pharmacies GeoDataFrame and warn user."""
        raise AttributeError("Pharmacies Attribute must not be deleted.")

def pharmacies_in_area(AreaGeometry: geo.AreaGeometry, gmaps_key: str) -> gpd.GeoDataFrame:
    """Get all pharmacies within an area.
    
    Parameters:
        AreaGeometry:   AreaGeometry object for the area.
        gmaps_key:      Google Maps API key.
        
    Returns:
        pharmacies:     GeoDataFrame of pharmacies within the area.
        
    Raises:
        None
    """

    # get pharmacies
    found_pharmacies = fetch_pharmacies(AreaGeometry, gmaps_key)

    # filter pharmacies
    pharmacies = filter_pharmacies(found_pharmacies, AreaGeometry)

    return pharmacies

def calculate_area_radius(AreaGeometry: geo.AreaGeometry) -> int:
    """Calculate area radius from boundaries.
    
    Parameters:
        AreaGeometry:   AreaGeometry object for the area.
        
    Returns:
        area_radius:    The radius of the area in meters.
        
    Raises:
        None
    """

    # get area geometry
    area_geom = AreaGeometry.geometry

    area_geom = area_geom.to_crs(area_geom.estimate_utm_crs())
    
    area_radius = area_geom.minimum_bounding_radius()

    return round(area_radius[0], 0)

def fetch_pharmacies(AreaGeometry: geo.AreaGeometry, gmaps_key: str) -> list:
    """Get pharmacies within area from GMaps.
    
    Parameters:
        AreaGeometry:   AreaGeometry object for the area.
        gmaps_key:      Google Maps API key.
        
    Returns:
        found_pharmacies:   List of pharmacies within the area.
        
    Raises:
        None
    """

    # get area geometry
    area_geom = AreaGeometry.geometry

    # convert area geometry to UTM
    area_geom = area_geom.to_crs(area_geom.estimate_utm_crs())

    # get area centroid and convert back to WGS84 for LatLng coordinates
    centroid = area_geom.centroid
    centroid = centroid.to_crs('EPSG:4326')

    # calculate search radius
    search_radius = calculate_area_radius(AreaGeometry)

    def query_gmaps(query_params):
        """Query the GMaps Places API ."""
        url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?'
    
        # set default parameter
        payload = {'key': gmaps_key}

        # add query parameters
        for key, value in query_params.items():
            payload[key] = value

        # query the API
        response = req.get(url, params=payload)

        # check if the request was successful        
        response.raise_for_status()
        

            
        # convert response to JSON
        result = response.json()
        
        # If the response is empty, raise an error
        if not result['results']:
            raise ValueError("No results found.")
        
        return result

    # get pharmacies from GMaps
    params = {
        'location': f'{centroid.y[0]},{centroid.x[0]}',
        'radius': search_radius,
        'type': 'pharmacy',
        'language': 'de'
    }
    result = query_gmaps(params)


    found_pharmacies = result['results']

    # API returns max. 20 results per request, next_page_token is used for pagination.
    # At max 3 pages (60 results) are returned.
    def get_next_page(next_page_token):
        """Get the next page of results from GMaps."""

        # short pause due to API limitations
        time.sleep(5)

        # resend request with next_page_token exclusively
        params.clear()
        params['pagetoken'] = next_page_token
        result = query_gmaps(params)

        return result
    
    # check if there are more results
    for i in range(2):
        if 'next_page_token' in result:
            # get next page
            result = get_next_page(result['next_page_token'])

            found_pharmacies.extend(result['results'])
        else:
            break

    return found_pharmacies

def filter_pharmacies(found_pharmacies: list, AreaGeometry: geo.AreaGeometry) -> gpd.GeoDataFrame:
    """Filter out of bounds pharmacies and fix attributes.
    
    Parameters:
        found_pharmacies:   List of pharmacies found in the area.
        AreaGeometry:       AreaGeometry object for the area.
        
    Returns:
        pharmacies:         GeoDataFrame of pharmacies within the area.
        
    Raises:
        None
    """

    # get area geometry
    area_geom = AreaGeometry.geometry

    pharmacies = []

    for pharmacy in found_pharmacies:

        # check if pharmacy is within bounds
        pharmacy_location = Point(pharmacy['geometry']['location']['lng'], pharmacy['geometry']['location']['lat'])
        in_area = area_geom.contains(gpd.GeoSeries(pharmacy_location, crs=area_geom.crs))[0]

        # check if pharmacy name contains "apotheke" or "pharmacy" and filter out "e.V." (Verein)
        matching_name = any(x in pharmacy['name'].lower() for x in ['apotheke', 'pharmacy']) and \
                        not any(x in pharmacy['name'].lower() for x in ['e.v.', 'e. v.'])
        
        # if either of the above checks fails, skip the pharmacy
        if not in_area or not matching_name:
            continue

        # extract location, name and id from results
        ph_name = ftfy.fix_text(pharmacy['name'])
        ph_id = pharmacy['place_id']
        ph_location = Point(pharmacy['geometry']['location']['lng'], pharmacy['geometry']['location']['lat'])
        ph_address = pharmacy['vicinity']

        ph = {
            'name': ph_name,
            'ph_id': ph_id,
            'location': ph_location,
            'address': ph_address
        }

        pharmacies.append(ph)

    # convert to GeoDataFrame
    result = gpd.GeoDataFrame(pharmacies, geometry='location', crs=area_geom.crs)

    return result

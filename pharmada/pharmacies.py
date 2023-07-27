"""Retrieve and present information about pharmacies within a given area.

Area geometry is extracted from OSM.
Pharmacy data is retreived from GMaps.
"""

import pharmada.overpass as op
import time
import ftfy
import requests as req
import geopandas as gpd
from shapely.geometry import Point

def pharmacies_in_area(regional_key, gmaps_key):
    """Get all pharmacies within an area."""

    # get area geometry
    area_geom = op.get_area_geometry(regional_key)

    # get pharmacies
    found_pharmacies = fetch_pharmacies(area_geom, gmaps_key)

    # filter pharmacies
    pharmacies = filter_pharmacies(found_pharmacies, area_geom)

    return pharmacies

def calc_area_radius(area_geom):
    """Calculate area radius from boundaries."""

    area_geom = area_geom.to_crs(area_geom.estimate_utm_crs())
    
    area_radius = area_geom.minimum_bounding_radius()

    return area_radius[0].round(0)

def fetch_pharmacies(area_geom, gmaps_key):
    """Get pharmacies within area from GMaps."""

    # convert area geometry to UTM
    crs = area_geom.estimate_utm_crs()
    area_geom = area_geom.to_crs(crs)

    # get area centroid and convert back to WGS84 for LatLng coordinates
    centroid = area_geom.centroid
    centroid = centroid.to_crs('EPSG:4326')

    # calculate search radius
    search_radius = calc_area_radius(area_geom)

    #Subfunction to query the GMaps Places API
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
        
        # If the response is empty, raise an error
        if not response['results']:
            raise ValueError("No results found.")
            
        # convert response to JSON
        result = response.json()
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
    # Max. of 3 pages (60 results) are returned.
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

def filter_pharmacies(found_pharmacies, area_geom):
    """Filter out of bounds pharmacies and fix attributes."""

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
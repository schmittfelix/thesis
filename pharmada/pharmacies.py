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

class Pharmacy:
    def __init__(self, name, gmaps_id, location, address):
        self.name = name
        self.gmaps_id = gmaps_id
        self.location = location
        self.address = address

    def __repr__(self):
        return f"Pharmacy('{self.name}', '{self.gmaps_id}', '{self.location}', '{self.address}')"
    
    def __str__(self):
        return f"{self.name} ({self.address})"
    
    def __eq__(self, other):
        return self.gmaps_id == other.gmaps_id
    
    def __hash__(self):
        return hash(self.gmaps_id)

    def to_dict(self):
        return {
            'name': self.name,
            'gmaps_id': self.gmaps_id,
            'location': self.location,
            'address': self.address
        }


def pharmacies_in_area(regional_key, gmaps_key):
    """Get all pharmacies within an area."""

    # get area geometry
    area_geom = op.get_area_geometry(regional_key)

    # calculate area radius
    area_radius = _calculate_area_radius(area_geom)

    # get pharmacies
    found_pharmacies = _fetch_pharmacies(area_geom, area_radius, gmaps_key)

    # filter pharmacies
    pharmacies = _filter_pharmacies(found_pharmacies, area_geom)

    return pharmacies

def _calculate_area_radius(area_geom):
    """Calculate area radius from boundaries."""

    area_geom = area_geom.to_crs(area_geom.estimate_utm_crs())
    
    area_radius = area_geom.minimum_bounding_radius()

    return area_radius

def _fetch_pharmacies(area_geom, area_radius, gmaps_key):
    """Get pharmacies within area from GMaps."""

    area_geom = area_geom.to_crs(area_geom.estimate_utm_crs())

    centroid = area_geom.centroid
    centroid = centroid.to_crs('epsg:4326')
    
    find_pharmacies = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={centroid.y[0]},{centroid.x[0]}&radius={area_radius}&type=pharmacy&language=de&key={gmaps_key}'
    result = req.get(find_pharmacies).json()

    found_pharmacies = result['results']

    # Max 20 results are returned per request, so we need to use the next_page_token to get more results if available
    if 'next_page_token' in result:
        
        while True:
            find_more_pharmacies = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?pagetoken={result["next_page_token"]}&key={gmaps_key}'
            
            time.sleep(5)
            result = req.get(find_more_pharmacies).json()
            found_pharmacies.extend(result['results'])

            if 'next_page_token' not in result:
                break

    return found_pharmacies

def _filter_pharmacies(found_pharmacies, area_geom):
    """Filter out of bounds pharmacies and fix attributes."""

    # filter and prepare pharmacies
    pharmacies = []

    for pharmacy in found_pharmacies:

        # check if pharmacy is within bounds
        pharmacy_location = Point(pharmacy['geometry']['location']['lng'], pharmacy['geometry']['location']['lat'])
        in_area = area_geom.contains(gpd.GeoSeries(pharmacy_location, crs=area_geom.crs))[0]

        # check if pharmacy name contains "apotheke" or "pharmacy" and filter out "e.V." (Verein)
        matching_name = any(x in pharmacy['name'].lower() for x in ['apotheke', 'pharmacy']) and \
                        not any(x in pharmacy['name'].lower() for x in ['e.V.'])
        
        # if either of the above checks fails, the pharmacy is skipped
        if not in_area or not matching_name:
            continue

        # extract location, name and id from results
        ph_name = ftfy.fix_text(pharmacy['name'])
        ph_id = pharmacy['place_id']
        ph_location = pharmacy['geometry']['location']
        ph_address = pharmacy['vicinity']

        # Instantiate a new pharmacy and pass data
        ph = Pharmacy(ph_name, ph_id, ph_location, ph_address)

        pharmacies.append(ph)

    return pharmacies
"""Various functions to interact with the Overpass API for OpenStreetMap data."""

import requests as req
import json
import geopandas as gpd
import osm2geojson as o2g

def resolve_reg_key(regional_key):
    """Resolve a German "Regionalschlüssel" to an OSM relation."""

    # Get an OSM ID for a given regional key
    overpass_url = 'https://overpass-api.de/api/interpreter'
    overpass_query = f"""
        [out:json];
        (relation["de:regionalschluessel"="{regional_key}"];);
        out tags;
        """
    
    response = req.get(overpass_url, params={'data': overpass_query}).json()

    # If the response is empty, add trailing zeros to the regional key to form a full 12-digit key
    if not response['elements']:
        regional_key = f"{regional_key:0<12}"
        overpass_query = f"""
            [out:json];
            (relation["de:regionalschluessel"="{regional_key}"];);
            out tags;
            """
        response = req.get(overpass_url, params={'data': overpass_query}).json()['elements'][0]

    # Check if the regional key from the request and the result match
    if regional_key != response['tags']['de:regionalschluessel']:
        raise ValueError("Regional keys from request and result do not match.")
    
    # Filter irrelevant information
    result = {
        'name':         response['tags']['name'],
        'osm_id':       response['id'],
        'regional_key': response['tags']['de:regionalschluessel'],
        'name:prefix':  response['tags']['name:prefix'],
    }

    return result

def get_area_geometry(regional_key):
    """Get area geometry for a regional key."""

    osm_id = resolve_reg_key(regional_key)['osm_id']

    overpass_url = 'https://overpass-api.de/api/interpreter'
    overpass_query = f"""
        [out:json];
        (relation({osm_id}););
        out geom;
        """
    
    response = req.get(overpass_url, params={'data': overpass_query}).json()

    result = o2g.json2geojson(response)

    area_geom = gpd.read_file(json.dumps(result['features'][0]['geometry']), driver='GeoJSON')

    return area_geom
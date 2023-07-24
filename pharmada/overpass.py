"""Various functions to interact with the Overpass API for OpenStreetMap data."""

import requests as req
import json
import geopandas as gpd
import osm2geojson as o2g

def query_overpass(query):
    """Query the Overpass API and return the JSON result."""

    overpass_url = 'https://overpass-api.de/api/interpreter'
    response = req.get(overpass_url, params={'data': query}).json()

    return response

def resolve_reg_key(regional_key):
    """Resolve a German "Regionalschlüssel" to an OSM relation."""

    # Search OSM data for a relation tagged with the regional key
    query = f"""
        [out:json];
        (relation["de:regionalschluessel"="{regional_key}"];);
        out tags;
        """
    response = query_overpass(query)

    # If the response is empty, add trailing zeros to the regional key to form a full 12-digit key
    if not response:
        regional_key = f"{regional_key:0<12}"
        query = f"""
            [out:json];
            (relation["de:regionalschluessel"="{regional_key}"];);
            out tags;
            """
        response = query_overpass(query)

    #Check response for existence and singularity of the result

    # If the response is still empty, raise an error
    if not response['elements']:
        raise ValueError("Invalid regional key.")

    # If the response contains more than one result, raise an error
    if len(response['elements']) > 1:
        raise ValueError("Multiple results for regional key.")
    
    #we can safely access the first element at this point
    result = response['elements'][0]

    # If the result is not a relation, raise an error
    if result['type'] != 'relation':
        raise ValueError("No relation found for regional key.")
    
    # If the response contains no regional key, raise an error
    if 'de:regionalschluessel' not in result['tags']:
        raise ValueError("No regional key found for relation.")
    
    # Check if the regional keys from the request and the result match
    if regional_key != response['tags']['de:regionalschluessel']:
        raise ValueError("Regional keys from request and result do not match.")
    
    # If the response contains no name or id, raise an error
    if 'name' or 'id' not in result['tags']:
        raise ValueError("No name or id found for relation.")
    
    # Result is valid, return it
    data = {
        'osm_id':       response['id'],
        'regional_key': response['tags']['de:regionalschluessel'],
    }

    # Add name with prefix if it exists
    if 'name:prefix' in response['tags']:
        n = []
        n.append(response['tags']['name:prefix'])
        n.append(' ')
        n.append(data['name'])
        data['name'] = ''.join(n)
    else:
        data['name'] = response['tags']['name']

    return data

def get_area_geometry(regional_key):
    """Get area geometry for a regional key."""

    # Resolve a regional key to OSM relation data
    data = resolve_reg_key(regional_key)
    osm_id = data['osm_id']
    name = data['name']

    # Get the relation's geometry data
    query = f"""
        [out:json];
        (relation({osm_id}););
        out geom;
        """
    response = query_overpass(query)

    # If the response is empty, raise an error
    if not response['elements']:
        raise ValueError("Invalid OSM ID.")
    
    # If the response contains more than one result, raise an error
    if len(response['elements']) > 1:
        raise ValueError("Multiple results for OSM ID.")
    
    # If the result is not a relation, raise an error
    if response['elements'][0]['type'] != 'relation':
        raise ValueError("No relation found for OSM ID.")
    
    # If the response contains no geometry, raise an error
    if 'geometry' not in response['elements'][0]:
        raise ValueError("No geometry found for relation.")
    
    # If the response contains no name or id, raise an error
    if 'name' or 'id' not in response['elements'][0]['tags']:
        raise ValueError("No name or id found for relation.")

    # If the IDs from the request and the result do not match, raise an error
    if osm_id != response['elements'][0]['id']:
        raise ValueError("IDs from request and result do not match.")
    
    # -> we can safely access the object
    
    # Convert the response to GeoJSON
    result = o2g.json2geojson(response)['features'][0]['geometry']

    # Create a GeoDataFrame from the GeoJSON
    area_geom = gpd.read_file(json.dumps(result), driver='GeoJSON')

    # Add the regional key and name to the GeoDataFrame
    area_geom['regional_key'] = regional_key
    area_geom['name'] = name

    # If the area is a multipolygon, convert it to a polygon
    if area_geom.geom_type[0] == 'MultiPolygon':
        area_geom = area_geom.explode()
        area_geom = area_geom.reset_index(drop=True)

    return area_geom
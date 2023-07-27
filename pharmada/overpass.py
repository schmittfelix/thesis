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
    if not response['elements']:
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
    if not result['tags']['de:regionalschluessel']:
        raise ValueError("No regional key found for relation.")
    
    # Check if the regional keys from the request and the result match
    result_key = result['tags']['de:regionalschluessel']
    
    """ OSM regional key lenghts differ for Kreisfreie Städte and Kreise.
        Both use the first 5 digits of the Regionalschlüssel system, but for
        Kreisfreie Städte the key is stored as a full-size key with 12 digits.
        For Kreise, the key is stored as a short key with 5 digits.
        More information: https://wiki.openstreetmap.org/wiki/Key:de:regionalschluessel"""
    
    # Evaluates to True if the regional key is a short key
    short_key = regional_key[:5] == result_key

    # Evaluates to True if the regional key is a long key
    # (i.e. the short key with trailing zeros)
    long_key = f'{regional_key:0<12}' == result_key

    # if not short_key or long_key:
        # raise ValueError("Regional keys from request and result do not match.")
    
    # If the response contains no name or id, raise an error
    if not result['id'] or not result['tags']['name']:
        raise ValueError("No name or id found for relation.")
    
    # Result is valid, return it
    data = {
        'osm_id':       result['id'],
        'regional_key': result['tags']['de:regionalschluessel'],
    }

    # Add name with prefix if it exists
    if 'name:prefix' in result['tags']:
        n = []
        n.append(result['tags']['name:prefix'])
        n.append(' ')
        n.append(result['tags']['name'])
        data['name'] = ''.join(n)
    else:
        data['name'] = result['tags']['name']

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
    
    # Existance and singularity of the result is guaranteed at this point
    result = response['elements'][0]
    
    # If the result is not a relation, raise an error
    if result['type'] != 'relation':
        raise ValueError("No relation found for OSM ID.")
    
    # If the response contains no name or id, raise an error
    if 'id' not in result or 'name' not in result['tags']:
        raise ValueError("No name or id found for relation.")

    # If the IDs from the request and the result do not match, raise an error
    if osm_id != result['id']:
        raise ValueError("IDs from request and result do not match.")
    
    # If the response contains no geometry, raise an error
    if not result['members']:
        raise ValueError("No geometry found for relation.")
    
    # -> Result is valid, continue with geometry extraction

    # Extract the geometry from the response
    geometry = o2g.json2shapes(response)[0]['shape']
    
    # Convert the geometry to a GeoDataFrame
    area_geom = gpd.GeoDataFrame(geometry=[geometry], crs='EPSG:4326')

    # Add regional key and name to the GeoDataFrame
    area_geom['regional_key'] = regional_key
    area_geom['name'] = name

    # If the area is a multipolygon, convert it to a polygon
    if area_geom.geom_type[0] == 'MultiPolygon':
        area_geom = area_geom.explode(index_parts=False)
        area_geom = area_geom.reset_index(drop=True)

    return area_geom

def get_precise_geometry(regional_key, union=True):
    """Get precise customer areas for a regional key.
    
    This function differs from get_area_geometry() in that it returns
    a GeoDataFrame with more precise area boundaries to allow for 
    more realistic customer locations."""

    # Resolve a regional key to OSM relation data
    data = resolve_reg_key(regional_key)
    osm_id = data['osm_id']
    name = data['name']

    # Get a complete set of all realistic customer areas within the area
    query = f"""
        [out:json];
            
        //set up area given by regional_key as search boundary
        (
        relation({osm_id});
        map_to_area;
        ) ->.boundary;

        //get all ways and relations within the boundary that have one of the specified area tags.
        //The tags represent the majority of areas where customers are likely to be found, while excluding
        //areas that are unlikely to contain customers such as outdoor spaces and unrealistic areas like bodies of water.
        
                //ways and relations (wr) within the boundary
            wr(area.boundary)[
            
                //with 'landuse' or 'amenity' tag
            ~"^(landuse|amenity)$"

                //with one of the following values
            ~"^(residential|commercial|industrial|education|retail|institutional|
                school|university|hospital|kindergarten|college)$"
            
                // save results in set
            ]->.results;

            // output full geometry of the results set     
        .results out geom qt;
        """
    response = query_overpass(query)

    # If the response is empty, raise an error
    if not response['elements']:
        raise ValueError("Empty response.")

    # Extract the geometry from the response
    geometry = o2g.json2geojson(response)

    # Convert the geometry to a GeoDataFrame
    area_geom = gpd.GeoDataFrame.from_features(geometry, crs='EPSG:4326')

    # Drop unnecessary column 'nodes' if it exists
    if 'nodes' in area_geom.columns:
        area_geom.drop(columns=['nodes'], inplace=True)

    # Remove all tags except for name, landuse and amenity
    area_geom['tags'] = area_geom['tags'].apply(
        lambda tags: {key: tags[key] for key in ['name', 'landuse', 'amenity'] if key in tags}
        )
    
    # Unite the geometry to a single polygon
    if union:
        area_geom = gpd.GeoDataFrame(geometry=[area_geom.unary_union], crs='EPSG:4326')

        # Add metadata to the GeoDataFrame
        area_geom['regional_key'] = regional_key
        area_geom['name'] = name

    return area_geom

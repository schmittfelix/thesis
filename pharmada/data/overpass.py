"""Module for interacting with the Overpass API for OSM data.

The Overpass API provides performant access to OpenStreetMap data via its own query language.
More information: https://wiki.openstreetmap.org/wiki/Overpass_API

Functions:
    query_overpass: Query the Overpass API and return the JSON result.
    regkey_to_osm_id: Resolve a German "Regionalschlüssel" to an OSM relation ID.
    get_area_geometry: Return the geometry of an area identified by a RegKey.
    get_precise_geometry: Get precise possible customer sub-areas for a total area.
"""

from pharmada.data.regkey import RegKey
import requests as req
import osm2geojson as o2g


def query_overpass(query: str) -> dict:
    """Query the Overpass API and return the JSON result.

    Parameters:
        query (str): The query to be sent to the Overpass API.

    Returns:
        response (dict): The JSON response from the Overpass API.

    Raises:
        ValueError: If the response is empty or contains an error.
    """

    overpass_url = "https://overpass-api.de/api/interpreter"
    response = req.get(overpass_url, params={"data": query}).json()

    return response


def regkey_to_osm_id(RegKey: RegKey) -> int:
    """Resolve a German "Regionalschlüssel" to an OSM relation ID.

    Parameters:
        RegKey (pharmada.regkey.RegKey): A valid RegKey object.

    Returns:
        osm_id (int): The OSM relation ID of the area identified by the RegKey.

    Raises:
        ValueError: If the RegKey is invalid or ambiguous.
    """

    """ OSM regional key lenghts differ for Kreisfreie Städte and Kreise.
        Both use the first 5 digits of the Regionalschlüssel system, but for
        Kreisfreie Städte the key is stored as a full-size key with 12 digits.
        For Kreise, the key is stored as a short key with 5 digits.
        More information: https://wiki.openstreetmap.org/wiki/Key:de:regionalschluessel"""
    long_regkey = f"{RegKey.regkey:0<12}"

    # Search OSM data for a relation tagged with the regional key
    query = f"""
        [out:json];
        (relation["de:regionalschluessel"="{RegKey.regkey}"];);
        out tags;
        """
    response = query_overpass(query)

    # If the response is empty, try again with the long key
    if not response["elements"]:
        query = f"""
            [out:json];
            (relation["de:regionalschluessel"="{long_regkey}"];);
            out tags;
            """
        response = query_overpass(query)

    # Check response for existence and singularity of the result

    # If the response is still empty, raise an error
    if not response["elements"]:
        raise ValueError("Invalid regional key.")

    # If the response contains more than one result, raise an error
    if len(response["elements"]) > 1:
        raise ValueError("Multiple results for regional key.")

    # we can safely access the first element at this point
    result = response["elements"][0]

    # If the result is not a relation, raise an error
    if result["type"] != "relation":
        raise ValueError("No relation found for regional key.")

    # If the response contains no regional key, raise an error
    if not result["tags"]["de:regionalschluessel"]:
        raise ValueError("No regional key found for relation.")

    # Check if the regional keys from the request and the result match
    result_key = result["tags"]["de:regionalschluessel"]

    # Evaluates to True if the result key is a short key
    short_key = RegKey.regkey == result_key

    # Evaluates to True if the result key is a long key
    # (i.e. the short key with trailing zeros)
    long_key = long_regkey == result_key

    if not (short_key or long_key):
        raise ValueError("RegKeys from request and result do not match.")

    # If the response contains no name or id, raise an error
    if not result["id"]:
        raise ValueError("No name or id found for relation.")

    # result is valid, return it
    osm_id = result["id"]
    return osm_id


def get_relation_geometry(osm_id: int) -> dict:
    """Get area geometry for a regional key.

    Parameters:
        osm_id (int): The OSM relation ID of the area to get geometry for.

    Returns:
        geometry (dict): A GeoJSON dictionary containing the area geometry.

    Raises:
        ValueError: If the OSM ID is invalid or ambiguous.
        ValueError: If the OSM ID is not a relation.
        ValueError: If the OSM IDs from the request and the result do not match.
        ValueError: If the result contains no name or id.
        ValueError: If the result contains no geometry.
    """

    # Get the relation's geometry data
    query = f"""
        [out:json];
        (relation({osm_id}););
        out geom;
        """
    response = query_overpass(query)

    # If the response is empty, raise an error
    if not response["elements"]:
        raise ValueError("Invalid OSM ID.")

    # If the response contains more than one result, raise an error
    if len(response["elements"]) > 1:
        raise ValueError("Multiple results for OSM ID.")

    # Existance and singularity of the result is guaranteed at this point
    result = response["elements"][0]

    # If the result is not a relation, raise an error
    if result["type"] != "relation":
        raise ValueError("No relation found for OSM ID.")

    # If the response contains no id, raise an error
    if "id" not in result:
        raise ValueError("No id found for relation.")

    # If the IDs from the request and the result do not match, raise an error
    if osm_id != result["id"]:
        raise ValueError("IDs from request and result do not match.")

    # If the response contains no geometry, raise an error
    if not result["members"]:
        raise ValueError("No geometry found for relation.")

    # -> Result is valid, extract the geometry

    # Extract the geometry from the response
    # (o2g needs the raw response due to a hardcoded access to the 'elements' key in _json2shapes)
    geometry = o2g.json2geojson(response)

    return geometry


def get_precise_geometry(osm_id: int) -> dict:
    """Get precise possible customer areas for a regional key.

    This function differs from get_area_geometry() in that it returns a GeoDataFrame with more precise
    area boundaries for all areas where customers usually originate to allow for more realistic
    customer locations.

    Parameters:
        osm_id (int): The OSM relation ID of the area to get geometry for.

    Returns:
        geometry (dict): A GeoJSON dictionary containing the area geometry.
    Raises:
        ValueError: If the query returns no results.
    """

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
            ~"^(residential|commercial|industrial|education|retail|institutional|school|university|hospital|kindergarten|college)$"
            
                // save results in set
            ]->.results;

            // output full geometry of the results set     
        .results out geom qt;
        """
    response = query_overpass(query)

    # If the response is empty, raise an error
    if len(response["elements"]) == 0:
        raise ValueError("Empty response.")

    # Extract the geometry from the response
    geometry = o2g.json2geojson(response)

    return geometry

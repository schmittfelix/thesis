"""Get all pharmacies within an area.

Area boundaries are extracted from OSM.
Pharmacy location, name and reference ID are retreived from GMaps.
"""

import json
import time
import ftfy
import requests as req
import geopandas as gpd

def pharmacies_in_area(area, gmaps_key):
    """Get all pharmacies within an area."""

    # get area IDs
    gmaps_id, osm_id = _get_area_ids(area, gmaps_key)

    # get area geometry
    area_geom = _get_area_geometry(osm_id)

    # calculate area radius
    area_radius = _calculate_area_radius(area_geom)

    # get pharmacies
    found_pharmacies = _fetch_pharmacies(area_geom, area_radius, gmaps_key)

    # filter pharmacies
    pharmacies = _filter_pharmacies(found_pharmacies, area_geom)

    return pharmacies



def _get_area_ids(area, gmaps_key):
    """Geocode area to GMaps and OSM IDs."""

    # Google Maps
    gmaps_id_url = f'https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={area}&inputtype=textquery&key={gmaps_key}'
    gmaps_id = req.get(gmaps_id_url).json()['candidates'][0]['place_id']

    # OpenStreetMap
    osm_id_url = f'https://nominatim.openstreetmap.org/search?q={area}&format=json&polygon_geojson=1&addressdetails=1'
    osm_id = req.get(osm_id_url).json()[0]['osm_id']

    return gmaps_id, osm_id

def _get_area_geometry(area_osm_id):
    """Get area centroid and boundaries from OSM."""

    osm_geo_url = f'https://nominatim.openstreetmap.org/lookup?osm_ids=R{area_osm_id}&format=json&polygon_geojson=1'
    osm_geo_response = req.get(osm_geo_url).json()
    area_geom = gpd.read_file(json.dumps(osm_geo_response[0]['geojson']), driver='GeoJSON')

    return area_geom

def _calculate_area_radius(area_geom):
    """Calculate area radius from boundaries."""

    area_geom = area_geom.to_crs(area_geom.estimate_utm_crs())

    refpoints = (
        gpd.GeoSeries(gpd.points_from_xy([area_geom.geometry.bounds.maxx[0]], [area_geom.geometry.bounds.maxy[0]])),
        gpd.GeoSeries(gpd.points_from_xy([area_geom.geometry.bounds.minx[0]], [area_geom.geometry.bounds.maxy[0]])),
        gpd.GeoSeries(gpd.points_from_xy([area_geom.geometry.bounds.maxx[0]], [area_geom.geometry.bounds.miny[0]])),
        gpd.GeoSeries(gpd.points_from_xy([area_geom.geometry.bounds.minx[0]], [area_geom.geometry.bounds.miny[0]]))
    )
    
    for refpoint in refpoints:
        refpoint.crs = area_geom.crs

    distances = []
    for refpoint in refpoints:
        distances.append(area_geom.centroid.distance(refpoint)[0].round(0))
    
    area_radius = max(distances)

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
        pharmacy_location = gpd.GeoSeries(gpd.points_from_xy([pharmacy['geometry']['location']['lng']], [pharmacy['geometry']['location']['lat']]))
        pharmacy_location.crs = area_geom.crs

        if not area_geom.contains(pharmacy_location)[0]:
            continue

        # check if pharmacy name contains "apotheke" or "pharmacy" to filter results wrongly classified as pharmacies
        if not any(x in pharmacy['name'].lower() for x in ['apotheke', 'pharmacy']):
            continue

        # extract location, name and id from results
        ph = {}
        ph['name'] = ftfy.fix_text(pharmacy['name'])
        ph['id'] = pharmacy['place_id']
        ph['location'] = pharmacy['geometry']['location']

        pharmacies.append(ph)

    return pharmacies


if __name__ == '__main__':
    greeting = f"""    This script will fetch all pharmacies within a given area from Google Maps.
    Please input your desired area as well as your Google Maps API key."""
    print(greeting)

#    area = input('Area: ')
#    sys.stdout.write("\033[F")

#    gmaps_key = input('Google Maps API key: ')
#    sys.stdout.write("\033[F")

    area = "Würzburg"
    gmaps_key = "AIzaSyD1t4K3GksCdP_g3kIu5iG1iPDCtYGzi-E"

    pharmacies = pharmacies_in_area(area, gmaps_key)

    num_pharmacies = f'{len(pharmacies)} pharmacies found.\n'
    print(num_pharmacies)

    print('Would you like to save the results to a file?')
    save = input('y/n: ')

    if save == 'y':
        with open('pharmacies.json', 'w') as f:
            json.dump(pharmacies, f)
        print('Saved to pharmacies.json')
    else:
        print('Results not saved.')

    print('Done.')
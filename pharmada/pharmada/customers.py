"""Generate randomized but realistic customers for the Pharma VRP.

"""
import pandas as pd
import re
import requests as req
import geopandas as gpd
import numpy as np
import json

inhabitants = 84,3e6
unit_volume = 852e6
total_cost = 51,21e9

class Customer:
    def __init__(self, address):
        self.address = address

def get_demand (area):
    """Get population size for a given area.
    
    This function uses population data from the GENESIS-Online database for all German "Kreise"."""

    # Read in the data from a dedicated csv file
    df = pd.read_csv('12411-0015-KREISE_$F_flat.csv', sep=';', encoding = "ISO-8859-1", index_col='1_Auspraegung_Label')
    
    # Drop unnecessary columns
    df = df.drop(columns=[
        'Statistik_Code', 'Statistik_Label', 'Zeit_Code', 'Zeit_Label', 'Zeit',
        '1_Merkmal_Code', '1_Auspraegung_Code', '1_Merkmal_Label'
        ])
    
    # Rename columns
    df.rename({'BEVSTD__Bevoelkerungsstand__Anzahl': 'population'}, axis=1, inplace=True)
    df.rename({'1_Auspraegung_Label': 'area'}, axis=0, inplace=True)
    
    # Remove ", Landkreis" and ", kreisfreie Stadt" from area names
    df.index = df.index.map(lambda label: re.sub(r',\s*(?:Landkreis|kreisfreie Stadt)', '', label))

    # Convert to dictionary
    population = df.to_dict()['population']

    return population[area] * (unit_volume / inhabitants)

def generate_addresses (area, size, gmaps_api_key):
    """Generate random addresses within an area."""
    
    # Get the OSM ID for the area
    osm_id_url = f'https://nominatim.openstreetmap.org/search?q={area}&format=json&polygon_geojson=1&addressdetails=1'
    osm_id = req.get(osm_id_url).json()[0]['osm_id']

    # Get the geometry for the area
    osm_geo_url = f'https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1'
    osm_geo_response = req.get(osm_geo_url).json()
    area_geom = gpd.read_file(json.dumps(osm_geo_response[0]['geojson']), driver='GeoJSON')

    # Get the bounds of the area
    xmin, ymin, xmax, ymax = area_geom.total_bounds

    # Generate random points within the bounds
    x = np.random.uniform(xmin, xmax, size)
    y = np.random.uniform(ymin, ymax, size)

    points = gpd.GeoSeries(gpd.points_from_xy(x, y))
    points = points[points.within(area_geom.unary_union)]

    # Create a dictionary of real addresses from the points
    addresses = {}

    for point in points:
        # Geocode with the GMaps API
        geocode_url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={point["geometry"].y[0]},{point["geometry"].x[0]}&key={gmaps_api_key}'
        geocode_response = req.get(geocode_url).json()

        # Geolocate (reverse Geocode) the address to get exact latlong coordinates
        geolocate_url = f'https://maps.googleapis.com/maps/api/geocode/json?address={geocode_response["results"][0]["formatted_address"]}&key={gmaps_api_key}'
        geolocate_response = req.get(geolocate_url).json()

        # Add the address to the dictionary
        addresses[geocode_response['results'][0]['formatted_address']] = geolocate_response['results'][0]['geometry']['location']        

if __name__ == "__main__":
    print(get_demand('Würzburg'))
    print(generate_addresses('Würzburg', 10, 'AIzaSyD1t4K3GksCdP_g3kIu5iG1iPDCtYGzi-E'))

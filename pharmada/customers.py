"""Generate randomized but realistic daily customers for the Pharma VRP.

"""
import overpass as op
import pandas as pd
import requests as req
import geopandas as gpd
import numpy as np

# Values taken from DeStatis and "Die Apotheke (2022)"
inhabitants = 84.3e6
unit_volume = 1.288e9
total_cost = 54.66e9

class Customer:
    def __init__(self, address):
        self.address = address

def generate_customers(regional_key, gmaps_key):

    # Determine the number of customers to generate
    count = get_demand(regional_key)

    # Generate addresses for the customers
    addresses = generate_addresses(regional_key, count, gmaps_key)

    
    return customers

def get_demand (regional_key):
    """Calculate yearly pharmaceutical demand for a given area.
    
    This function requires a valid German "Regionalschlüssel" as input."""

    # Read in the data from a dedicated csv file
    df = pd.read_csv('./data/population_by_kreise.csv', sep=';',
                     header=0, index_col=0, encoding='utf-8', converters={'regional_key': str}, engine='python')    
    
    #Population in area * (total volume / total population)
    demand = df.loc[regional_key, 'total'] * (unit_volume / inhabitants)

    return demand.round(0)

def generate_addresses (regional_key, count, gmaps_key):
    """Generate random addresses within an area."""

    # Get the area geometry
    area_geom = op.get_area_geometry(regional_key)

    # Get the bounds of the area
    xmin, ymin, xmax, ymax = area_geom.total_bounds

    # Generate random points within the bounds
    x = np.random.uniform(xmin, xmax, count)
    y = np.random.uniform(ymin, ymax, count)

    points = gpd.GeoSeries(gpd.points_from_xy(x, y))
    points = points[points.within(area_geom.unary_union)]

    # Create a dictionary of real addresses from the points
    addresses = {}

    for point in points:
        # Geocode with the GMaps API
        geocode_url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={point["geometry"].y[0]},{point["geometry"].x[0]}&key={gmaps_key}'
        geocode_response = req.get(geocode_url).json()

        # Geolocate (reverse Geocode) the address to get exact latlong coordinates
        geolocate_url = f'https://maps.googleapis.com/maps/api/geocode/json?address={geocode_response["results"][0]["formatted_address"]}&key={gmaps_key}'
        geolocate_response = req.get(geolocate_url).json()

        # Add the address to the dictionary
        addresses[geocode_response['results'][0]['formatted_address']] = geolocate_response['results'][0]['geometry']['location']
"""Generate randomized but realistic daily customers for the Pharma VRP.

    Currently, the customer generation is based on the following assumptions:
    - proportional pharmaceutical demand is equal to the area's population share
    - all customers buy one unit of pharmaceuticals per day
    - all customers are located in random spots within the area's boundaries
      (realistic addresses are not yet implemented)"""

import math
import pharmada.overpass as op
import pandas as pd
import requests as req
import geopandas as gpd
import numpy as np

# Values taken from DeStatis and "Die Apotheke (2022)"
population = 84.3e6
unit_volume = 1.288e9
total_cost = 54.66e9

def generate_customers(regional_key, gmaps_key):

    # Determine the number of customers to generate
    count = get_demand(regional_key)

    # Generate random addresses within the area
    addresses = generate_locations(regional_key, count)

def get_demand (regional_key):
    """Calculate daily pharmaceutical demand for a given area.
    
    This function requires a valid German "Regionalschlüssel" as input."""

    # Read in the data from a dedicated csv file
    df = pd.read_csv('./data/population_by_kreise.csv', sep=';',
                     header=0, index_col=0, encoding='utf-8', converters={'regional_key': str}, engine='python')    
    
    #Yearly demand: Population in area * (overall yearly volume / total population)
    yearly_demand = df.loc[regional_key, 'total'] * (unit_volume / population)

    #Return daily demand rounded to the nearest integer
    daily_demand = round(yearly_demand / 365)
    
    return math.trunc(daily_demand)

def generate_locations (regional_key, count):
    """Generate random addresses within an area."""

    # Get the area geometry
    area_geom = op.get_area_geometry(regional_key)

    points = area_geom.sample_points(count)
    
    #TODO: Validate addresses and constrict to residential areas

    return points
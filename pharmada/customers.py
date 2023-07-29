"""Generate randomized but realistic daily customers for the Pharma VRP.

    Currently, the customer generation is based on the following assumptions:
    - proportional pharmaceutical demand is equal to the area's population share
    - all customers buy one unit of pharmaceuticals per day
    - all customers are located in random spots within realistic sub-areas of the total area
      (e.g. residential areas, commercial areas, not in outdoor spaces or bodies of water)
    """

import math
import pharmada.overpass as op
import pharmada.regkey as rk
import pharmada.geometry as geo
import pandas as pd
import geopandas as gpd

# Values taken from DeStatis and "Die Apotheke (2022)"
POPULATION = 84.3e6
UNIT_VOLUME = 1.288e9
TOTAL_COST = 54.66e9

class Customers:
    """A collection of customers."""

    def __init__(self, RegKey: rk.RegKey):
        """Initialize a collection of customers."""

        self.customers = generate_customers(RegKey)

    def __repr__(self):
        """Return a string representation of the customers."""

        return f"Customers: {self.customers}"

    def __str__(self):
        """Return a string representation of the customers."""

        return f"Customers: {self.customers}"

    def __iter__(self):
        """Return an iterator over the customers."""

        return iter(self.customers)

    def __len__(self):
        """Return the number of customers."""

        return len(self.customers)

    def __getitem__(self, index):
        """Return the customer at the given index."""

        return self.customers[index]

    def __setitem__(self, index, value):
        """Set the customer at the given index to the given value."""

        self.customers[index] = value

    def __delitem__(self, index):
        """Delete the customer at the given index."""

        del self.customers[index]

    def __contains__(self, value):
        """Return whether the customers contain the given value."""

        return value in self.customers

    def __add__(self, other):
        """Return the union of the customers and the other customers."""

        return Customers(self.customers + other.customers)

    def __iadd__(self, other):
        """Add the other customers to the customers."""

        self.customers += other.customers
        return self

    def __mul__(self, other):
        """Return the customers repeated the given number of times."""

        return Customers(self.customers * other)

    def __imul__(self, other):
        """Repeat the customers the given number of times."""

        self.customers *= other
        return self

    def __eq__(self, other):
        """Return whether the customers are equal to the other customers."""

        return self.customers == other.customers

    def __ne__(self, other):
        """Return whether the customers are not equal to the other customers."""

        return self.customers != other.customers

    def __lt__(self, other):
        """Return whether the customers are less than the other customers."""

        return self.customers < other.customers

    def __le__(self, other):
        """Return whether the customers are less than or equal to the other customers."""
            
        return self.customers <= other.customers

def generate_customers(RegKey: rk.RegKey) -> gpd.GeoSeries:

    # Determine the number of customers to generate
    count = get_demand(RegKey)

    # Generate random addresses within the area
    points = generate_locations(RegKey, count)

    return points

def get_demand (RegKey) -> int:
    """Calculate daily pharmaceutical demand for a given area."""

    regkey = RegKey.regkey
    
    # Read in the data from a dedicated csv file
    df = pd.read_csv('./data/kreise_data.csv', sep=';',
                     header=0, index_col=0, encoding='utf-8', converters={'regional_key': str}, engine='python')    
    
    #Yearly demand: Population in area * (overall yearly volume / total population)
    yearly_demand = df.loc[regkey, 'total'] * (UNIT_VOLUME / POPULATION)

    #Return daily demand rounded to the nearest integer
    daily_demand = round(yearly_demand / 365)
    
    return math.trunc(daily_demand)

def generate_locations (AreaGeometry: geo.AreaGeometry, count: int) -> gpd.GeoSeries:
    """Generate random addresses within an area."""

    # Get the precise area geometry from the given AreaGeometry object
    area_geom = AreaGeometry.precise_geometry

    points = area_geom.sample_points(count)
    
    #TODO: Validate addresses with either Google Maps API (could run into rate limits) or OpenStreetMap Nominatim (probably best to host own instance)

    return points
"""Module for the generation of randomized but realistic daily customers for the Pharma VRP.

    Currently, the customer generation is based on the following assumptions:
    - proportional pharmaceutical demand is equal to the area's population share
    - all customers buy one unit of pharmaceuticals per day
    - all customers are located in random spots within realistic sub-areas of the total area
      (e.g. residential areas, commercial areas, not in outdoor spaces or bodies of water)
    """

import math
import pharmada.geometry as geo
import pandas as pd
import geopandas as gpd

# Values taken from DeStatis and "Die Apotheke (2022)"
POPULATION = 84.3e6
UNIT_VOLUME = 1.288e9
TOTAL_COST = 54.66e9

class Customers:
    """A collection of customers.
    
    Attributes:
        AreaGeometry (geo.AreaGeometry): The area to generate customers for.
        customers (gpd.GeoSeries): A GeoSeries containing the customers.
        
    Methods:
        __init__:   Initialize a collection of customers.
        __str__:    Return information about the Customers object.
        __repr__:   Return all information about the Customers object.
    """

    __slots__ = ['_AreaGeometry', '_customers']

    def __init__(self, AreaGeometry: geo.AreaGeometry) -> None:
        """Initialize a collection of customers.
        
        Parameters:
            AreaGeometry (geo.AreaGeometry): The area to generate customers for.
        
        Returns:
            None
            
        Raises:
            None
        """

        # check if AreaGeometry is valid
        if not isinstance(AreaGeometry, geo.AreaGeometry):
            raise TypeError("AreaGeometry must be an instance of AreaGeometry.")
        
        self.AreaGeometry = AreaGeometry
        self._customers = generate_customers(self.AreaGeometry)

    def reset(self) -> None:
        """Reset the customers GeoDataFrame.
        
        Parameters:
            None
            
        Returns:
            None
            
        Raises:
            None
        """

        self._customers = generate_customers(self.AreaGeometry)

    def __str__(self) -> str:
        """Return information about the Customers object."""

        return f'Customers in {self.AreaGeometry.RegKey}'
    
    def __repr__(self) -> str:
        """Return all information about the Customers object."""

        return f'Customers in {self.AreaGeometry.RegKey}.\n{self.customers.info()}'
    
    @property
    def AreaGeometry(self) -> geo.AreaGeometry:
        """Return the area to generate customers for."""
        return self._AreaGeometry
    
    @AreaGeometry.setter
    def AreaGeometry(self, AreaGeometry: geo.AreaGeometry) -> None:
        """Set the area to generate customers for."""

        # check if AreaGeometry is valid
        if not isinstance(AreaGeometry, geo.AreaGeometry):
            raise TypeError("AreaGeometry must be an instance of AreaGeometry.")
        
        self._AreaGeometry = AreaGeometry

        # update customers GeoSeries when RegKey is changed
        self._customers = generate_customers(self.AreaGeometry)

    @AreaGeometry.deleter
    def AreaGeometry(self) -> None:
        """Protect AreaGeometry and warn user."""
        raise AttributeError("AreaGeometry must not be deleted, change it instead.")

    @property
    def customers(self) -> gpd.GeoSeries:
        """Return a GeoSeries containing the customers."""
        return self._customers
    
    @customers.setter
    def customers(self) -> None:
        """Protect customers and warn user."""
        raise AttributeError("customers must not be changed, change AreaGeometry instead.")
    
    @customers.deleter
    def customers(self) -> None:
        """Protect customers and warn user."""
        raise AttributeError("customers must not be deleted, change AreaGeometry instead.")

def generate_customers(AreaGeometry: geo.AreaGeometry) -> gpd.GeoDataFrame:
    """Generate randomized but realistic daily customers for a given area.
    
    Parameters:
        AreaGeometry (geo.AreaGeometry): The area to generate customers for.
        
    Returns:
        gpd.GeoDataFrame: A GeoDataFrame containing the generated customers.
        
    Raises:
        None
    """

    # Determine the number of customers to generate
    count = get_demand(AreaGeometry)

    # Generate random addresses within the area
    points = generate_locations(AreaGeometry, count)

    # add metadata to the GeoSeries
    points['regkey'] = AreaGeometry.RegKey.regkey
    points['name'] = AreaGeometry.RegKey.name

    return points

def get_demand (AreaGeometry: geo.AreaGeometry) -> int:
    """Calculate daily pharmaceutical demand for a given area.
    
    Parameters:
        AreaGeometry (geo.AreaGeometry): The area to calculate demand for.
        
    Returns:
        int: The daily pharmaceutical demand for the given area.
        
    Raises:
        None
    """

    # Get the area's regional key
    regkey = AreaGeometry.regkey
    
    # Read in the data from a dedicated csv file
    df = pd.read_csv('./data/kreise_data.csv', sep=';',
                     header=0, index_col=0, encoding='utf-8', converters={'regional_key': str}, engine='python')    
    
    #Yearly demand: Population in area * (overall yearly volume / total population)
    yearly_demand = df.loc[regkey, 'population'] * (UNIT_VOLUME / POPULATION)

    #Return daily demand rounded to the nearest integer
    daily_demand = round(yearly_demand / 365)
    
    return math.trunc(daily_demand)

def generate_locations (AreaGeometry: geo.AreaGeometry, count: int) -> gpd.GeoDataFrame:
    """Generate random addresses within an area.
    
    Parameters:
        AreaGeometry (geo.AreaGeometry): The area to generate addresses for.
        count (int): The number of addresses to generate.
        
    Returns:
        gpd.GeoSeries: A GeoSeries containing the generated addresses.
        
    Raises:
        None
    """

    # Unite all sub-areas in the AreaGeometry's precise geometry into one geometry
    AreaGeometry.unite_precise_geometry()

    # Get the precise area geometry from the given AreaGeometry object
    area_geom = AreaGeometry.precise_geometry

    # Generate random points within the area
    samples = area_geom.sample_points(count)

    # Convert the GeoSeries to a GeoDataFrame and set the crs
    points = gpd.GeoDataFrame(geometry=samples)
    points.crs = area_geom.crs

    # Explode the MultiPoint into single Points
    points = points.explode(ignore_index=True, inplace=True)
    
    #TODO: Possibly validate addresses with Nominatim-style algorithm

    return points
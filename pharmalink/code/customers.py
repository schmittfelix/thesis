"""Module for the generation of randomized but realistic daily customers for the Pharmalink VRP.

    Currently, the customer generation is based on the following assumptions:
    - proportional yearly pharmaceutical demand is equal to the area's population share
    - daily demand is calculated as a fraction of the yearly demand
    - each customer buys one unit of pharmaceuticals (daily demand = number of customers)
    - customers are distributed across the area based on population density and realistic residential areas
    
    Classes:
        Customers: A collection of customers.
        
    Functions:
        generate_customers: Generate randomized but realistic daily customers for a given area.
        get_demand: Calculate daily pharmaceutical demand for a given area.
        
    Constants:
        POPULATION: The total population of Germany.
        UNIT_VOLUME: The total yearly pharmaceutical volume in Germany.
        TOTAL_COST: The total yearly pharmaceutical cost in Germany.
    """

import math
import pharmalink.code.area as area
import pharmalink.code.sources as src
import random
import pandas as pd
import geopandas as gpd
import folium as fl
from statistics import mean


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

    __slots__ = ["_area", "customers"]

    def __init__(self, customer_area: area.Area) -> None:
        """Initialize a collection of customers.

        Parameters:


        Returns:
            None

        Raises:
            None
        """

        # check if Area is valid
        if not isinstance(customer_area, area.Area):
            raise TypeError("Area must be an instance of area.Area.")

        self._area = customer_area
        self.customers = self._generate_customers(self._area)

    def __str__(self) -> str:
        """Return information about the Customers object."""

        return f"Customers for {self._area.full_name} ({self._area.regkey})"

    def __repr__(self) -> str:
        """Return all information about the Customers object."""

        return f"Customers (Area: {self._area.full_name} ({self._area.regkey}), Customers: {len(self.customers)})"

    def plot(self, **kwargs) -> fl.Map:
        """Plot the area geometry.

        Args:
            **kwargs: Keyword arguments passed to the plot functions.

        Returns:
            None

        Raises:
            None
        """

        customers = self.customers

        # Set CRS to EPSG:4326 for folium
        customers = customers.to_crs(epsg=4326)

        # Setup of the map's bounds
        bounds = customers.total_bounds
        x = mean([bounds[0], bounds[2]])
        y = mean([bounds[1], bounds[3]])
        viewport_center = (y, x)

        # Setup of the map
        map_args = {
            "location": viewport_center,
            "width": "100%",
            "height": "100%",
            "tiles": "cartodbpositron",
            "min_zoom": 8,
            "max_zoom": 18,
            "control_scale": False,
            "zoom_control": False,
        }

        map = fl.Map(**map_args)

        # fit map to bounds for nice display
        map.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

        style_args = {}

        customer_marker_args = {
            "radius": 2,
            "color": "green",
            "fill": True,
            "fillOpacity": 1.0,
            "weight": 1,
        }

        # Setup of the map content
        area_args = {
            "data": self._area.geometry,
            "name": self._area.full_name,
            "regkey": self._area.regkey,
        }

        customer_args = {
            "data": customers,
            "name": "Customers",
            "marker": fl.CircleMarker(**customer_marker_args),
        }

        # Add the area and customers to the map
        fl.GeoJson(**area_args, **style_args).add_to(map)
        fl.GeoJson(**customer_args, **style_args).add_to(map)

        # Return the map
        return map

    def _generate_customers(self, area: area.Area) -> gpd.GeoDataFrame:
        """Generate randomized but realistic daily customers for a given area.

        Parameters:
            AreaGeometry (geo.AreaGeometry): The area to generate customers for.

        Returns:
            gpd.GeoDataFrame: A GeoDataFrame containing the generated customers.

        Raises:
            None
        """

        # suppress FutureWarnings due to an upcoming change in GeoPandas
        # # (which will also necessitate a change in the code)
        # import warnings

        # warnings.filterwarnings("ignore", category=FutureWarning)

        residential_areas = src.ResidentialAreas.get_within_area(area)
        residential_areas = residential_areas.unary_union

        population_grid = src.PopulationGrids.get_within_area(area)

        # Scale the population values to match the area's total population
        # Differences can occur due to statistical obfuscation and clipping of the cells to the area boundaries
        scale_factor = area.population / population_grid["population"].sum()

        population_grid["population"] = population_grid.apply(
            lambda row: row["population"] * scale_factor, axis=1
        )

        total_pop = area.population

        # determine the number of customers to generate
        demand = get_daily_demand(area)

        customers = gpd.GeoSeries()

        # Diff is the number of customers that still need to be drawn.
        # It is initialized with the total demand and later calculated as the difference
        # between demand and the number of customers generated so far.
        # The loop runs until the difference is less than 1% of demand.
        diff = demand
        while diff > 0:  # demand * 0.01:
            # calculate the number of customers to sample for each grid cell
            cell_customers = []
            for _, row in population_grid.iterrows():
                # expected number = (cell population / total population) * sample size
                expected_customers = (row["population"] / total_pop) * diff

                # split the expected number into an integer and a decimal part
                decimal_part, int_part = math.modf(expected_customers)

                actual_customers = int_part

                # additional customer with the probability of decimal_part
                if random.random() < decimal_part:
                    actual_customers += 1

                cell_customers.append(int(actual_customers))

            # set 0 for all list entries with NaN
            cell_customers = [0 if math.isnan(x) else x for x in cell_customers]

            # sample the determined number of customers for each grid cell
            customer_locs = population_grid.sample_points(cell_customers)

            # Remove all empty entries (= cells without customers) and explode the
            # MultiPoints into a single Point for each customer
            customer_locs.dropna(inplace=True)
            customer_locs = customer_locs.explode(ignore_index=True)
            customer_locs.reset_index(drop=True, inplace=True)

            # check if all customer locations are within the realistic residential areas
            # (i.e. not in the middle of a lake) and remove them if not
            # customer_locs = customer_locs[customer_locs.within(residential_areas)]
            customer_locs = customer_locs.iloc[
                customer_locs.sindex.query(residential_areas, predicate="contains")
            ]

            # add the new customers to the list of all customers
            customers = pd.concat([customers, customer_locs], ignore_index=True)
            customers.reset_index(drop=True, inplace=True)

            # calculate the new difference between demand and number of customers
            diff = demand - len(customers)

            if diff < 0:
                # sample exactly the number of customers needed from the too large customer list
                customers = customers.sample(demand)

        # convert the customers to a GeoDataFrame
        customers = gpd.GeoDataFrame(geometry=customers)
        customers.rename_geometry("location", inplace=True)

        return customers


def get_daily_demand(area: area.Area) -> int:
    """Calculate daily pharmaceutical demand for a given area.

    Parameters:
        area (area.Area): The area to calculate the daily demand for.

    Returns:
        int: The daily pharmaceutical demand for the given area.

    Raises:
        None
    """

    # Constants
    const = src.Constants()
    total_population = const.total_population
    total_medicine_units = const.total_medicine_units

    # Yearly demand: Population in area * (overall yearly volume / total population)
    yearly_demand = area.population * (total_medicine_units / total_population)

    # Return daily demand rounded to the nearest integer
    daily_demand = round(yearly_demand / 365, 0).astype(int)

    return daily_demand

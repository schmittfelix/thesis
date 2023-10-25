"""Module for the generation of randomized but realistic daily customers for the Pharma VRP.

    Currently, the customer generation is based on the following assumptions:
    - proportional pharmaceutical demand is equal to the area's population share
    - all customers buy one unit of pharmaceuticals per day
    - all customers are located in random spots within realistic sub-areas of the total area
      (e.g. residential areas, commercial areas, not in outdoor spaces or bodies of water)
    
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
import pharmada.data.geometry as geo
import random
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

    __slots__ = ["_AreaGeometry", "_customers"]

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

        self._AreaGeometry = AreaGeometry
        self._customers = generate_customers(self.AreaGeometry)

    def __str__(self) -> str:
        """Return information about the Customers object."""

        return f"Customers in {self.AreaGeometry.RegKey}"

    def __repr__(self) -> str:
        """Return all information about the Customers object."""

        return f"Customers in {self.AreaGeometry.RegKey}.\n{self.customers.info()}"

    @property
    def AreaGeometry(self) -> geo.AreaGeometry:
        """AreaGeometry object defining the area to generate customers for."""
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
        """Protect AreaGeometry object from being deleted and warn user."""
        raise AttributeError(
            "Customers.AreaGeometry must not be deleted, change it instead."
        )

    @property
    def customers(self) -> gpd.GeoSeries:
        """Customers within the area."""
        return self._customers

    @customers.setter
    def customers(self, value) -> None:
        """Protect customers from being set and warn user."""
        raise AttributeError(
            f'Customers.customers cannot be changed to "{value}", change AreaGeometry instead.'
        )

    @customers.deleter
    def customers(self) -> None:
        """Protect customers from being deleted and warn user."""
        raise AttributeError(
            "Customers.customers must not be deleted, change AreaGeometry instead."
        )


def generate_customers(AreaGeometry: geo.AreaGeometry) -> gpd.GeoDataFrame:
    """Generate randomized but realistic daily customers for a given area.

    Parameters:
        AreaGeometry (geo.AreaGeometry): The area to generate customers for.

    Returns:
        gpd.GeoDataFrame: A GeoDataFrame containing the generated customers.

    Raises:
        None
    """

    # suppress FutureWarnings due to an upcoming change in GeoPandas
    # (which will also necessitate a change in the code)
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)


    precise_geom = AreaGeometry.precise_geometry
    pop_cells = AreaGeometry.pop_cells

    # Calculate the relative population deviation between the 2011 Zensus data used
    # in the grid and the 2021 projection from the regkeys data for the area.
    # This is used to scale the demand for each grid cell according to population changes
    scale_factor = AreaGeometry.RegKey.population / pop_cells["population"].sum()

    pop_cells["population"] = pop_cells.apply(
        lambda row: row["population"] * scale_factor, axis=1
    )

    total_pop = pop_cells["population"].sum()
    # determine the number of customers to generate
    demand = get_demand(AreaGeometry)

    customers = gpd.GeoSeries()
    # Diff is the number of customers that still need to be drawn.
    # It is initialized with the total demand and later calculated as the difference
    # between demand and the number of customers generated so far.
    # The loop runs until the difference is less than 1% of demand.
    diff = demand
    while diff > demand * 0.01:
        # calculate the number of customers to sample for each grid cell
        cell_customers = []
        for _, row in pop_cells.iterrows():
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
        customer_locs = pop_cells.sample_points(cell_customers)

        # Remove all empty entries (= cells without customers) and explode the
        # MultiPoints into a single Point for each customer
        customer_locs.dropna(inplace=True)
        customer_locs = customer_locs.explode(ignore_index=True)
        customer_locs.reset_index(drop=True, inplace=True)

        # check if all customer locations are within plausible areas
        # (i.e. not in the middle of a lake) and remove them if not
        projected_precise_geom = precise_geom.to_crs(epsg=3035)
        plausible_areas = projected_precise_geom.unary_union
        customer_locs = customer_locs[customer_locs.within(plausible_areas)]
        customer_locs.reset_index(drop=True, inplace=True)

        # add the new customers to the list of all customers
        customers = pd.concat([customers, customer_locs], ignore_index=True)

        # calculate the new difference between demand and number of customers
        diff = demand - len(customers)

    # convert the customers to a GeoDataFrame
    customers = gpd.GeoDataFrame(geometry=customers)

    return customers


def get_demand(AreaGeometry: geo.AreaGeometry) -> int:
    """Calculate daily pharmaceutical demand for a given area.

    Parameters:
        AreaGeometry (geo.AreaGeometry): The area to calculate demand for.

    Returns:
        int: The daily pharmaceutical demand for the given area.

    Raises:
        None
    """

    # Get the area's population
    area_pop = AreaGeometry.RegKey.population

    # Yearly demand: Population in area * (overall yearly volume / total population)
    yearly_demand = area_pop * (UNIT_VOLUME / POPULATION)

    # Return daily demand rounded to the nearest integer
    daily_demand = round(yearly_demand / 365)

    return math.trunc(daily_demand)

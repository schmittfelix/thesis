"""Module for dealing with the various sources of data used in the pharmalink model.

This module exists to abstract the data source handling from the main codebase.

"""

from __future__ import annotations
from typing import List
from dataclasses import dataclass
import pharmalink.code.area as area
import importlib.resources as res
import lzma
import warnings
import pyogrio as pgr
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import json


@dataclass
class Constants:
    """Class for handling the project's constants."""

    # Source: Zensus2022 (via admin_areas and area.Area("00").population)
    total_population: int = (
        82711282  # total population of Germany at Zensus2022 cut-off date
    )

    # Source: "ABDA: GERMAN PHARMACIES – FIGURES, DATA, FACTS 2024, p. 31"
    yearly_pharmaceutical_units: int = (
        1.388e9  # total yearly pharmaceutical volume in Germany in 2023 in single units (blister, bottle, etc.)
    )

    # Source: "ABDA: GERMAN PHARMACIES – FIGURES, DATA, FACTS 2024, p. 31"
    daily_pharmaceutical_units: int = int(
        yearly_pharmaceutical_units
        / 365
        # total daily pharmaceutical volume in Germany in 2023 in single units
    )

    # Source: "ABDA: GERMAN PHARMACIES – FIGURES, DATA, FACTS 2024, p. 31, 64"
    fraction_of_pharmaceuticals_delivered_by_courier: float = round(
        300000 / daily_pharmaceutical_units, 4
    )  # average percentage of daily pharmaceuticals delivered by courier

    # Source: "PHAGRO: Pharmazeutischer Großhandel in Zahlen (www.phagro.de)"
    average_daily_deliveries_to_pharmacy: int = (
        3  # average daily deliveries to pharmacies in Germany
    )


class AdminAreas:
    """Class for handling data about German administrative areas.

    Parameters:
        None

    Attributes:
        None

    Methods:
        get_regkeys:    Get a list of all valid German Regionalschlüssel (regkeys).
        get_area_names: Get a DataFrame containing the names of all German administrative areas.
        get_areas:      Get information about all German administrative areas.
        get_area:       Get information about a German administrative area.
    """

    # compressed admin_areas GeoPackage in the sources subfolder
    path = res.files(__package__).joinpath("sources", "admin_areas.gpkg.xz")

    @classmethod
    def get_regkeys(cls) -> list:
        """Get a list of all valid German Regionalschlüssel (regkeys).

        Data source is an aggregated list of all German administrative areas.
        For more information, see: sources/admin_areas.

        Parameters:
            None

        Returns:
            regkeys (list): A list containing all valid German Regionalschlüssel.

        Raises:
            None
        """

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Decompress with lzma, then access with pyogrio.
        # Output will be a simple DataFrame because no Geometries are read
        with lzma.open(cls.path, "rb") as archive:
            regkeys = pgr.read_dataframe(
                archive, layer="admin_areas", columns=["regkey"], read_geometry=False
            )

        # Transform the DataFrame to a list
        regkeys = regkeys["regkey"].tolist()

        return regkeys

    @classmethod
    def get_area_names(cls) -> pd.DataFrame:
        """Get a DataFrame containing the names of all German administrative areas.

        Data source is an aggregated list of all German administrative areas.
        For more information, see: sources/admin_areas.

        Parameters:
            None

        Returns:
            names (pd.DataFrame): A DataFrame containing name and regkey for all areas.

        Raises:
            None
        """

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Decompress with lzma, then access with pyogrio.
        # Output will be a simple DataFrame because no Geometries are read
        with lzma.open(cls.path, "rb") as archive:
            names = pgr.read_dataframe(
                archive,
                layer="admin_areas",
                columns=["regkey", "full_name"],
                read_geometry=False,
            )

        names = names.set_index("regkey")

        return names["full_name"]

    @classmethod
    def get_areas(cls) -> gpd.GeoDataFrame:
        """Get information about all German administrative areas.

        Data source is an aggregated list of all German administrative areas.
        For more information, see: sources/admin_areas.

        Parameters:
            None

        Returns:
            areas (gpd.GeoDataFrame): A GeoDataFrame containing all German administrative areas.

        Raises:
            None
        """

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Decompress with lzma, then access with geopandas.
        # Output is a GeoDataFrame
        with lzma.open(cls.path, "rb") as archive:
            areas = gpd.read_file(archive, layer="admin_areas")

        # Set index to regkey to allow for quick filtering
        areas = areas.set_index("regkey")

        return areas

    @classmethod
    def get_area(cls, regkey: str) -> gpd.GeoDataFrame:
        """Get information about a German administrative area.

        Data source is an aggregated list of all German administrative areas.
        For more information, see: sources/admin_areas.

        Parameters:
            regkey (str): The regkey of the area to be retrieved.

        Returns:
            area (pd.Series): A Series containing information about the requested area.

        Raises:
            None
        """

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Decompress with lzma, then access with pyogrio.
        with lzma.open(cls.path, "rb") as archive:
            area = gpd.read_file(
                archive, layer="admin_areas", where=f"regkey = '{regkey}'"
            )

        # Check if area_data is a GeoDataFrame (= multiple entries for the regkey)
        if type(area) == gpd.GeoDataFrame:
            # Sort entries by level value in the order of "bundesland", "kreis", "gemeinde"
            area = area.sort_values(
                "level",
                key=lambda x: x.map({"bundesland": 1, "kreis": 2, "gemeinde": 3}),
            )

            # Return only the first entry as a filtered GeoDataFrame
            area = area.head(1)

        return area


class GeometryHandler:
    """Abstract Class for handling the project's geometry data."""

    # Source of the geometry data
    path = res.files(__package__).joinpath("sources")

    @classmethod
    def get_within_area(cls, filter_area: area.Area) -> gpd.GeoDataFrame:
        """Get all geometries within the given bounds.

        Parameters:
            filter_area (area.Area): The Area to filter the geometries by.
        """

        # Check if area is valid
        if not isinstance(filter_area, area.Area):
            raise TypeError("filter_area must be an instance of area.Area")

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Handle the edge case of the whole country
        if filter_area.level == "staat":
            return cls.get_all_entries()

        # Get the two-letter abbreviation for the Bundesland
        two_digits = f"{filter_area.regkey[:2]}"
        # Construct the path to the Bundesland-specific file
        file = cls.path.joinpath(f"{two_digits}.gpkg.xz")

        # Handle the edge case of a whole Bundesland
        if filter_area.level == "land":
            # Decompress with lzma, then access with geopandas.
            # Output is a GeoDataFrame
            with lzma.open(file, "rb") as archive:
                geometries = gpd.read_file(archive)

            return geometries

        # Only the underlying shapely geometry is used for the filter mask
        mask_geometry = filter_area.geometry.geometry[0]

        # The layer name is the name of the Bundesland the filter_area is in
        layer_name = filter_area.bundesland

        # Decompress with lzma, then access with geopandas.
        # Output is a GeoDataFrame
        with lzma.open(file, "rb") as archive:
            geometries = gpd.read_file(
                archive, engine="pyogrio", layer=layer_name, mask=mask_geometry
            )

        # Clip geometries that are not fully contained in the filter_area to the boundary
        geometries = geometries.clip(filter_area.geometry)

        return geometries

    @classmethod
    def get_all_entries(cls) -> gpd.GeoDataFrame:

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        filtered_geometries = gpd.GeoDataFrame()

        # Iterate over all files in the sources folder
        for file in cls.path.glob("*.gpkg.xz"):

            # Decompress with lzma, then access with geopandas.
            # Output is a GeoDataFrame
            with lzma.open(file, "rb") as archive:
                areas = gpd.read_file(archive)
                filtered_geometries = pd.concat([filtered_geometries, areas])

        # Reset the index to avoid duplicate indices
        filtered_geometries = filtered_geometries.reset_index(drop=True)

        return filtered_geometries


class ResidentialAreas(GeometryHandler):
    """Class for handling data about German residential areas."""

    path = res.files(__package__).joinpath("sources", "residential_areas")


class PopulationGrids(GeometryHandler):
    """Class for handling data about German population grids."""

    path = res.files(__package__).joinpath("sources", "population_grids")


class Pharmacies:

    path = res.files(__package__).joinpath("sources", "pharmacies.gpkg.xz")

    @classmethod
    def get_within_area(cls, filter_area: area.Area) -> gpd.GeoDataFrame:
        """Get all pharmacies within the given bounds."""

        # Check if area is valid
        if not isinstance(filter_area, area.Area):
            raise TypeError("filter_area must be an instance of area.Area")

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        mask = filter_area.geometry

        # Decompress with lzma, then access with geopandas.
        # Output is a GeoDataFrame
        with lzma.open(cls.path, "rb") as archive:
            pharmacies = gpd.read_file(archive, mask=mask)

        pharmacies.rename(columns={"geometry": "location"}, inplace=True)
        pharmacies.set_geometry("location", inplace=True)

        return pharmacies

    @classmethod
    def get_all_pharmacies(cls) -> gpd.GeoDataFrame:

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Decompress with lzma, then access with geopandas.
        # Output is a GeoDataFrame
        with lzma.open(cls.path, "rb") as archive:
            pharmacies = gpd.read_file(archive)

        pharmacies.rename(columns={"geometry": "location"}, inplace=True)
        pharmacies.set_geometry("location", inplace=True)

        return pharmacies


class DistributionCenters:

    path = res.files(__package__).joinpath("sources", "distribution_centers.gpkg.xz")

    @classmethod
    def get_closest_dist_centers(
        cls, area: area.Area, num_centers: int = 3
    ) -> gpd.GeoDataFrame:
        """Get the closest distribution centers within and/or around a given area."""

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Decompress with lzma, then access with geopandas.
        # Output is a GeoDataFrame
        with lzma.open(cls.path, "rb") as archive:
            distribution_centers = gpd.read_file(archive)

        # Convert both geometries to a projected CRS to calculate distances
        area_geometry = area.geometry.to_crs(epsg=25832)
        distribution_centers = distribution_centers.to_crs(epsg=25832)

        area_geometry = area_geometry.geometry[0]  # extract the shapely geometry

        within_area = distribution_centers[distribution_centers.within(area_geometry)]

        # If there are not enough centers within the area, add the closest ones outside the area
        if len(within_area) < num_centers:
            outside_area = distribution_centers[
                ~distribution_centers.within(area_geometry)
            ].copy()

            # Calculate the distance to the area for each center outside the area
            outside_area.loc[:, "distance"] = outside_area.distance(area_geometry)

            closest_outside = outside_area.nsmallest(
                num_centers - len(within_area), "distance"
            )

            closest_outside = closest_outside.drop(columns="distance")

            distribution_centers = pd.concat([within_area, closest_outside])
            distribution_centers.reset_index(drop=True, inplace=True)

        else:
            distribution_centers = within_area

        # Convert the geometries back to a geographic CRS
        distribution_centers = distribution_centers.to_crs(epsg=4326)

        distribution_centers.rename(columns={"geometry": "location"}, inplace=True)
        distribution_centers.set_geometry("location", inplace=True)

        return distribution_centers

    @classmethod
    def get_all_dist_centers(cls) -> gpd.GeoDataFrame:

        # Filter RuntimeWarnings from pyogrio. The GDAL driver for GeoPackage expects a .gpkg filename,
        # but the virtual file it receives from lzma cannot comply with the file standard in this regard.
        warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyogrio")

        # Decompress with lzma, then access with geopandas.
        # Output is a GeoDataFrame
        with lzma.open(cls.path, "rb") as archive:
            distribution_centers = gpd.read_file(archive)

        distribution_centers.rename(columns={"geometry": "location"}, inplace=True)
        distribution_centers.set_geometry("location", inplace=True)

        return distribution_centers


def evaluate_mode_of_transport(distance: int, choices: List[str]) -> str:
    """Return a suitable mode of transportation for a given distance.

    Returns either "auto", "bicycle" or "pedestrian" with probabilities
    based on the given distance.

    Args:
        distance (float): The distance.
        choices (List[str]): The modes of transportation to choose from.

    Returns:
        str: The mode of transportation.
    """

    # Source is a json file with interval breaks and cell values describing
    # usage probabilities for different modes of transportation based on trip length
    path = res.files(__package__).joinpath("sources", "transport_modes.json")

    with open(path, "r") as path:
        json_table = json.load(path)

    index = pd.IntervalIndex.from_breaks(
        json_table["breaks"], closed="left", name="distance"
    )

    mot_table = pd.DataFrame(json_table["data"], index=index)

    # Find the row with the interval that contains the given distance
    row = mot_table.loc[distance]

    # Filter the row to only include the given choices if not all routes could be computed
    row = row[choices]

    # Draw a mode of transportation with the probabilities from the row
    draw = row.sample(1, weights=row.values).index[0]

    return draw

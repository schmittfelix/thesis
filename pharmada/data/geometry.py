"""Module for working with area geometries.

Classes:
    AreaGeometry:   Class for storing and manipulating area geometry.
    
Functions:
    get_area_geometry:      Return the geometry of an area.
    get_precise_geometry:   Return the precise geometry of an area.
    remove_enclosed:        Remove enclosed geometries from a GeoDataFrame.
    remove_oob:             Remove out-of-bounds geometries from a GeoDataFrame.
"""

import pharmada.data.overpass as op
import pharmada.data.regkey as rk
import geopandas as gpd
import importlib.resources as res
import zipfile as zip
import pandas as pd
from shapely.geometry import Polygon


class AreaGeometry:
    """Class for storing and manipulating area geometry.

    Parameters:
        RegKey:     RegKey object for the area.

    Attributes:
        RegKey:             RegKey object for the area.
        osm_id:             The OSM ID of the area.
        geometry:           The general geometry of the area.
        precise_geometry:   The precise geometry of the sub-areas of the total area which are possible customer locations.

    Methods:
        unite_precise_geometry:   Unite all geometries in the precise_geometry GeoDataFrame to a single geometry.
        __str__:                  Return information about the AreaGeometry object.
        __repr__:                 Return all information about the AreaGeometry object.
    """

    __slots__ = ("_RegKey", "_osm_id", "_geometry", "_precise_geometry", "_pop_cells")

    def __init__(self, RegKey: rk.RegKey) -> None:
        """Initialize AreaGeometry object."""

        # check if RegKey is valid
        if not isinstance(RegKey, rk.RegKey):
            raise TypeError("RegKey must be of type RegKey.")

        self._RegKey = RegKey
        self._osm_id = op.regkey_to_osm_id(RegKey)
        self._geometry = _get_area_geometry(RegKey, self.osm_id)
        self._precise_geometry = _get_precise_geometry(self.geometry, self.osm_id)
        self._pop_cells = _get_pop_cells(self.geometry)

    def reset(self) -> None:
        """Reset the geometry GeoDataFrames.

        Parameters:
            None

        Returns:
            None

        Raises:
            None
        """

        self._geometry = _get_area_geometry(self.RegKey, self.osm_id)
        self._precise_geometry = _get_precise_geometry(self.geometry, self.osm_id)

    def united_precise_geometry(self) -> gpd.GeoDataFrame:
        """Unite all geometries in a GeoDataFrame to a single geometry.

        This step is necessary before using the geometry for customer generation.

        Parameters:
            None

        Returns:
            unary_geom (gpd.GeoDataFrame):  A GeoDataFrame containing a single geometry.

        Raises:
            None
        """

        # Unite the geometry to a single polygon
        unary_geom = gpd.GeoDataFrame(
            geometry=[self.precise_geometry.unary_union], crs="EPSG:4326"
        )

        # Add metadata to the GeoDataFrame
        unary_geom["regkey"] = self.regkey
        unary_geom["name"] = self.name
        unary_geom["osm_id"] = self.osm_id

        return unary_geom

    def __str__(self) -> str:
        """Returns information about the AreaGeometry object."""
        return f"AreaGeometry for {self.RegKey}"

    def __repr__(self) -> str:
        """Returns information about the AreaGeometry object."""

        description = f"AreaGeometry for {self.RegKey}.\n"
        geoms_description = f"""Contains the following geometries:\n{self.geometry}\n{self.precise_geometry}"""

        return "".join(description, geoms_description)

    @property
    def RegKey(self) -> rk.RegKey:
        """RegKey object defining the area for AreaGeometry."""
        return self._RegKey

    @RegKey.setter
    def RegKey(self, RegKey: rk.RegKey) -> None:
        """Set RegKey object which defines AreaGeometry."""

        # check if RegKey is valid
        if not isinstance(RegKey, rk.RegKey):
            raise TypeError("RegKey must be of type RegKey.")

        self._RegKey = RegKey

        # update osm_id, geometry, precise_geometry and when RegKey is changed
        self._osm_id = op.regkey_to_osm_id(self.RegKey)
        self._geometry = _get_area_geometry(self.RegKey, self._osm_id)
        self._precise_geometry = _get_precise_geometry(self.geometry, self._osm_id)

    @RegKey.deleter
    def RegKey(self) -> None:
        """Protect RegKey from being deleted and warn user."""
        raise AttributeError(
            "AreaGeometry.RegKey must not be deleted, change it instead."
        )

    @property
    def osm_id(self) -> int:
        """Area OSM relation ID."""
        return self._osm_id

    @osm_id.setter
    def osm_id(self, value) -> None:
        """Protect osm_id from being set and warn user."""
        raise AttributeError(
            f'AreaGeometry.osm_id cannot be changed to "{value}", change RegKey instead.'
        )

    @osm_id.deleter
    def osm_id(self) -> None:
        """Protect osm_id from being deleted and warn user."""
        raise AttributeError(
            "AreaGeometry.osm_id must not be deleted, change RegKey instead."
        )

    @property
    def geometry(self) -> gpd.GeoDataFrame:
        """Area geometry."""
        return self._geometry

    @geometry.setter
    def geometry(self, value) -> None:
        """Protect geometry from being set and warn user."""
        raise AttributeError(
            f'AreaGeometry.geometry cannot be changed to "{value}", change RegKey instead.'
        )

    @geometry.deleter
    def geometry(self) -> None:
        """Protect geometry from being deleted and warn user."""
        raise AttributeError(
            "AreaGeometry.geometry must not be deleted, change RegKey instead."
        )

    @property
    def precise_geometry(self) -> gpd.GeoDataFrame:
        """Precise customer area geometry."""
        return self._precise_geometry

    @precise_geometry.setter
    def precise_geometry(self, value) -> None:
        """Protect precise_geometry from being set and warn user."""
        raise AttributeError(
            f'AreaGeometry.precise_geometry cannot be changed to "{value}", change RegKey instead.'
        )

    @precise_geometry.deleter
    def precise_geometry(self) -> None:
        """Protect precise_geometry from being deleted and warn user."""
        raise AttributeError(
            "AreaGeometry.precise_geometry must not be deleted, change RegKey instead."
        )

    @property
    def pop_cells(self) -> gpd.GeoDataFrame:
        """Area population data with one-ha resolution."""
        return self._pop_cells

    @pop_cells.setter
    def pop_cells(self, value) -> None:
        """Protect pop_cells from being set and warn user."""
        raise AttributeError(
            f'AreaGeometry.pop_cells cannot be changed to "{value}", change RegKey instead.'
        )

    @pop_cells.deleter
    def pop_cells(self) -> None:
        """Protect pop_cells from being deleted and warn user."""
        raise AttributeError(
            "AreaGeometry.pop_cells attribute must not be deleted, change RegKey instead."
        )


def _get_area_geometry(RegKey: rk.RegKey, osm_id: int) -> gpd.GeoDataFrame:
    """Get geometry for given RegKey.

    Parameters:
        RegKey:     RegKey object for the area.
        osm_id:     OSM ID for the area.

    Returns:
        area_geom:  GeoDataFrame containing area geometry.

    Raises:
        None
    """

    geometry = op.get_relation_geometry(osm_id)

    # Convert the geometry to a GeoDataFrame
    area_geom = gpd.GeoDataFrame.from_features(
        geometry, columns=["geometry"], crs="EPSG:4326"
    )

    # Add regional key and name to the GeoDataFrame
    area_geom["regkey"] = RegKey.regkey
    area_geom["name"] = RegKey.name

    """
    # If the area is a multipolygon, convert it to a polygon
    if area_geom.geom_type[0] == "MultiPolygon":
        area_geom = area_geom.explode(index_parts=False)
        area_geom = area_geom.reset_index(drop=True)
    """
    return area_geom


def _get_precise_geometry(boundary: gpd.GeoDataFrame, osm_id: int) -> gpd.GeoDataFrame:
    """Get precise customer areas for given RegKey.

    Parameters:
        boundary:   GeoDataFrame containing the boundary of the area.
        osm_id:     OSM ID for the area.

    Returns:
        area_geom:  GeoDataFrame containing area geometry.

    Raises:
        None
    """

    # Get the raw geometry from the Overpass API
    geometry = op.get_precise_geometry(osm_id)

    # Convert the geometry to a GeoDataFrame
    area_geom = gpd.GeoDataFrame.from_features(geometry, crs="EPSG:4326")

    # Drop unnecessary column 'nodes' if it exists
    if "nodes" in area_geom.columns:
        area_geom.drop(columns=["nodes"], inplace=True)

    # Remove all tags except for name, landuse and amenity
    area_geom["tags"] = area_geom["tags"].apply(
        lambda tags: {
            key: tags[key] for key in ["name", "landuse", "amenity"] if key in tags
        }
    )

    # remove all geometries which are not completely within the area
    area_geom = _remove_oob(boundary, area_geom)

    # Remove all geometries which are enclosed by other geometries
    area_geom = _remove_enclosed(area_geom)

    return area_geom


def _remove_enclosed(area_geom: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Remove enclosed geometries from a GeoDataFrame.

    Parameters:
        area_geom:  GeoDataFrame containing area geometries.

    Returns:
        area_geom:  GeoDataFrame containing area geometries.

    Raises:
        None
    """

    # Create a spatial index of the area geometries
    sindex = area_geom.sindex

    # Create a list of geometries to drop
    to_drop = []
    for row in area_geom.iterrows():
        geom = row[1].geometry
        own_index = row[0]

        # find geometries in the spatial index whose bounding boxes intersect with the current geometry
        possible_matches_index = list(sindex.intersection(geom.bounds))
        # remove the current geometry from the list
        possible_matches_index.remove(own_index)

        # get possible matches and check for intersection
        possible_matches = area_geom.iloc[possible_matches_index]
        precise_matches = possible_matches[possible_matches.intersects(geom)]

        # get contained geometries
        contained_geoms = precise_matches[precise_matches.within(geom)]

        # add indices of contained geometries to list
        to_drop.extend(contained_geoms.index.values)

    # remove duplicates from list
    to_drop = list(set(to_drop))

    # drop contained geometries
    area_geom.drop(to_drop, axis=0, inplace=True)
    area_geom.reset_index(drop=True, inplace=True)

    return area_geom


def _remove_oob(
    boundary: gpd.GeoDataFrame, area_geom: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Remove geometries from area_geom which are not enclosed by a single boundary geometry."""

    to_drop = []

    for geom in area_geom.iterrows():
        if not boundary.geometry.contains(geom[1].geometry)[0]:
            to_drop.append(geom[0])

    area_geom.drop(to_drop, axis=0, inplace=True)
    area_geom.reset_index(drop=True, inplace=True)

    return area_geom


def _get_pop_cells(area_geom: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Get fine-grained population data for a given area.

    Data source: German Zensus 2011, more information: https://www.zensus2022.de/DE/Was-ist-der-Zensus/gitterzellenbasierte_Ergebnisse_Zensus2011.html.
    Since the data consists of 100m x 100m (= 1 hectare) grid cells, we need to find all grid cells within the area of interest.
    This is achieved by filtering the grid cells by the area's bounding box. Subsequently, all grid cells outside of the area's actual geometry are omitted.
    The grid cells are defined by their center point, so all calculations revolve around it ("mp" from German "Mittelpunkt" in data & code).
    EPSG:3035, the format which the data is provided in, is a metric projection, so the coordinates are used as meters instead of degrees.
    """

    # Calculate the center point of the southwest and northeast corner cells
    # defining the area's bounding box.
    area_geom.to_crs(epsg=3035, inplace=True)
    bounds = area_geom.total_bounds

    # Round down to the nearest hectometre and add/subtract 50m to calculate the
    # center point for each of the four corner cells.
    e_sw = int(bounds[0]) // 10**2 * 10**2 + 50
    n_sw = int(bounds[1]) // 10**2 * 10**2 + 50
    e_ne = int(bounds[2]) // 10**2 * 10**2 - 50
    n_ne = int(bounds[3]) // 10**2 * 10**2 - 50

    # Check if a grid cell's center point is within the area bounds
    def in_range(x, y):
        return n_sw <= y <= n_ne and e_sw <= x <= e_ne

    # Load the grid cells and filter them by the area bounds
    path = res.files(__package__).joinpath("files.zip")

    # Read the grid cells from the csv file in the zip archive
    with res.as_file(path) as zipfile:
        with zip.ZipFile(zipfile, mode="r") as archive:
            with archive.open("files/gridcells_data.csv") as csvfile:
                cells = pd.read_csv(
                    csvfile,
                    delimiter=",",
                    header=0,
                    names=["id", "x_mp", "y_mp", "population"],
                    dtype={"id": str, "x_mp": int, "y_mp": int, "population": int},
                    index_col="id",
                )

    # Filter the grid cells by the area bounds
    cells = cells[cells.apply(lambda row: in_range(row["x_mp"], row["y_mp"]), axis=1)]

    # Add cell geometries (100mx100m square around centroid) and convert to a GeoDataFrame
    cells["geometry"] = cells.apply(
        lambda row: Polygon(
            [
                (row["x_mp"] - 50, row["y_mp"] - 50),
                (row["x_mp"] + 50, row["y_mp"] - 50),
                (row["x_mp"] + 50, row["y_mp"] + 50),
                (row["x_mp"] - 50, row["y_mp"] + 50),
            ]
        ),
        axis=1,
    )

    # Convert to a GeoDataFrame and set crs
    cells = gpd.GeoDataFrame(cells, geometry="geometry")
    cells.set_crs(epsg=3035, inplace=True)

    # Drop all grid cells that are outside of the area's geometry
    to_drop = []
    for index, row in cells.iterrows():
        if not area_geom.contains(row.geometry)[0]:
            to_drop.append(index)

    cells.drop(to_drop, inplace=True)
    cells.reset_index(drop=True, inplace=True)

    return cells

"""Module for working with area geometries.

Classes:
    AreaGeometry:   Class for storing and manipulating area geometry.
    
Functions:
    get_area_geometry:      Return the geometry of an area.
    get_precise_geometry:   Return the precise geometry of an area.
    remove_enclosed:        Remove enclosed geometries from a GeoDataFrame.
    remove_oob:             Remove out-of-bounds geometries from a GeoDataFrame.
"""

import pharmada.overpass as op
import pharmada.regkey as rk
import geopandas as gpd

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

    __slots__ = ('_RegKey', '_osm_id', '_geometry', '_precise_geometry')

    def __init__(self, RegKey: rk.RegKey) -> None:
        """Initialize AreaGeometry object."""

        # check if RegKey is valid
        if not isinstance(RegKey, rk.RegKey):
            raise TypeError("RegKey must be of type RegKey.")

        self._RegKey = RegKey
        self._osm_id = op.regkey_to_osm_id(RegKey)
        self._geometry = get_area_geometry(RegKey, self.osm_id)
        self._precise_geometry = get_precise_geometry(self.geometry, self.osm_id)

    def reset(self) -> None:
        """Reset the geometry GeoDataFrames.
        
        Parameters:
            None
            
        Returns:
            None
            
        Raises:
            None
        """

        self._geometry = get_area_geometry(self.RegKey, self.osm_id)
        self._precise_geometry = get_precise_geometry(self.geometry, self.osm_id)

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
        unary_geom = gpd.GeoDataFrame(geometry=[self.precise_geometry.unary_union], crs='EPSG:4326')

        # Add metadata to the GeoDataFrame
        unary_geom['regkey'] = self.regkey
        unary_geom['name'] = self.name
        unary_geom['osm_id'] = self.osm_id

        return unary_geom
                
    def __str__(self) -> str:
        """Returns information about the AreaGeometry object."""
        return f"AreaGeometry for {self.RegKey}"
    
    def __repr__(self) -> str:
        """Returns information about the AreaGeometry object."""
        
        description = f"AreaGeometry for {self.RegKey}.\n"
        geoms_description = f"""Contains the following geometries:\n{self.geometry}\n{self.precise_geometry}"""

        return ''.join(description, geoms_description)

    @property
    def RegKey(self) -> rk.RegKey:
        """Get area RegKey."""
        return self._RegKey
    
    @RegKey.setter
    def RegKey(self, RegKey: rk.RegKey) -> None:
        """Set area RegKey."""

        # check if RegKey is valid
        if not isinstance(RegKey, rk.RegKey):
            raise TypeError("RegKey must be of type RegKey.")
        
        self._RegKey = RegKey

        # update osm_id, geometry and precise_geometry when RegKey is changed
        self._osm_id = op.regkey_to_osm_id(self.RegKey)
        self._geometry = get_area_geometry(self.RegKey, self._osm_id)
        self._precise_geometry = get_precise_geometry(self.geometry, self._osm_id)

    @RegKey.deleter
    def RegKey(self) -> None:
        """Protect RegKey from being deleted and warn user."""
        raise AttributeError("RegKey attribute must not be deleted, change it instead.")

    @property
    def regkey(self) -> str:
        """Get area RegKey."""
        return self._RegKey.regkey
    
    @regkey.setter
    def regkey(self) -> None:
        """Protect regkey from being set and warn user."""
        raise AttributeError("regkey attribute must not be changed, change the RegKey object instead.")
    
    @regkey.deleter
    def regkey(self) -> None:
        """Protect regkey from being deleted and warn user."""
        raise AttributeError("regkey attribute must not be deleted, change the RegKey object instead.")

    @property
    def name(self) -> str:
        """Get area name."""
        return self._RegKey.name
    
    @name.setter
    def name(self) -> None:
        """Protect name from being set and warn user."""
        raise AttributeError("name attribute must not be changed, change the RegKey object instead.")
    
    @name.deleter
    def name(self) -> None:
        """Protect name from being deleted and warn user."""
        raise AttributeError("name attribute must not be deleted, change the RegKey object instead.")
    
    @property
    def osm_id(self) -> int:
        """Get area OSM ID."""
        return self._osm_id
    
    @osm_id.setter
    def osm_id(self) -> None:
        """Protect osm_id from being set and warn user."""
        raise AttributeError("osm_id attribute must not be changed, change the RegKey object instead.")
    
    @osm_id.deleter
    def osm_id(self) -> None:
        """Protect osm_id from being deleted and warn user."""
        raise AttributeError("osm_id attribute must not be deleted, change the RegKey object instead.")

    @property
    def geometry(self) -> gpd.GeoDataFrame:
        """Get area geometry."""
        return self._geometry
    
    @geometry.setter
    def geometry(self) -> None:
        """Protect geometry from being set and warn user."""
        raise AttributeError("geometry attribute must not be changed, change the RegKey object instead.")

    @geometry.deleter
    def geometry(self) -> None:
        """Protect geometry from being deleted and warn user."""
        raise AttributeError("geometry attribute must not be deleted, change the RegKey object instead.")
    
    @property
    def precise_geometry(self) -> gpd.GeoDataFrame:
        """Get precise customer area geometry."""
        return self._precise_geometry
    
    @precise_geometry.setter
    def precise_geometry(self) -> None:
        """Protect precise_geometry from being set and warn user."""
        raise AttributeError("precise_geometry attribute must not be changed, change the RegKey object instead.")
    
    @precise_geometry.deleter
    def precise_geometry(self) -> None:
        """Protect precise_geometry from being deleted and warn user."""
        raise AttributeError("precise_geometry attribute must not be deleted, change the RegKey object instead.")
        
def get_area_geometry(RegKey: rk.RegKey, osm_id: int) -> gpd.GeoDataFrame:
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
    area_geom = gpd.GeoDataFrame.from_features(geometry, columns=['geometry'], crs='EPSG:4326')

    # Add regional key and name to the GeoDataFrame
    area_geom['regkey'] = RegKey.regkey
    area_geom['name'] = RegKey.name

    # If the area is a multipolygon, convert it to a polygon
    if area_geom.geom_type[0] == 'MultiPolygon':
        area_geom = area_geom.explode(index_parts=False)
        area_geom = area_geom.reset_index(drop=True)

    return area_geom

def get_precise_geometry(boundary: gpd.GeoDataFrame, osm_id: int) -> gpd.GeoDataFrame:
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
    area_geom = gpd.GeoDataFrame.from_features(geometry, crs='EPSG:4326')

    # Drop unnecessary column 'nodes' if it exists
    if 'nodes' in area_geom.columns:
        area_geom.drop(columns=['nodes'], inplace=True)

    # Remove all tags except for name, landuse and amenity
    area_geom['tags'] = area_geom['tags'].apply(
        lambda tags: {key: tags[key] for key in ['name', 'landuse', 'amenity'] if key in tags}
        )
    
    # remove all geometries which are not completely within the area
    area_geom = remove_oob(boundary, area_geom)

    # Remove all geometries which are enclosed by other geometries
    area_geom = remove_enclosed(area_geom)

    return area_geom

def remove_enclosed(area_geom: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
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

def remove_oob(boundary: gpd.GeoDataFrame, area_geom: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Remove geometries from area_geom which are not enclosed by a single boundary geometry."""

    to_drop = []

    for geom in area_geom.iterrows():
        if not boundary.geometry.contains(geom[1].geometry)[0]:
            to_drop.append(geom[0])

    area_geom.drop(to_drop, axis=0, inplace=True)
    area_geom.reset_index(drop=True, inplace=True)

    return area_geom


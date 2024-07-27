"""Obtain and present data for the pharmalink VRP model.

Classes:
    Data: Class for data sourcing, storing and presentation for the pharmalink VRP model.
"""

import pharmalink.code.regkey as rk
import pharmalink.code.geometry as geo
import pharmalink.code.pharmacies as ph
import pharmalink.code.customers as cu
import folium as fl
from statistics import mean


class Data:
    """Class for data sourcing, storing and presentation.

    Parameters:
        area:   The area to source data for.

    Attributes:
        RegKey:         RegKey object for the area.
        AreaGeometry:   AreaGeometry object for the area.
        Pharmacies:     PharmaciesInArea object for the area.
        Customers:      Customers object for the area.

    Methods:
        __str__:   Return information about the Data object.
        __repr__:  Return all information about the Data object.
    """

    __slots__ = ["_RegKey", "_AreaGeometry", "_Pharmacies", "_Customers"]

    def __init__(self, area: str) -> None:
        """Initialise the Data class.

        Args:
            area: The area to source data for.
                  Can either be a valid german regional key
                  or a valid county/county-level city name.

        Returns:
            None

        Raises:
            None
        """

        self._RegKey = rk.RegKey(area)
        self._AreaGeometry = geo.AreaGeometry(self.RegKey)
        self._Pharmacies = ph.Pharmacies(self.AreaGeometry)
        self._Customers = cu.Customers(self.AreaGeometry)

    def plot(self) -> fl.Map:
        """Plot the area geometry, pharmacies and customers.

        Args:
            **kwargs: Keyword arguments passed to the plot functions.

        Returns:
            None

        Raises:
            None
        """

        # Setup of the map's bounds
        bounds = self.AreaGeometry.geometry.total_bounds
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

        # Setup marker styles for pharmacies and customers
        pharmacies_marker_args = {
            "radius": 5,
            "color": "red",
            "fill": True,
            "fillOpacity": 1.0,
            "weight": 1,
        }
        customers_marker_args = {
            "radius": 2,
            "color": "green",
            "fill": True,
            "fillOpacity": 1.0,
            "weight": 1,
        }

        style_args = {}

        # Setup of the map's layers
        geometry_args = {
            "data": self.AreaGeometry.geometry,
            "name": "Model boundary",
        }
        precise_geometry_args = {
            "data": self.AreaGeometry.precise_geometry,
            "name": "Customer areas",
            "show": False,
        }
        pharmacies_args = {
            "data": self.Pharmacies.pharmacies,
            "name": "Pharmacies",
            "marker": fl.CircleMarker(**pharmacies_marker_args),
            "show": False,
        }
        customers_args = {
            "data": self.Customers.customers,
            "name": "Customers",
            "marker": fl.CircleMarker(**customers_marker_args),
            "show": False,
        }

        fl.GeoJson(**geometry_args, **style_args).add_to(map)
        fl.GeoJson(**precise_geometry_args, **style_args).add_to(map)
        fl.GeoJson(**pharmacies_args, **style_args).add_to(map)
        fl.GeoJson(**customers_args, **style_args).add_to(map)

        # Add a LayerControl object to the map
        fl.LayerControl().add_to(map)

        # Return the map
        return map

    def __str__(self) -> str:
        """Return information about the Data object."""
        return f"pharmalink data model for {self.RegKey}"

    def __repr__(self) -> str:
        """Return all information about the Data object."""
        data_description = f"pharmalink data model for {self.RegKey}"
        ph_description = f"Pharmacies in area: {len(self.Pharmacies.pharmacies)}"
        cu_description = f"Customers in area:  {len(self.Customers.customers)}"
        return f"{data_description}\n{ph_description}\n{cu_description}"

    @property
    def RegKey(self) -> rk.RegKey:
        """RegKey object defining the area."""
        return self._RegKey

    @RegKey.setter
    def RegKey(self, area: str) -> None:
        """Set RegKey object to define the model area."""

        # check if area is valid
        if not isinstance(area, str):
            raise TypeError("area must be a string.")

        self._RegKey = rk.RegKey(area)
        self._AreaGeometry = geo.AreaGeometry(self.RegKey)
        self._Pharmacies = ph.Pharmacies(self.AreaGeometry)
        self._Customers = cu.Customers(self.AreaGeometry)

    @RegKey.deleter
    def RegKey(self) -> None:
        """Protect RegKey from being deleted and warn user."""
        raise AttributeError("Data.RegKey must not be deleted, change it instead.")

    @property
    def AreaGeometry(self) -> geo.AreaGeometry:
        """AreaGeometry object defining the area."""
        return self._AreaGeometry

    @AreaGeometry.setter
    def AreaGeometry(self, value) -> None:
        """Protect AreaGeometry from being set and warn user."""
        raise AttributeError(
            f'Data.AreaGeometry cannot be changed to "{value}", change RegKey instead.'
        )

    @AreaGeometry.deleter
    def AreaGeometry(self) -> None:
        """Protect AreaGeometry from being deleted and warn user."""
        raise AttributeError(
            "Data.AreaGeometry must not be deleted, change RegKey instead."
        )

    @property
    def Pharmacies(self) -> ph.Pharmacies:
        """Pharmacies within the area."""
        return self._Pharmacies

    @Pharmacies.setter
    def Pharmacies(self, value) -> None:
        """Protect Pharmacies from being set and warn user."""
        raise AttributeError(
            f'Data.Pharmacies cannot be changed to "{value}", change RegKey instead.'
        )

    @Pharmacies.deleter
    def Pharmacies(self) -> None:
        """Protect Pharmacies from being deleted and warn user."""
        raise AttributeError(
            "Data.Pharmacies must not be deleted, change RegKey instead."
        )

    @property
    def Customers(self) -> cu.Customers:
        """Customers within the area."""
        return self._Customers

    @Customers.setter
    def Customers(self, value) -> None:
        """Protect Customers from being set and warn user."""
        raise AttributeError(
            f'Data.Customers cannot be changed to "{value}", change RegKey instead.'
        )

    @Customers.deleter
    def Customers(self) -> None:
        """Protect Customers from being deleted and warn user."""
        raise AttributeError(
            "Data.Customers must not be deleted, change RegKey instead."
        )

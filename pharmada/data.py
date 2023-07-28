"""Obtain and present data for the pharmada VRP model.

This model uses the following submodules:
    - Pharmacies:    Obtain pharmacy data from Google Maps
    - Customers:     Generate randomized but realistic daily customers
    - Overpass:      Interact with the Overpass API for OSM data
    - Gmaps:         Interact with the Google Maps API for Google Maps data
"""

import pharmada.customers as cu
import pharmada.overpass as op
import pharmada.pharmacies as ph
import pharmada.regkey as rk
import geopandas as gpd
"""Module to test the pharmalink package using pytest."""

import pharmalink.code.overpass as overpass
import pharmalink.code.area as area
import pharmalink.code.geometry as geometry
import pharmalink.code.customers as customers
import pharmalink.code.pharmacies as pharmacies
import pharmalink.code.data as data

"""Test the overpass module."""


def test_query_overpass():
    """Test the query_overpass function."""

    # Test a valid query (example is "Kreisfreie Stadt Würzburg")
    query = """
        [out:json];
        (relation(62464);); 
        out geom;
        """
    response = overpass.query_overpass(query)
    assert response["elements"][0]["id"] == 62464

    # Test an invalid query
    query = """
        [out:json];
        out geom;
        """
    response = overpass.query_overpass(query)
    assert response["elements"] == []


def test_regkey_to_osm_id():
    """Test the get_relation_id function."""
    import pharmalink.code.area as area
    import pharmalink.code.overpass as overpass

    # Test a valid regkey
    area = "09663"  # Kreisfreie Stadt Würzburg
    RegKey = area.RegKey(area)

    osm_id = overpass.regkey_to_osm_id(RegKey)
    assert osm_id == 51477

    # Test an invalid regkey
    area = ""
    osm_id = overpass.regkey_to_osm_id(area)
    assert osm_id == None


def test_get_relation_geometry():
    """Test the get_relation_geometry function."""

    # Test a valid regkey
    regkey = "62464"  # Kreisfreie Stadt Würzburg
    relation_geometry = overpass.get_relation_geometry(regkey)
    assert relation_geometry["id"] == "62464"

    # Test an invalid regkey
    regkey = ""
    relation_geometry = overpass.get_relation_geometry(regkey)
    assert type(relation_geometry) == dict


def test_get_precise_geometry():
    """Test the get_precise_geometry function."""

    # Test a valid regkey
    regkey = "62464"  # Kreisfreie Stadt Würzburg
    precise_geometry = overpass.get_precise_geometry(regkey)
    assert type(precise_geometry) == dict

    # Test an invalid regkey
    regkey = ""
    precise_geometry = overpass.get_precise_geometry(regkey)
    assert type(precise_geometry) == dict

"""Module to test the pharmada package using pytest."""

import pharmada.overpass as overpass
import pharmada.regkey as regkey
import pharmada.geometry as geometry
import pharmada.customers as customers
import pharmada.pharmacies as pharmacies
import pharmada.data as data

"""Test the overpass module."""

def test_query_overpass():
    """Test the query_overpass function."""
    
    # Test a valid query
    query = """
        [out:json];
        (relation(51477););
        out geom;
        """
    response = overpass.query_overpass(query)
    assert response['elements'][0]['id'] == 51477
    
    # Test an invalid query
    query = """
        [out:json];
        out geom;
        """
    response = overpass.query_overpass(query)
    assert response['elements'] == []

def test_get_relation_id():
    """Test the get_relation_id function."""
    
    # Test a valid regkey
    regkey = '09663'
    osm_id = overpass.regkey_to_osm_id(regkey)
    assert osm_id == 51477
    
    # Test an invalid regkey
    regkey = ''
    osm_id = overpass.regkey_to_osm_id(regkey)
    assert osm_id == None
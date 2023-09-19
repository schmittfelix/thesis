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
    
    # Test a valid query (example is "Kreisfreie Stadt Würzburg")
    query = """
        [out:json];
        (relation(62464);); 
        out geom;
        """
    response = overpass.query_overpass(query)
    assert response['elements'][0]['id'] == 62464
    
    # Test an invalid query
    query = """
        [out:json];
        out geom;
        """
    response = overpass.query_overpass(query)
    assert response['elements'] == []

def test_regkey_to_osm_id():
    """Test the get_relation_id function."""
    import pharmada.regkey as regkey
    import pharmada.overpass as overpass
    
    # Test a valid regkey
    regkey = '09663' # Kreisfreie Stadt Würzburg
    RegKey = regkey.RegKey(regkey)

    osm_id = overpass.regkey_to_osm_id(RegKey)
    assert osm_id == 51477
    
    # Test an invalid regkey
    regkey = ''
    osm_id = overpass.regkey_to_osm_id(regkey)
    assert osm_id == None

def test_get_relation_geometry():
    """Test the get_relation_geometry function."""
    
    # Test a valid regkey
    regkey = '62464' # Kreisfreie Stadt Würzburg
    relation_geometry = overpass.get_relation_geometry(regkey)
    assert relation_geometry['id'] == '62464'
    
    # Test an invalid regkey
    regkey = ''
    relation_geometry = overpass.get_relation_geometry(regkey)
    assert type(relation_geometry) == dict

def test_get_precise_geometry():
    """Test the get_precise_geometry function."""
    
    # Test a valid regkey
    regkey = '62464' # Kreisfreie Stadt Würzburg
    precise_geometry = overpass.get_precise_geometry(regkey)
    assert type(precise_geometry) == dict
    
    # Test an invalid regkey
    regkey = ''
    precise_geometry = overpass.get_precise_geometry(regkey)
    assert type(precise_geometry) == dict
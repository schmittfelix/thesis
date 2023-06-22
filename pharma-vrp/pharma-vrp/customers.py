"""Generate randomized but realistic customers for the Pharma VRP.

"""
inhabitants = 84,3e6
unit_volume = 852e6
total_cost = 51,21e9


def get_pop_size (area):
    """Get population size for a given area.
    
    This method uses the GENESIS-Online database for population statistics."""

        pop_size_url = "https://www-genesis.destatis.de/genesisWS/rest/2020/data/result?name="

    

import sys
sys.path.append('/Users/felix/Documents/thesis')

from pharmada.overpass import resolve_reg_key


regional_key = '09663'
gmaps_key = 'AIzaSyD1t4K3GksCdP_g3kIu5iG1iPDCtYGzi-E'

name = resolve_reg_key(regional_key)
print(name['name'])
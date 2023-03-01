#%%
import networkx as nx
from matplotlib import pyplot as plt
import osmnx as ox

ox.settings.use_cache=True
# %%
G = ox.graph_from_place(", Würzburg, Unterfranken, Bayern, Deutschland", network_type="all")

G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)
ox.plot_graph(G)



# %%

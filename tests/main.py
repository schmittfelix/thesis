#%%
import networkx as nx
from matplotlib import pyplot as plt
#%%
#first drawing test
G = nx.DiGraph(name="test")

G.add_node(0, name="root")
G.add_node(1, name="middle")
G.add_node(2, name="end")
G.add_edge(0, 1, weight=5)
G.add_edge(1, 2, weight=10)
G.add_edge(2, 0, weight=100)

pos = nx.spring_layout(G)
edge_labels = dict([((n1, n2), f'{G.edges[n1, n2]["weight"]}')
                     for n1, n2 in G.edges])
fig, ax = plt.subplots()
ax.set_title("This is the result of my first test:")
nx.draw_networkx(G, pos)
nx.draw_networkx_edge_labels(
       G, pos, 
       edge_labels=edge_labels
)
plt.box(False)
plt.show()
# %%

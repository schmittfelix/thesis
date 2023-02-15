# Create graph
from networkx import DiGraph

G = DiGraph()

for v in [1, 2, 3, 4, 5]:
       G.add_edge("Source", v, cost=10)
       G.add_edge(v, "Sink", cost=10)
G.add_edge(1, 2, cost=10)
G.add_edge(2, 3, cost=10)
G.add_edge(3, 4, cost=15)
G.add_edge(4, 5, cost=10)

print(len(G))
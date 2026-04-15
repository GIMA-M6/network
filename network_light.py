import osmnx as ox

print("Loading original map...")
G = ox.load_graphml("utrecht_network.graphml")

print("Stripping useless data to save memory...")

# 1. Clean Nodes: Keep ONLY coordinates (x, y)
for node, data in G.nodes(data=True):
    keys_to_remove = [k for k in data.keys() if k not in {'x', 'y'}]
    for k in keys_to_remove:
        del data[k]

# 2. Clean Edges: Keep ONLY the length (for routing) and geometry (for drawing the line)
for u, v, key, data in G.edges(keys=True, data=True):
    keys_to_remove = [k for k in data.keys() if k not in {'length', 'geometry'}]
    for k in keys_to_remove:
        del data[k]

# 3. Save the skinny map
light_path = "utrecht_network_light.graphml"
ox.save_graphml(G, light_path)
print(f"Done! Saved lightweight map as {light_path}")
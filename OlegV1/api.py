from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import osmnx as ox
import networkx as nx
from pathlib import Path # Add this import!

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://utoerist.github.io/"], 
    allow_methods=["https://utoerist.github.io/"],
    allow_headers=["https://utoerist.github.io/"],
)

# 1. Dynamically find the folder where api.py is located
BASE_DIR = Path(__file__).resolve().parent

# 2. Build the exact path to the file
graph_path = BASE_DIR / "utrecht_network.graphml"

# 3. Check if it actually exists before loading to give a better error message
if not graph_path.exists():
    raise FileNotFoundError(f"Cannot find the map file! I looked exactly here: {graph_path}")

print(f"Loading map from: {graph_path}")
G = ox.load_graphml(graph_path)
print("Map loaded!")

@app.get("/get-route")
def calculate_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    # 1. Find the nearest network nodes to the user's clicks
    start_node = ox.nearest_nodes(G, start_lon, start_lat)
    end_node = ox.nearest_nodes(G, end_lon, end_lat)
    
    # 2. Calculate shortest path (Dijkstra)
    try:
        route = nx.shortest_path(G, start_node, end_node, weight='length')
        
        # 3. Convert the list of nodes into actual GPS coordinates
        # (This is simplified; you'll need to extract the geometry of the edges here)
        route_coords = [[G.nodes[n]['y'], G.nodes[n]['x']] for n in route]
        
        return {"status": "success", "route": route_coords}
    except nx.NetworkXNoPath:
        return {"status": "error", "message": "No path found between these points."}
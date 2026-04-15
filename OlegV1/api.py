from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import osmnx as ox
import networkx as nx

app = FastAPI()

# CRITICAL: CORS (Cross-Origin Resource Sharing)
# This allows your GitHub Pages website to talk to this server without getting blocked.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change "*" to your GitHub Pages URL
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the map into memory when the server starts
print("Loading map...")
G = ox.load_graphml("utrecht_network.graphml")
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
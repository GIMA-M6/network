from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import osmnx as ox
import networkx as nx
from pathlib import Path # Add this import!

app = FastAPI()

origins = [
    "https://gima-m6.github.io", # Your live frontend
    "http://localhost:8000",     # For local testing
    "*"                          # Fallback to allow all during development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    
    try:
        # 1. Vind de start en eind nodes
        start_node = ox.nearest_nodes(G, start_lon, start_lat)
        end_node = ox.nearest_nodes(G, end_lon, end_lat)
        
        # 2. Bereken de kortste route (dit is een lijst van Node ID's)
        route_nodes = nx.shortest_path(G, start_node, end_node, weight='length')
        
        # 3. NIEUW: Verzamel de exacte vorm (geometry) van de wegen
        route_coords = []
        
        for i in range(len(route_nodes) - 1):
            u = route_nodes[i]
            v = route_nodes[i+1]
            
            # Haal de data van de straat op tussen node U en V
            # (OSMnx netwerken zijn MultiDiGraphs, dus we pakken de eerste verbinding [0])
            edge_data = G.get_edge_data(u, v)[0]
            
            # Check of deze straat een fysieke bocht/vorm heeft ingeladen
            if 'geometry' in edge_data:
                # Haal alle micro-coördinaten van de bocht uit elkaar
                xs, ys = edge_data['geometry'].xy
                for x, y in zip(xs, ys):
                    route_coords.append([y, x]) # Let op: Leaflet wil Lat(y), Lon(x)
            else:
                # Als het een perfect rechte weg is, heeft hij geen geometry.
                # Dan pakken we gewoon het startpunt.
                route_coords.append([G.nodes[u]['y'], G.nodes[u]['x']])
                
        # Vergeet niet het allereerste eindpunt van de hele route toe te voegen
        last_node = route_nodes[-1]
        route_coords.append([G.nodes[last_node]['y'], G.nodes[last_node]['x']])

        # 4. Stuur de gedetailleerde lijst terug naar je website
        return {"status": "success", "route": route_coords}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

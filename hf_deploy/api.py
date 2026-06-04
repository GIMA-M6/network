from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import osmnx as ox
import networkx as nx
from pathlib import Path

app = FastAPI()

origins = [
    "https://gima-m6.github.io",
    "http://localhost:8000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# GRAPH LOADING
# ---------------------------------------------------------------------------

SCENIC_GRAPH_PATH = BASE_DIR / "utrecht_network_scenic.graphml"
PLAIN_GRAPH_PATH  = BASE_DIR / "utrecht_network.graphml"

if SCENIC_GRAPH_PATH.exists():
    print(f"Loading scenic graph from: {SCENIC_GRAPH_PATH}")
    G = ox.load_graphml(SCENIC_GRAPH_PATH)
    HAS_SCENIC = True
    print("Scenic graph loaded!")
elif PLAIN_GRAPH_PATH.exists():
    print(f"Scenic graph not found — falling back to plain graph: {PLAIN_GRAPH_PATH}")
    G = ox.load_graphml(PLAIN_GRAPH_PATH)
    HAS_SCENIC = False
    print("Plain graph loaded.")
else:
    raise FileNotFoundError(
        f"No graph file found. Expected one of:\n"
        f"  {SCENIC_GRAPH_PATH}\n"
        f"  {PLAIN_GRAPH_PATH}"
    )


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _extract_route_coords(G: nx.MultiDiGraph, route_nodes: list) -> list[list[float]]:
    """
    Walk a list of node IDs and extract the full polyline geometry,
    ensuring the geometry flows in the correct direction of travel.
    """
    coords = []
    
    for i in range(len(route_nodes) - 1):
        u = route_nodes[i]
        v = route_nodes[i + 1]
        
        edges = G.get_edge_data(u, v)
        edge_data = min(edges.values(), key=lambda x: x.get('length', float('inf')))

        if "geometry" in edge_data:
            geom_coords = list(edge_data["geometry"].coords)
            
            u_x, u_y = G.nodes[u]["x"], G.nodes[u]["y"]
            start_x, start_y = geom_coords[0]
            
            if abs(start_x - u_x) > 1e-5 or abs(start_y - u_y) > 1e-5:
                geom_coords.reverse() # Draai de straat om!
            
            for x, y in geom_coords[:-1]:
                coords.append([y, x])  # Leaflet wants [lat, lon]
        else:
            coords.append([G.nodes[u]["y"], G.nodes[u]["x"]])

    last_node = route_nodes[-1]
    coords.append([G.nodes[last_node]["y"], G.nodes[last_node]["x"]])
    
    return coords


def _route_stats(G: nx.MultiDiGraph, route_nodes: list) -> dict:
    """Compute total distance and weighted mean scenic score for a route."""
    total_length = 0.0
    scenic_scores = []
    edge_lengths = []

    for i in range(len(route_nodes) - 1):
        u = route_nodes[i]
        v = route_nodes[i + 1]
        
        edges = G.get_edge_data(u, v)
        edge_data = min(edges.values(), key=lambda x: x.get('length', float('inf')))
        
        length = edge_data.get("length", 0.0)
        total_length += length
        edge_lengths.append(length)
        
        if "scenic_score" in edge_data:
            scenic_scores.append(float(edge_data["scenic_score"]))
        else:
            scenic_scores.append(0.0)

    # Weighted mean: weight each score by the edge's distance proportion
    mean_scenic_score = None
    if scenic_scores and total_length > 0:
        weighted_score = sum(s * l for s, l in zip(scenic_scores, edge_lengths)) / total_length
        mean_scenic_score = round(weighted_score, 3)

    return {
        "distance_m": round(total_length),
        "mean_scenic_score": mean_scenic_score,
    }

# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/get-route")
def get_shortest_route(
    start_lat: float, start_lon: float,
    end_lat: float,   end_lon: float,
):
    """Classic shortest-path route (unchanged behaviour)."""
    try:
        start_node = ox.nearest_nodes(G, start_lon, start_lat)
        end_node   = ox.nearest_nodes(G, end_lon,   end_lat)
        route      = nx.shortest_path(G, start_node, end_node, weight="length")
        coords     = _extract_route_coords(G, route)
        stats      = _route_stats(G, route)

        return {"status": "success", "route": coords, **stats}

    except nx.NetworkXNoPath:
        return {"status": "error", "message": "No path found between these points."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/get-scenic-route")
def get_scenic_route(
    start_lat: float, start_lon: float,
    end_lat: float,   end_lon: float,
    alpha: float = Query(default=0.5, ge=0.0, le=1.0,
                         description="0 = shortest path, 1 = most scenic"),
):
    if not HAS_SCENIC:
        return {
            "status": "error",
            "message": "Scenic graph not available."
        }

    try:
        start_node = ox.nearest_nodes(G, start_lon, start_lat)
        end_node   = ox.nearest_nodes(G, end_lon,   end_lat)

        def dynamic_scenic_cost(u, v, edge_data):
            length = float(edge_data.get("length", 1.0))
            raw_score = float(edge_data.get("scenic_score", 0.0))
            
            if alpha == 0:
                return length
            
            # Smooth blending formula: creates a gradient of routes from shortest to most scenic
            # cost = length / (1 - alpha + alpha * scenic_score)
            # 
            # alpha = 0.0  → cost = length                     (shortest path, ignores scenery)
            # alpha = 0.5  → cost = length / (0.5 + 0.5*score) (balanced)
            # alpha = 1.0  → cost = length / score             (pure scenic, avoids non-scenic edges)
            cost = length / (1.0 - alpha + alpha * raw_score)
            return cost

        route  = nx.shortest_path(G, start_node, end_node, weight=dynamic_scenic_cost)
        
        coords = _extract_route_coords(G, route)
        stats  = _route_stats(G, route)

        return {
            "status": "success",
            "route":  coords,
            "alpha":  alpha,
            **stats,
        }

    except nx.NetworkXNoPath:
        return {"status": "error", "message": "No path found between these points."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/health")
def health():
    return {
        "status":      "ok",
        "scenic_graph": HAS_SCENIC,
        "nodes":        G.number_of_nodes(),
        "edges":        G.number_of_edges(),
    }

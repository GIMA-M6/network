"""
scenic_graph.py — Enrich a Utrecht street network graph with scenic weights.

Pipeline:
    1. Load the GraphML network (osmnx MultiDiGraph)
    2. Load all scenic GeoDataFrames via the existing data loader
    3. For every edge, compute a distance-decay scenic score from nearby features
    4. Attach two new edge attributes:
         - scenic_score   : float [0, 1]  (higher = more scenic)
         - scenic_cost    : float         (routing cost, length-adjusted)
    5. Save the enriched graph back to GraphML

Routing cost formula:
    scenic_cost = length * (1 / (alpha * scenic_score + (1 - alpha)))

    alpha = 0.0  →  pure shortest path (scenic ignored)
    alpha = 1.0  →  pure scenic routing (distance barely matters)
    alpha = 0.5  →  balanced (recommended default)

Usage:
    python scenic_graph.py --input utrecht_network.graphml \
                           --output utrecht_network_scenic.graphml \
                           --alpha 0.5
"""

import argparse
import math
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
from shapely.geometry import LineString

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Metric CRS for accurate distance calculations (RD New — perfect for Netherlands)
METRIC_CRS = "EPSG:28992"

# Default alpha: balance between scenic quality and shortest distance
DEFAULT_ALPHA = 0.5

# Per-layer search radius (meters).
# Reflects realistic street-level visibility in Utrecht's urban environment.
LAYER_SEARCH_RADIUS: dict[str, float] = {
    # Large landmarks
    "atlas_kastelen":               100.0,
    "atlas_rijksmonumenten":        100.0,
    "atlas_molens":                 100.0,
    "atlas_groene_rijksmonumenten": 100.0,
    "atlas_stadsgezichten":         100.0,
    "atlas_grafheuvels":             75.0,
    # Heritage buildings — block-level visibility
    "utrecht_beeldbepalend_1":       50.0,
    "utrecht_beeldbepalend_2":       50.0,
    "bag_oude_gebouwen":             50.0,
    "erfgoed_gemeentelijk":          50.0,
    "osm_ruins":                     50.0,
    "osm_museum":                    50.0,
    "osm_theatre":                   50.0,
    "osm_viewpoint":                 75.0,
    # Water & green
    "bgt_water":                     50.0,
    "bgt_green":                     50.0,
    "osm_leisure":                   50.0,
    "osm_fountain":                  25.0,
    # Street furniture
    "osm_artwork":                   30.0,
    "osm_memorial":                  30.0,
    "osm_benches":                   20.0,
    "bgt_benches":                   20.0,
    "osm_boulevard":                 20.0,
}

# Fallback radius for any layer not listed above
DEFAULT_SEARCH_RADIUS = 50.0

# Decay steepness: score = exp(-k * distance / radius)
# k=2 means a feature at the edge of its radius contributes ~e^-2 ≈ 0.13× its weight
DECAY_K = 2.5


# ---------------------------------------------------------------------------
# STEP 1 — LOAD GRAPH
# ---------------------------------------------------------------------------

def load_graph(path: str) -> nx.MultiDiGraph:
    print(f"Loading graph from {path} …")
    G = ox.load_graphml(path)
    print(f"  Nodes: {G.number_of_nodes():,}   Edges: {G.number_of_edges():,}")
    return G


# ---------------------------------------------------------------------------
# STEP 2 — LOAD SCENIC DATA
# ---------------------------------------------------------------------------

def load_scenic_data() -> dict[str, gpd.GeoDataFrame]:
    """
    Load scenic GeoDataFrames via the project's data_loader module.
    Falls back gracefully if the module isn't importable (e.g. running standalone).
    """
    try:
        from data_loader import load_all_scenic_data
        from scenic_weights import assign_weights

        print("Loading scenic datasets via data_loader …")
        raw = load_all_scenic_data()
        datasets, _ = assign_weights(raw)
        print(f"  Loaded {len(datasets)} layers")
        return datasets

    except ImportError:
        print(
            "[WARN] data_loader / scenic_weights not found on sys.path.\n"
            "       Place this script in the same folder as data_loader.py, or\n"
            "       pass pre-loaded datasets via enrich_graph() directly."
        )
        return {}


# ---------------------------------------------------------------------------
# STEP 3 — REPROJECT HELPERS
# ---------------------------------------------------------------------------

def _reproject_datasets(
    datasets: dict[str, gpd.GeoDataFrame],
    target_crs: str,
) -> dict[str, gpd.GeoDataFrame]:
    """Reproject all non-empty GeoDataFrames to target_crs."""
    reprojected = {}
    for name, gdf in datasets.items():
        if not isinstance(gdf, gpd.GeoDataFrame) or len(gdf) == 0:
            continue
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        reprojected[name] = gdf.to_crs(target_crs)
    return reprojected


def _graph_edges_as_gdf(G: nx.MultiDiGraph, target_crs: str) -> gpd.GeoDataFrame:
    """
    Convert graph edges to a GeoDataFrame in target_crs.
    Uses stored geometry if available, otherwise builds a straight line.
    """
    records = []
    for u, v, key, data in G.edges(keys=True, data=True):
        if "geometry" in data:
            geom = data["geometry"]
        else:
            # Straight line fallback
            x_u, y_u = G.nodes[u]["x"], G.nodes[u]["y"]
            x_v, y_v = G.nodes[v]["x"], G.nodes[v]["y"]
            geom = LineString([(x_u, y_u), (x_v, y_v)])
        records.append({"u": u, "v": v, "key": key, "geometry": geom})

    edges_gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
    return edges_gdf.to_crs(target_crs)


# ---------------------------------------------------------------------------
# STEP 4 — DISTANCE-DECAY SCORING
# ---------------------------------------------------------------------------

def _decay_weight(distance_m: float, radius_m: float) -> float:
    """
    Exponential distance-decay weight.
    Returns 1.0 at distance=0, ~0.13 at distance=radius, 0 beyond radius.
    """
    if distance_m >= radius_m:
        return 0.0
    return math.exp(-DECAY_K * distance_m / radius_m)


def compute_edge_scenic_scores(
    edges_gdf: gpd.GeoDataFrame,
    datasets: dict[str, gpd.GeoDataFrame],
    scenic_weight_lookup: dict[str, float],
) -> np.ndarray:
    """
    For each edge, compute a cumulative distance-decay scenic score.

    Score = sum over all nearby features of:
        layer_scenic_weight * decay(distance_to_feature, layer_radius)

    The raw cumulative score is then normalised to [0, 1] across all edges.

    Returns an array of normalised scenic scores, same order as edges_gdf.
    """
    n_edges = len(edges_gdf)
    raw_scores = np.zeros(n_edges, dtype=np.float64)

    # Represent each edge as its centroid for distance queries.
    # For short urban edges this is accurate enough; avoids expensive
    # polygon–line distance ops on tens of thousands of edges.
    edge_centroids = edges_gdf.geometry.centroid

    total_layers = len(datasets)
    for layer_idx, (layer_name, gdf) in enumerate(datasets.items()):
        if not isinstance(gdf, gpd.GeoDataFrame) or len(gdf) == 0:
            continue

        layer_weight = scenic_weight_lookup.get(layer_name)
        if layer_weight is None:
            continue

        radius = LAYER_SEARCH_RADIUS.get(layer_name, DEFAULT_SEARCH_RADIUS)

        # Dissolve multi-part geometries to points / centroids for speed
        feature_centroids = gdf.geometry.centroid

        print(
            f"  [{layer_idx+1}/{total_layers}] {layer_name}: "
            f"{len(gdf)} features, radius={radius}m, weight={layer_weight:.3f}"
        )

        # Spatial index on features for fast radius queries
        feature_sindex = feature_centroids.sindex

        for edge_idx, edge_centroid in enumerate(edge_centroids):
            # Candidate features within bounding-box radius
            candidates_idx = list(
                feature_sindex.query(edge_centroid.buffer(radius))
            )
            if not candidates_idx:
                continue

            for feat_idx in candidates_idx:
                feat_geom = feature_centroids.iloc[feat_idx]
                dist = edge_centroid.distance(feat_geom)
                decay = _decay_weight(dist, radius)
                if decay > 0:
                    raw_scores[edge_idx] += layer_weight * decay

    # Normalise to [0, 1]
    max_score = raw_scores.max()
    if max_score > 0:
        normalised = raw_scores / max_score
    else:
        normalised = raw_scores

    print(
        f"\nScenic score stats — "
        f"min: {normalised.min():.4f}, "
        f"mean: {normalised.mean():.4f}, "
        f"max: {normalised.max():.4f}"
    )
    return normalised


# ---------------------------------------------------------------------------
# STEP 5 — ATTACH SCORES TO GRAPH
# ---------------------------------------------------------------------------

def attach_scores_to_graph(
    G: nx.MultiDiGraph,
    edges_gdf: gpd.GeoDataFrame,
    scenic_scores: np.ndarray,
    alpha: float,
) -> nx.MultiDiGraph:
    """
    Write scenic_score and scenic_cost back onto every edge in G.

    scenic_cost = length * (1 / (alpha * scenic_score + (1 - alpha)))

    When scenic_score = 0: scenic_cost = length          (same as shortest path)
    When scenic_score = 1: scenic_cost = length / 1.0    (alpha=0.5 → length * 0.667)
    """
    for i, (_, row) in enumerate(edges_gdf.iterrows()):
        u, v, key = row["u"], row["v"], row["key"]
        score = float(scenic_scores[i])

        length = G[u][v][key].get("length", 1.0)
        cost = length * (1.0 / (alpha * score + (1.0 - alpha)))

        G[u][v][key]["scenic_score"] = round(score, 6)
        G[u][v][key]["scenic_cost"] = round(cost, 4)

    return G


# ---------------------------------------------------------------------------
# STEP 6 — SAVE
# ---------------------------------------------------------------------------

def save_graph(G: nx.MultiDiGraph, path: str) -> None:
    print(f"\nSaving enriched graph to {path} …")
    ox.save_graphml(G, path)
    size_mb = Path(path).stat().st_size / 1_048_576
    print(f"  Saved ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------

def enrich_graph(
    input_path: str,
    output_path: str,
    datasets: dict[str, gpd.GeoDataFrame] | None = None,
    alpha: float = DEFAULT_ALPHA,
) -> nx.MultiDiGraph:
    """
    Full pipeline: load → score → attach → save.

    Parameters
    ----------
    input_path  : path to the source GraphML file
    output_path : path for the enriched GraphML output
    datasets    : pre-loaded dict from load_all_scenic_data() + assign_weights().
                  If None, the function will call load_scenic_data() itself.
    alpha       : scenic/distance trade-off (0 = shortest path, 1 = most scenic)

    Returns
    -------
    Enriched MultiDiGraph (also saved to output_path)
    """
    from scenic_weights import SCENIC_WEIGHT_LOOKUP

    # 1. Load graph
    G = load_graph(r"C:\GIMA\Module 6\Code\network\hf_deploy\utrecht_network.graphml")

    # 2. Load scenic data if not provided
    if datasets is None:
        datasets = load_scenic_data()
        if not datasets:
            print("[ERROR] No scenic datasets loaded — aborting.")
            sys.exit(1)

    # 3. Reproject everything to metric CRS
    print(f"\nReprojecting to {METRIC_CRS} …")
    metric_datasets = _reproject_datasets(datasets, METRIC_CRS)
    edges_gdf = _graph_edges_as_gdf(G, METRIC_CRS)
    print(f"  {len(edges_gdf):,} edges to score")

    # 4. Compute scenic scores
    print("\nComputing distance-decay scenic scores …")
    scenic_scores = compute_edge_scenic_scores(
        edges_gdf, metric_datasets, SCENIC_WEIGHT_LOOKUP
    )

    # 5. Attach to graph
    print(f"\nAttaching scores (alpha={alpha}) …")
    G = attach_scores_to_graph(G, edges_gdf, scenic_scores, alpha)

    # 6. Save
    save_graph(G, r"C:\GIMA\Module 6\Code\network\hf_deploy\utrecht_network_scenic.graphml")

    return G


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich a Utrecht road graph with scenic weights.")
    parser.add_argument("--input",  default="utrecht_network.graphml",        help="Input GraphML path")
    parser.add_argument("--output", default="utrecht_network_scenic.graphml", help="Output GraphML path")
    parser.add_argument("--alpha",  type=float, default=DEFAULT_ALPHA,        help="Scenic/distance balance (0–1)")
    args = parser.parse_args()

    enrich_graph(args.input, args.output, alpha=args.alpha)

    # ===========================================================================
    # GEOPACKAGE EXPORT
    # ===========================================================================
    try:
        print("\nNetwerk exporteren naar GeoPackage...")
        
        G_saved = ox.load_graphml(args.output)
        
        gdf_nodes, gdf_edges = ox.graph_to_gdfs(G_saved, nodes=True, edges=True)

        for col in gdf_nodes.columns:
            if gdf_nodes[col].apply(lambda x: isinstance(x, list)).any():
                gdf_nodes[col] = gdf_nodes[col].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x)

        for col in gdf_edges.columns:
            if gdf_edges[col].apply(lambda x: isinstance(x, list)).any():
                gdf_edges[col] = gdf_edges[col].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x)

        gdf_edges = gdf_edges.reset_index()

        output_gpkg_path = args.output.replace(".graphml", ".gpkg")
        
        gdf_nodes.to_file(output_gpkg_path, layer="network_nodes", driver="GPKG")
        gdf_edges.to_file(output_gpkg_path, layer="network_edges", driver="GPKG")

        print(f"Succesvol opgeslagen! Nodes en Edges staan in: {output_gpkg_path}\n")

    except Exception as e:
        print(f"\n[WARN] GeoPackage-export mislukt, maar GraphML is veilig opgeslagen: {e}\n")

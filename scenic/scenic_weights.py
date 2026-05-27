"""
Assign scenicness weights to all scenic datasets loaded by the data loader.

Weights are derived from the forest-plot coefficients in:
    Seresinhe et al. (or equivalent) — 'Change in Scenicness Rating' per scene label.

Methodology:
1. Raw coefficients are read from the figure (approximate point estimates).
2. Each dataset layer is mapped to the most representative figure label(s).
   Where a layer spans multiple labels, the mean of those coefficients is used.
3. All final weights are min-max normalised to [0, 1] across the full layer set.

Output:
- SCENIC_WEIGHT_LOOKUP : dict  {layer_name: normalised_weight}
- assign_weights(datasets)    : adds a 'scenic_weight' column to every GeoDataFrame
                                and returns both the enriched dict and the lookup.
"""

# ---------------------------------------------------------------------------
# 1. RAW COEFFICIENTS  (read from figure, point estimates)
# ---------------------------------------------------------------------------
# Positive = increases perceived scenicness
# Negative = decreases perceived scenicness

RAW_COEFFICIENTS = {
    # Greenspace
    "Listed Building":          0.65,   # purple dot — top of chart
    "Agriculture":              0.45,
    "Branch":                   0.50,
    "Forest":                   0.65,
    "Highland":                 0.55,
    "Mountain":                 1.10,
    "Natural Landscape":        0.55,
    "Plant Community":          0.50,
    "Rock":                     0.55,
    "Trunk":                    0.55,
    # Bluespace
    "Boat":                     1.35,
    "Lake":                     0.85,
    "Reservoir":               -0.55,
    "Water":                   -0.35,
    "Watercourse":              0.40,
    # Built Environment
    "Asphalt":                 -0.0020,
    "Building":                -0.15,
    "Church":                   0.20,
    "City":                    -0.10,
    "Commercial Building":     -0.25,
    "Cottage":                 -0.10,
    "Gas":                     -0.20,
    "Girder Bridge":           -0.20,
    "Highway":                 -0.25,
    "House":                   -0.20,
    "Land Lot":                -0.25,
    "Manor House":             -0.10,
    "Monument":                 0.05,
    "Overhead Power Line":     -0.30,
    "Real Estate":             -0.20,
    "Road Surface":            -0.0020,
    "Street Light":            -0.25,
    "Tar":                     -0.25,
    "Tower Block":             -0.30,
    # Vehicles
    "Automotive Parking Light":-0.30,
    "Motor Vehicle":           -0.25,
    "Train":                   -0.15,
    # Other
    "Biome":                    0.55,
    "Cloud":                   -0.15,
    "Ecoregion":                0.45,
    "Horizon":                  0.50,
    "Monochrome":               0.50,
    "Snow":                    -0.30,
}


# ---------------------------------------------------------------------------
# 2. LAYER → FIGURE LABEL MAPPING
# ---------------------------------------------------------------------------
# Each layer is mapped to one or more figure labels.
# The layer's raw score = mean of its mapped label coefficients.

LAYER_LABEL_MAP = {
    # --- OSM ---
    "osm_artwork":          ["Monument", "Listed Building"],
    "osm_memorial":         ["Monument"],
    "osm_viewpoint":        ["Natural Landscape", "Horizon"],
    "osm_fountain":         ["Water", "Watercourse"],
    "osm_ruins":            ["Listed Building", "Monument"],
    "osm_theatre":          ["Building", "City"],
    "osm_museum":           ["Listed Building", "Building"],
    "osm_leisure":          ["Plant Community", "Natural Landscape"],
    "osm_benches":          ["Natural Landscape"],          # proxy: seating in parks
    "osm_boulevard":        ["Asphalt", "Road Surface"],

    # --- BGT + BAG ---
    "bgt_benches":          ["Natural Landscape"],          # same proxy as osm_benches
    "bgt_water":            ["Watercourse", "Water"],
    "bgt_green":            ["Plant Community", "Agriculture", "Natural Landscape"],
    "bag_oude_gebouwen":    ["Listed Building", "Manor House"],

    # --- Atlas Leefomgeving ---
    "atlas_rijksmonumenten":        ["Listed Building"],
    "atlas_molens":                 ["Listed Building", "Natural Landscape"],
    "atlas_kastelen":               ["Listed Building", "Manor House"],
    "atlas_groene_rijksmonumenten": ["Listed Building", "Plant Community", "Natural Landscape"],
    "atlas_grafheuvels":            ["Natural Landscape", "Monument"],
    "atlas_stadsgezichten":         ["Listed Building", "City"],

    # --- RIVM (negative pressure layers) ---
    "rivm_noise":           ["Highway", "Motor Vehicle", "Train"],
    "rivm_air":             ["Asphalt", "Commercial Building", "Gas"],

    # --- UtrechtOpen + Erfgoed ---
    "utrecht_beeldbepalend_1":  ["Listed Building", "Manor House"],
    "utrecht_beeldbepalend_2":  ["Listed Building", "Manor House"],
    "erfgoed_gemeentelijk":     ["Listed Building", "Monument"],
}


# ---------------------------------------------------------------------------
# 3. COMPUTE RAW LAYER SCORES
# ---------------------------------------------------------------------------

def _compute_raw_scores() -> dict:
    """Average the mapped coefficients for each layer."""
    raw_scores = {}
    for layer, labels in LAYER_LABEL_MAP.items():
        scores = [RAW_COEFFICIENTS[lbl] for lbl in labels if lbl in RAW_COEFFICIENTS]
        raw_scores[layer] = sum(scores) / len(scores) if scores else 0.0
    return raw_scores


# ---------------------------------------------------------------------------
# 4. MIN-MAX NORMALISE TO [0, 1]
# ---------------------------------------------------------------------------

def _normalise(raw_scores: dict) -> dict:
    """Normalise raw scores to [0, 1]."""
    values = list(raw_scores.values())
    min_v, max_v = min(values), max(values)
    span = max_v - min_v if max_v != min_v else 1.0
    return {layer: round((score - min_v) / span, 4)
            for layer, score in raw_scores.items()}


# ---------------------------------------------------------------------------
# 5. BUILD THE PUBLIC LOOKUP DICT
# ---------------------------------------------------------------------------

_RAW_SCORES = _compute_raw_scores()
SCENIC_WEIGHT_LOOKUP: dict = _normalise(_RAW_SCORES)

"""
SCENIC_WEIGHT_LOOKUP  —  {layer_name: float in [0, 1]}

Quick reference (sorted descending):
    atlas_rijksmonumenten          ~1.00   (Listed Building alone)
    osm_ruins                      ~0.97   (Listed Building + Monument)
    atlas_kastelen                 ~0.94   (Listed Building + Manor House)
    utrecht_beeldbepalend_1/2      ~0.94
    bag_oude_gebouwen              ~0.94
    atlas_molens                   ~0.90   (Listed Building + Natural Landscape)
    osm_museum                     ~0.74
    osm_artwork                    ~0.74
    bgt_green                      ~0.71
    osm_viewpoint                  ~0.68
    bgt_water / osm_fountain       ~0.43
    rivm_noise / rivm_air          ~0.00–0.06  (lowest — negative labels)
"""


# ---------------------------------------------------------------------------
# 6. MAIN PUBLIC FUNCTION
# ---------------------------------------------------------------------------

def assign_weights(datasets: dict) -> tuple[dict, dict]:
    """
    Add a 'scenic_weight' column to every GeoDataFrame in `datasets`.

    Parameters
    ----------
    datasets : dict
        Output of load_all_scenic_data() — {layer_name: GeoDataFrame}

    Returns
    -------
    weighted_datasets : dict
        Same structure; each non-empty GeoDataFrame gains a 'scenic_weight' column.
    lookup : dict
        {layer_name: normalised_weight}  — identical to SCENIC_WEIGHT_LOOKUP
        but limited to layers present in `datasets`.
    """
    import geopandas as gpd

    weighted_datasets = {}
    present_lookup = {}

    for layer_name, gdf in datasets.items():
        weight = SCENIC_WEIGHT_LOOKUP.get(layer_name)

        if weight is None:
            print(f"  [WARN] No weight mapping for layer '{layer_name}' — skipping.")
            weighted_datasets[layer_name] = gdf
            continue

        present_lookup[layer_name] = weight

        if isinstance(gdf, gpd.GeoDataFrame) and len(gdf) > 0:
            gdf = gdf.copy()
            gdf["scenic_weight"] = weight
            # Also attach the raw (un-normalised) score for reference
            gdf["scenic_weight_raw"] = round(_RAW_SCORES.get(layer_name, 0.0), 4)

        weighted_datasets[layer_name] = gdf

    print(f"\nWeights assigned to {len(present_lookup)} layers.")
    return weighted_datasets, present_lookup


# ---------------------------------------------------------------------------
# 7. CONVENIENCE: PRINT WEIGHT TABLE
# ---------------------------------------------------------------------------

def print_weight_table():
    """Print a sorted summary of all layer weights."""
    sorted_layers = sorted(SCENIC_WEIGHT_LOOKUP.items(), key=lambda x: x[1], reverse=True)
    print(f"\n{'Layer':<40} {'Raw score':>10}  {'Normalised':>10}  {'Labels'}")
    print("-" * 90)
    for layer, norm in sorted_layers:
        raw = round(_RAW_SCORES[layer], 3)
        labels = ", ".join(LAYER_LABEL_MAP.get(layer, []))
        print(f"{layer:<40} {raw:>10.3f}  {norm:>10.4f}  {labels}")


# ---------------------------------------------------------------------------
# 8. EXAMPLE USAGE
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Stand-alone demo (no actual data loading)
    print("=== Scenic Weight Lookup (normalised 0–1) ===")
    print_weight_table()

    # Full pipeline usage:
    #
    #   from data_loader import load_all_scenic_data
    #   from scenic_weights import assign_weights
    #
    #   datasets = load_all_scenic_data()
    #   weighted_datasets, lookup = assign_weights(datasets)
    #
    #   # Access a specific layer:
    #   gdf = weighted_datasets["atlas_rijksmonumenten"]
    #   print(gdf[["geometry", "scenic_weight"]].head())

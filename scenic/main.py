"""
main.py — Entry point for the Utrecht Scenic Routing project.

Runs the full pipeline:
    1. Load all scenic datasets for Utrecht (OSM, BGT, BAG, Atlas, RIVM, UtrechtOpen)
    2. Assign normalised scenicness weights to every layer
    3. Save results to a GeoPackage + a CSV weight lookup table

Usage:
    python main.py

Outputs (written to the folder defined in config.OUTPUT_DIR):
    utrecht_scenic_weighted.gpkg   — all weighted layers as GeoPackage
    scenic_weight_lookup.csv       — layer → weight mapping table
"""

import os
import sys
import pandas as pd
import geopandas as gpd

from data_loader import load_all_scenic_data
from scenic_weights import assign_weights, print_weight_table
import scenic.config as config


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def save_outputs(weighted_datasets: dict, lookup: dict) -> None:
    """
    Persist results to disk:
      - Each non-empty GeoDataFrame → a layer in a GeoPackage.
      - The weight lookup dict      → a CSV table.
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    gpkg_path = os.path.join(config.OUTPUT_DIR, config.OUTPUT_GPKG)
    csv_path  = os.path.join(config.OUTPUT_DIR, config.OUTPUT_WEIGHT_CSV)

    saved_layers = 0
    for layer_name, gdf in weighted_datasets.items():
        if not isinstance(gdf, gpd.GeoDataFrame) or len(gdf) == 0:
            print(f"  [SKIP] '{layer_name}' — empty or not a GeoDataFrame")
            continue
        # Ensure a consistent CRS (WGS 84)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        gdf.to_file(gpkg_path, layer=layer_name, driver="GPKG")
        saved_layers += 1
        print(f"  [OK]   Saved '{layer_name}' ({len(gdf)} features)")

    # Weight lookup CSV
    df = pd.DataFrame(
        [(k, v) for k, v in sorted(lookup.items(), key=lambda x: x[1], reverse=True)],
        columns=["layer", "scenic_weight_normalised"]
    )
    df.to_csv(csv_path, index=False)

    print(f"\nSaved {saved_layers} layers → {gpkg_path}")
    print(f"Saved weight lookup     → {csv_path}")


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

def run_pipeline() -> tuple[dict, dict]:
    """Execute the full load → weight → save pipeline."""

    print("=" * 60)
    print("Utrecht Scenic Routing — Data Pipeline")
    print("=" * 60)

    # 1. Load data
    print("\n[1/3] Loading scenic datasets …")
    datasets = load_all_scenic_data()
    n_loaded    = sum(1 for gdf in datasets.values()
                      if isinstance(gdf, gpd.GeoDataFrame) and len(gdf) > 0)
    n_empty     = len(datasets) - n_loaded
    print(f"      {n_loaded} layers loaded, {n_empty} empty (WFS failures silenced above)")

    # 2. Assign weights
    print("\n[2/3] Assigning scenicness weights …")
    weighted_datasets, lookup = assign_weights(datasets)
    print_weight_table()

    # 3. Save
    print("\n[3/3] Saving outputs …")
    save_outputs(weighted_datasets, lookup)

    print("\nDone.")
    return weighted_datasets, lookup


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    weighted_datasets, lookup = run_pipeline()

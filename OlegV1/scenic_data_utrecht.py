#!/usr/bin/env python3
"""Build a Utrecht scenic-feature dataset from OSM and Dutch public sources.

Usage:
  python scenic_data_utrecht.py --out data/utrecht_scenic_features.geojson

Notes:
- Utrecht boundary is fetched from OSM via geocoding.
- External datasets are fetched from URLs that can be overridden with env vars
  (or CLI flags) because providers sometimes rotate endpoints.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import geopandas as gpd
import osmnx as ox
import pandas as pd
import requests

# Default candidate endpoints (override via CLI/env if needed)
DEFAULT_ATLAS_MILLS_URL = os.getenv("ATLAS_MILLS_URL", "")
DEFAULT_ATLAS_MONUMENTAL_TREES_URL = os.getenv("ATLAS_MONUMENTAL_TREES_URL", "")
DEFAULT_RIJKSMONUMENTEN_URL = os.getenv("RIJKSMONUMENTEN_URL", "")
DEFAULT_GROENE_RIJKSMONUMENTEN_URL = os.getenv("GROENE_RIJKSMONUMENTEN_URL", "")
DEFAULT_BEELDBEPALEND_PAND_URL = os.getenv("BEELDBEPALEND_PAND_URL", "")


@dataclass
class SourceSpec:
    url: str
    category: str
    source: str


def _fetch_geojson(url: str) -> gpd.GeoDataFrame:
    if not url:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    # Handle FeatureCollection payloads cleanly.
    if isinstance(data, dict) and "features" in data:
        gdf = gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")
    else:
        gdf = gpd.GeoDataFrame.from_features(data, crs="EPSG:4326")

    if gdf.empty:
        return gdf
    return gdf.to_crs("EPSG:4326")


def _clip_to_utrecht(gdf: gpd.GeoDataFrame, utrecht_poly: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    return gpd.clip(gdf, utrecht_poly)


def load_osm_features(utrecht_polygon) -> gpd.GeoDataFrame:
    tags = {
        "tourism": ["artwork"],
        "historic": ["memorial", "monument"],
        "amenity": ["fountain", "bench"],
        "highway": ["pedestrian", "footway", "living_street"],
    }
    raw = ox.features_from_polygon(utrecht_polygon, tags)
    raw = raw.reset_index(drop=False)

    def classify(row: pd.Series) -> Optional[str]:
        if row.get("tourism") == "artwork":
            return "artwork"
        if row.get("historic") == "memorial":
            return "historic_memorial"
        if row.get("historic") == "monument":
            return "historic_monument"
        if row.get("amenity") == "fountain":
            return "fountain"
        if row.get("amenity") == "bench":
            return "bench"

        # Boulevard heuristic: named walkable streets containing boulevard-like words.
        name = str(row.get("name") or "").lower()
        hw = row.get("highway")
        if hw in {"pedestrian", "living_street", "footway"} and any(
            k in name for k in ["boulevard", "singel", "laan"]
        ):
            return "boulevard"
        return None

    raw["category"] = raw.apply(classify, axis=1)
    raw = raw[raw["category"].notna()].copy()
    raw["source"] = "osm"
    raw["feature_name"] = raw.get("name")
    raw["feature_id"] = raw.get("osmid")

    cols = ["source", "category", "feature_id", "feature_name", "geometry"]
    return raw[cols]


def load_external_features(
    specs: Iterable[SourceSpec],
    utrecht_poly: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    frames = []
    for spec in specs:
        gdf = _fetch_geojson(spec.url)
        if gdf.empty:
            continue
        gdf = _clip_to_utrecht(gdf, utrecht_poly)
        if gdf.empty:
            continue

        gdf = gdf.copy()
        gdf["source"] = spec.source
        gdf["category"] = spec.category
        gdf["feature_id"] = gdf.get("id")
        gdf["feature_name"] = gdf.get("name")

        frames.append(gdf[["source", "category", "feature_id", "feature_name", "geometry"]])

    if not frames:
        return gpd.GeoDataFrame(columns=["source", "category", "feature_id", "feature_name", "geometry"], crs="EPSG:4326")

    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")


def get_utrecht_boundary() -> gpd.GeoDataFrame:
    utrecht = ox.geocode_to_gdf("Utrecht, Utrecht, Netherlands")
    utrecht = utrecht.to_crs("EPSG:4326")
    return utrecht[["geometry"]]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/utrecht_scenic_features.geojson")
    p.add_argument("--atlas-mills-url", default=DEFAULT_ATLAS_MILLS_URL)
    p.add_argument("--atlas-monumental-trees-url", default=DEFAULT_ATLAS_MONUMENTAL_TREES_URL)
    p.add_argument("--rijksmonumenten-url", default=DEFAULT_RIJKSMONUMENTEN_URL)
    p.add_argument("--groene-rijksmonumenten-url", default=DEFAULT_GROENE_RIJKSMONUMENTEN_URL)
    p.add_argument("--beeldbepalend-pand-url", default=DEFAULT_BEELDBEPALEND_PAND_URL)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    utrecht_poly = get_utrecht_boundary()
    utrecht_geom = utrecht_poly.geometry.iloc[0]

    osm = load_osm_features(utrecht_geom)

    specs = [
        SourceSpec(args.atlas_mills_url, "mills", "atlas_leefomgeving"),
        SourceSpec(args.atlas_monumental_trees_url, "monumental_trees", "atlas_leefomgeving"),
        SourceSpec(args.rijksmonumenten_url, "rijksmonumenten", "rijk"),
        SourceSpec(args.groene_rijksmonumenten_url, "groene_rijksmonumenten", "gemeente"),
        SourceSpec(args.beeldbepalend_pand_url, "beeldbepalend_pand", "gemeente"),
    ]

    external = load_external_features(specs, utrecht_poly)

    all_features = gpd.GeoDataFrame(pd.concat([osm, external], ignore_index=True), crs="EPSG:4326")
    all_features = all_features.dropna(subset=["geometry"])
    all_features.to_file(args.out, driver="GeoJSON")

    counts: Dict[str, int] = all_features.groupby(["source", "category"]).size().to_dict()
    print("Saved:", args.out)
    print("Counts by (source, category):")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

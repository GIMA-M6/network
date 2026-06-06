"""
data_loader.py — Load ALL scenic-relevant datasets from LOCAL FILES.

Output:
- One dictionary: {layer_name: GeoDataFrame}
"""

import geopandas as gpd
import osmnx as ox
from shapely.geometry import box
import os

import config

# ---------------------------------------------------------------------------
# HELPER FUNCTIE: LOKAAL INLEZEN & FILTEREN OP GEBIED
# ---------------------------------------------------------------------------
def load_local_file(filepath, bounds=None):
    """
    Loads a local GIS file using a pathlib.Path object.
    """
    # Check existence using pathlib syntax
    if not filepath.exists():
        print(f"  [Warning] File not found: {filepath}")
        return gpd.GeoDataFrame()

    try:
        # Convert Path object to string if older versions of Fiona require it,
        # though modern GeoPandas accepts Path objects natively.
        path_str = str(filepath)
        
        if bounds:
            bbox_tuple = (bounds[0], bounds[1], bounds[2], bounds[3])
            gdf = gpd.read_file(path_str, bbox=bbox_tuple, engine="pyogrio")
        else:
            gdf = gpd.read_file(path_str, engine="pyogrio")
            
        print(f"  -> Success: {len(gdf)} objects loaded from {filepath.name}")
        return gdf
    except Exception as e:
        print(f"  [Error] Could not read {filepath.name}: {e}")
        return gpd.GeoDataFrame()

# ---------------------------------------------------------------------------
# 0. STUDY AREA (Blijft via OSM, want dat is heel betrouwbaar)
# ---------------------------------------------------------------------------

def load_study_area():
    try:
        tags = {"boundary": "administrative", "admin_level": "8", "name": "Utrecht"}
        gdf = ox.features_from_place(config.STUDY_AREA_NAME, tags)

        if gdf is not None and len(gdf) > 0:
            geometry = gdf.geometry.iloc[0]
            if geometry.geom_type == "MultiPolygon":
                polygon = max(geometry.geoms, key=lambda x: x.area)
            else:
                polygon = geometry
            
            if polygon.geom_type in ["Polygon", "MultiPolygon"]:
                print(f"Loaded study area boundary from OSM: {config.STUDY_AREA_NAME}")
                return polygon
    except Exception as e:
        print(f"OSM boundary query failed: {e}")

    print(f"Using fallback bbox: {config.STUDY_AREA_BBOX}")
    return box(config.STUDY_AREA_BBOX[0], config.STUDY_AREA_BBOX[1], 
               config.STUDY_AREA_BBOX[2], config.STUDY_AREA_BBOX[3])


# ---------------------------------------------------------------------------
# 1. OSM DATA (Blijft hetzelfde, OSMnx downloadt lokaal heel efficiënt)
# ---------------------------------------------------------------------------

def load_osm_features(polygon):
    print("\n--- Loading OSM Features ---")
    tags = {
        "tourism": ["artwork", "viewpoint", "museum"],
        "amenity": ["fountain", "bench", "theatre"],
        "historic": ["memorial", "monument", "ruins"],
        "leisure": True,
    }

    pois = ox.features_from_polygon(polygon, tags)
    boulevards = ox.features_from_polygon(polygon, {"highway": "pedestrian"})

    def _filter(col, val):
        if col in pois.columns:
            return pois[pois[col] == val]
        return gpd.GeoDataFrame()

    datasets = {
        "osm_artwork":   _filter("tourism", "artwork"),
        "osm_memorial":  _filter("historic", "memorial"),
        "osm_viewpoint": _filter("tourism", "viewpoint"),
        "osm_fountain":  _filter("amenity", "fountain"),
        "osm_ruins":     _filter("historic", "ruins"),
        "osm_theatre":   _filter("amenity", "theatre"),
        "osm_museum":    _filter("tourism", "museum"),
        "osm_leisure":   pois[pois["leisure"].notna()] if "leisure" in pois.columns else gpd.GeoDataFrame(),
        "osm_benches":   _filter("amenity", "bench"),
        "osm_boulevard": boulevards,
    }
    return datasets


# ---------------------------------------------------------------------------
# 2. BGT + BAG DATA (LOKAAL)
# ---------------------------------------------------------------------------

def load_bgt_bag_features(polygon):
    print("\n--- Loading Local BGT & BAG Data ---")
    datasets = {}
    bounds = polygon.bounds

    # BGT Bankjes
    benches = load_local_file(config.PATH_BGT_BENCHES, bounds)
    if not benches.empty and "bgt_functie" in benches.columns:
        datasets["bgt_benches"] = benches[benches["bgt_functie"] == "zitbank"]
    else:
        datasets["bgt_benches"] = benches

    # BGT Water & Groen
    datasets["bgt_water"] = load_local_file(config.PATH_BGT_WATER, bounds)
    datasets["bgt_green"] = load_local_file(config.PATH_BGT_GREEN, bounds)

    # BAG Oude Gebouwen
    bag = load_local_file(config.PATH_BAG_PANDEN, bounds)
    if not bag.empty and "oorspronkelijk_bouwjaar" in bag.columns:
        # Zorg dat bouwjaar numeriek is voor de filter
        bag["oorspronkelijk_bouwjaar"] = bag["oorspronkelijk_bouwjaar"].astype(int, errors='ignore')
        datasets["bag_oude_gebouwen"] = bag[bag["oorspronkelijk_bouwjaar"] < config.BAG_MAX_BUILD_YEAR]
    else:
        datasets["bag_oude_gebouwen"] = bag

    return datasets


# ---------------------------------------------------------------------------
# 3. ATLAS / RCE (LOKAAL)
# ---------------------------------------------------------------------------

def load_atlas_features(polygon):
    print("\n--- Loading Local Atlas (RCE) Data ---")
    datasets = {}
    
    datasets["atlas_rijksmonumenten"] = load_local_file(config.PATH_RCE_MONUMENTEN, polygon.bounds)
    
    return datasets


# ---------------------------------------------------------------------------
# 4. UTRECHT LOKAAL ERFGOED (LOKAAL)
# ---------------------------------------------------------------------------

def load_utrechtopen_erfgoed_features(polygon):
    print("\n--- Loading Local Utrecht Erfgoed ---")
    datasets = {}
    bounds = polygon.bounds

    # Beeldbepalende Panden (Let op de _1 en _2 fallback uit je originele script)
    datasets["utrecht_beeldbepalend_1"] = load_local_file(config.PATH_UTRECHT_BEELDBEPALEND, bounds)
    datasets["erfgoed_gemeentelijk"]    = load_local_file(config.PATH_UTRECHT_GEMEENTELIJK, bounds)

    return datasets


# ---------------------------------------------------------------------------
# 5. MASTER LOADER
# ---------------------------------------------------------------------------

def load_all_scenic_data() -> dict:
    polygon = load_study_area()

    datasets = {}
    datasets.update(load_osm_features(polygon))
    datasets.update(load_bgt_bag_features(polygon))
    datasets.update(load_atlas_features(polygon))
    datasets.update(load_utrechtopen_erfgoed_features(polygon))

    print("\n[SUCCES] Alle lokale datasets zijn verwerkt!")
    return datasets
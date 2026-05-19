"""
data_loader.py — Load ALL scenic-relevant datasets for Utrecht.

Groups:
- OSM (artwork, memorials, viewpoints, fountains, ruins, benches, museums, boulevards, leisure)
- BGT + BAG (benches, water, green, old buildings)
- Atlas Leefomgeving + RIVM (monuments, castles, mills, etc. + noise/air)
- UtrechtOpen + Erfgoedregistratie (beeldbepalende panden, gemeentelijk erfgoed)

Output:
- One dictionary: {layer_name: GeoDataFrame}
"""

import geopandas as gpd
import osmnx as ox
from shapely.geometry import box

import config


# ---------------------------------------------------------------------------
# 0. STUDY AREA
# ---------------------------------------------------------------------------

def load_study_area():
    """
    Load Utrecht administrative boundary from OSM.
    Returns a Shapely polygon for use in data loading functions.
    Falls back to the bounding box defined in config.py.
    """
    try:
        tags = {"boundary": "administrative", "admin_level": "8", "name": "Utrecht"}
        gdf = ox.features_from_place(config.STUDY_AREA_NAME, tags)

        if len(gdf) > 0:
            geometry = gdf.geometry.iloc[0]
            if geometry.geom_type == "MultiPolygon":
                polygon = max(geometry.geoms, key=lambda x: x.area)
            else:
                polygon = geometry
            print(f"Loaded study area boundary from OSM: {config.STUDY_AREA_NAME}")
            return polygon
    except Exception as e:
        print(f"OSM boundary query failed, using fallback bbox: {e}")

    polygon = box(*config.STUDY_AREA_BBOX)
    print(f"Using fallback bbox: {config.STUDY_AREA_BBOX}")
    return polygon


# ---------------------------------------------------------------------------
# 1. OSM DATA
# ---------------------------------------------------------------------------

def load_osm_features(polygon):
    """
    OSM: artwork, memorials, viewpoints, fountains, ruins, benches,
         museums, theatres, leisure, boulevards.
    """
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

    print("Loaded OSM features")
    return datasets


# ---------------------------------------------------------------------------
# 2. BGT + BAG DATA
# ---------------------------------------------------------------------------

def load_bgt_bag_features(polygon):
    """
    BGT: benches, water, green
    BAG: old buildings (bouwjaar < config.BAG_MAX_BUILD_YEAR)
    """
    datasets = {}
    bounds = polygon.bounds

    # BGT benches
    try:
        benches = gpd.read_file(config.BGT_URL, layer="meubilair", bbox=bounds)
        datasets["bgt_benches"] = benches[benches["bgt_functie"] == "zitbank"]
    except Exception as e:
        print(f"Failed to load BGT benches: {e}")
        datasets["bgt_benches"] = gpd.GeoDataFrame()

    # BGT water
    try:
        datasets["bgt_water"] = gpd.read_file(config.BGT_URL, layer="waterdeel", bbox=bounds)
    except Exception as e:
        print(f"Failed to load BGT water: {e}")
        datasets["bgt_water"] = gpd.GeoDataFrame()

    # BGT green
    try:
        datasets["bgt_green"] = gpd.read_file(
            config.BGT_URL, layer="begroeidterreindeel", bbox=bounds
        )
    except Exception as e:
        print(f"Failed to load BGT green: {e}")
        datasets["bgt_green"] = gpd.GeoDataFrame()

    # BAG old buildings
    try:
        bag = gpd.read_file(config.BAG_URL, layer="pand", bbox=bounds)
        datasets["bag_oude_gebouwen"] = bag[
            bag["oorspronkelijk_bouwjaar"] < config.BAG_MAX_BUILD_YEAR
        ]
    except Exception as e:
        print(f"Failed to load BAG old buildings: {e}")
        datasets["bag_oude_gebouwen"] = gpd.GeoDataFrame()

    print("Loaded BGT + BAG features")
    return datasets


# ---------------------------------------------------------------------------
# 3. ATLAS LEEFOMGEVING + RIVM
# ---------------------------------------------------------------------------

def load_atlas_rivm_features(polygon):
    """
    Atlas Leefomgeving: monuments, castles, mills, etc.
    RIVM: road noise and air quality.
    """
    datasets = {}
    bounds = polygon.bounds

    # Atlas layers (defined in config.ATLAS_LAYER_MAP)
    for key, layer in config.ATLAS_LAYER_MAP.items():
        try:
            datasets[key] = gpd.read_file(config.ATLAS_URL, layer=layer, bbox=bounds)
        except Exception as e:
            print(f"Failed to load {key} ({layer}): {e}")
            datasets[key] = gpd.GeoDataFrame()

    # RIVM noise
    try:
        datasets["rivm_noise"] = gpd.read_file(
            config.RIVM_URL, layer="geluid_weg", bbox=bounds
        )
    except Exception as e:
        print(f"Failed to load RIVM noise: {e}")
        datasets["rivm_noise"] = gpd.GeoDataFrame()

    # RIVM air quality
    try:
        datasets["rivm_air"] = gpd.read_file(
            config.RIVM_URL, layer="luchtkwaliteit", bbox=bounds
        )
    except Exception as e:
        print(f"Failed to load RIVM air quality: {e}")
        datasets["rivm_air"] = gpd.GeoDataFrame()

    print("Loaded Atlas Leefomgeving + RIVM features")
    return datasets


# ---------------------------------------------------------------------------
# 4. UTRECHTOPEN + ERFGOEDREGISTRATIE
# ---------------------------------------------------------------------------

def load_utrechtopen_erfgoed_features(polygon):
    """
    UtrechtOpen: beeldbepalende panden (two possible layer name variants)
    Erfgoedregistratie: gemeentelijk erfgoed
    """
    datasets = {}
    bounds = polygon.bounds

    for key, layer in [
        ("utrecht_beeldbepalend_1", "utrechtopen:beeldbepalend_pand"),
        ("utrecht_beeldbepalend_2", "utrechtopen:beeldbepalende_panden"),
    ]:
        try:
            datasets[key] = gpd.read_file(config.UTRECHTOPEN_URL, layer=layer, bbox=bounds)
        except Exception as e:
            print(f"Failed to load {key} ({layer}): {e}")
            datasets[key] = gpd.GeoDataFrame()

    try:
        datasets["erfgoed_gemeentelijk"] = gpd.read_file(
            config.ERFGOED_URL, layer="erfgoed", bbox=bounds
        )
    except Exception as e:
        print(f"Failed to load erfgoed_gemeentelijk: {e}")
        datasets["erfgoed_gemeentelijk"] = gpd.GeoDataFrame()

    print("Loaded UtrechtOpen + Erfgoed features")
    return datasets


# ---------------------------------------------------------------------------
# 5. MASTER LOADER
# ---------------------------------------------------------------------------

def load_all_scenic_data() -> dict:
    """
    Run all loaders and return a single merged dict:
        {layer_name: GeoDataFrame}
    """
    polygon = load_study_area()

    datasets = {}
    datasets.update(load_osm_features(polygon))
    datasets.update(load_bgt_bag_features(polygon))
    datasets.update(load_atlas_rivm_features(polygon))
    datasets.update(load_utrechtopen_erfgoed_features(polygon))

    return datasets

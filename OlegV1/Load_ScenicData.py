"""
Load ALL scenic-relevant datasets for Utrecht in one modular script.

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

# -------------------------------------------------------------------
# 0. STUDY AREA
# -------------------------------------------------------------------

def load_study_area():
    """
    Load your study area polygon.
    Option A: from GeoJSON/shapefile (recommended)
    Option B: from hard-coded bbox (fallback)
    """
    try:
        sa = gpd.read_file("../data/study_area.geojson")
        polygon = sa.geometry.iloc[0]
        print("✅ Loaded study area from ../data/study_area.geojson")
    except Exception:
        from shapely.geometry import box
        # Fallback: Utrecht-ish bbox (adjust if needed)
        polygon = box(4.98, 52.05, 5.18, 52.17)
        print("⚠️ Using fallback bbox for study area")
    return polygon


# -------------------------------------------------------------------
# 1. OSM DATA
# -------------------------------------------------------------------

def load_osm_features(polygon):
    """
    OSM: artwork, memorials, viewpoints, fountains, ruins, benches,
         museums, theatres, leisure, boulevards.
    """
    tags = {
        "tourism": ["artwork", "viewpoint", "museum"],
        "amenity": ["fountain", "bench", "theatre"],
        "historic": ["memorial", "monument", "ruins"],
        "leisure": True
    }

    pois = ox.features_from_polygon(polygon, tags)
    boulevards = ox.features_from_polygon(polygon, {"highway": "pedestrian"})

    datasets = {
    "osm_artwork": pois[pois["tourism"] == "artwork"] if "tourism" in pois.columns else gpd.GeoDataFrame(),
    "osm_memorial": pois[pois["historic"] == "memorial"] if "historic" in pois.columns else gpd.GeoDataFrame(),
    "osm_viewpoint": pois[pois["tourism"] == "viewpoint"] if "tourism" in pois.columns else gpd.GeoDataFrame(),
    "osm_fountain": pois[pois["amenity"] == "fountain"] if "amenity" in pois.columns else gpd.GeoDataFrame(),
    "osm_ruins": pois[pois["historic"] == "ruins"] if "historic" in pois.columns else gpd.GeoDataFrame(),
    "osm_theatre": pois[pois["amenity"] == "theatre"] if "amenity" in pois.columns else gpd.GeoDataFrame(),
    "osm_museum": pois[pois["tourism"] == "museum"] if "tourism" in pois.columns else gpd.GeoDataFrame(),
    "osm_leisure": pois[pois["leisure"].notna()] if "leisure" in pois.columns else gpd.GeoDataFrame(),
    "osm_benches": pois[pois["amenity"] == "bench"] if "amenity" in pois.columns else gpd.GeoDataFrame(),
    "osm_boulevard": boulevards
}

    print("✅ Loaded OSM features")
    return datasets


# -------------------------------------------------------------------
# 2. BGT + BAG DATA
# -------------------------------------------------------------------

BGT_URL = "https://service.pdok.nl/kadaster/bgt/wfs/v1_1"
BAG_URL = "https://service.pdok.nl/lv/bag/wfs/v2_0"

def load_bgt_bag_features(polygon):
    """
    BGT: benches, water, green
    BAG: old buildings (oude gebouwen)
    """
    datasets = {}

    # BGT benches
    try:
        benches = gpd.read_file(BGT_URL, layer="meubilair", bbox=polygon.bounds)
        benches = benches[benches["bgt_functie"] == "zitbank"]
        datasets["bgt_benches"] = benches
    except Exception:
        datasets["bgt_benches"] = gpd.GeoDataFrame()

    # BGT water
    try:
        water = gpd.read_file(BGT_URL, layer="waterdeel", bbox=polygon.bounds)
        datasets["bgt_water"] = water
    except Exception:
        datasets["bgt_water"] = gpd.GeoDataFrame()

    # BGT green
    try:
        green = gpd.read_file(BGT_URL, layer="begroeidterreindeel", bbox=polygon.bounds)
        datasets["bgt_green"] = green
    except Exception:
        datasets["bgt_green"] = gpd.GeoDataFrame()

    # BAG oude gebouwen
    try:
        bag = gpd.read_file(BAG_URL, layer="pand", bbox=polygon.bounds)
        oude = bag[bag["oorspronkelijk_bouwjaar"] < 1900]
        datasets["bag_oude_gebouwen"] = oude
    except Exception:
        datasets["bag_oude_gebouwen"] = gpd.GeoDataFrame()

    print("✅ Loaded BGT + BAG features")
    return datasets


# -------------------------------------------------------------------
# 3. ATLAS LEEFKRING + RIVM
# -------------------------------------------------------------------

ATLAS_URL = "https://geodata.nationaalgeoregister.nl/atlasleefomgeving/wfs"
RIVM_URL = "https://geodata.rivm.nl/geoserver/wfs"

ATLAS_LAYER_MAP = {
    "atlas_rijksmonumenten": "Rijksmonumenten",
    "atlas_molens": "Molens",
    "atlas_kastelen": "Kastelen",
    "atlas_groene_rijksmonumenten": "GroeneRijksmonumenten",
    "atlas_grafheuvels": "Grafheuvels",
    "atlas_stadsgezichten": "StadsEnDorpsGezichten"
}

def load_atlas_rivm_features(polygon):
    """
    Atlas Leefomgeving: monuments, castles, mills, etc.
    RIVM: noise, air (optionally light if available).
    """
    datasets = {}

    # Atlas layers
    for key, layer in ATLAS_LAYER_MAP.items():
        try:
            gdf = gpd.read_file(ATLAS_URL, layer=layer, bbox=polygon.bounds)
            datasets[key] = gdf
        except Exception:
            datasets[key] = gpd.GeoDataFrame()

    # RIVM noise + air (layer names may need adjustment)
    try:
        noise = gpd.read_file(RIVM_URL, layer="geluid_weg", bbox=polygon.bounds)
        datasets["rivm_noise"] = noise
    except Exception:
        datasets["rivm_noise"] = gpd.GeoDataFrame()

    try:
        air = gpd.read_file(RIVM_URL, layer="luchtkwaliteit", bbox=polygon.bounds)
        datasets["rivm_air"] = air
    except Exception:
        datasets["rivm_air"] = gpd.GeoDataFrame()

    print("✅ Loaded Atlas Leefomgeving + RIVM features")
    return datasets


# -------------------------------------------------------------------
# 4. UTRECHTOPEN + ERFGOEDREGISTRATIE
# -------------------------------------------------------------------

UTRECHTOPEN_URL = "https://open.utrecht.nl/geoserver/utrechtopen/ows"
ERFGOED_URL = "https://erfgoedregistratie.nl/geoserver/wfs"

def load_utrechtopen_erfgoed_features(polygon):
    """
    UtrechtOpen: beeldbepalende panden
    Erfgoedregistratie: gemeentelijk erfgoed
    """
    datasets = {}

    # UtrechtOpen – layer names may need to be checked in capabilities
    try:
        beeld1 = gpd.read_file(
            UTRECHTOPEN_URL,
            layer="utrechtopen:beeldbepalend_pand",
            bbox=polygon.bounds
        )
        datasets["utrecht_beeldbepalend_1"] = beeld1
    except Exception:
        datasets["utrecht_beeldbepalend_1"] = gpd.GeoDataFrame()

    try:
        beeld2 = gpd.read_file(
            UTRECHTOPEN_URL,
            layer="utrechtopen:beeldbepalende_panden",
            bbox=polygon.bounds
        )
        datasets["utrecht_beeldbepalend_2"] = beeld2
    except Exception:
        datasets["utrecht_beeldbepalend_2"] = gpd.GeoDataFrame()

    # Erfgoedregistratie – gemeentelijk erfgoed
    try:
        erfgoed = gpd.read_file(
            ERFGOED_URL,
            layer="erfgoed",
            bbox=polygon.bounds
        )
        datasets["erfgoed_gemeentelijk"] = erfgoed
    except Exception:
        datasets["erfgoed_gemeentelijk"] = gpd.GeoDataFrame()

    print("✅ Loaded UtrechtOpen + Erfgoed features")
    return datasets


# -------------------------------------------------------------------
# 5. MASTER LOADER
# -------------------------------------------------------------------

def load_all_scenic_data():
    polygon = load_study_area()

    datasets = {}
    datasets.update(load_osm_features(polygon))
    datasets.update(load_bgt_bag_features(polygon))
    datasets.update(load_atlas_rivm_features(polygon))
    datasets.update(load_utrechtopen_erfgoed_features(polygon))

    return datasets




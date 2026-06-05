"""
config.py — Central configuration for the Utrecht Scenic Routing project.

Edit this file to change the study area, data source URLs, or output paths.
"""

# ---------------------------------------------------------------------------
# STUDY AREA
# ---------------------------------------------------------------------------

STUDY_AREA_NAME = "Utrecht, Netherlands"

# Fallback bounding box used if the OSM boundary query fails.
# Format: (min_lon, min_lat, max_lon, max_lat)
STUDY_AREA_BBOX = (5.05, 52.05, 5.20, 52.15)


# ---------------------------------------------------------------------------
# DATA SOURCE URLs
# ---------------------------------------------------------------------------

# BGT (Basisregistratie Grootschalige Topografie) — Kadaster WFS
BGT_URL = "https://api.pdok.nl/lv/bgt/ogc/v1_0/collections"

# BAG (Basisregistraties Adressen en Gebouwen) — Kadaster WFS
BAG_URL = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections"

# RCE (Rijksdienst voor het Cultureel Erfgoed)(was eerst: "Atlas Leefomgeving") — GeoServer WFS)
ATLAS_URL = "https://api.pdok.nl/lv/bag/ogc/v1/collections"

# RIVM — GeoServer WFS
RIVM_URL = "https://data.rivm.nl/geo/wfs?request=GetCapabilities&service=WFS"

# UtrechtOpen — GeoServer WFS
UTRECHTOPEN_URL = "https://geodata.utrecht.nl/geoserver/UtrechtOpen/ows?service=WFS&version=1.0.0&request=GetCapabilities"

# Erfgoedregistratie — GeoServer WFS
ERFGOED_URL = "https://data.geo.cultureelerfgoed.nl/openbaar/wfs?service=WFS&request=GetCapabilities"

# ---------------------------------------------------------------------------
# ATLAS LAYER NAMES
# ---------------------------------------------------------------------------
# Maps internal dataset key → WFS layer name on the Atlas Leefomgeving service.
# Update these if the remote layer names change.

ATLAS_LAYER_MAP = {
    "atlas_rijksmonumenten":        "Rijksmonumenten",
    "atlas_molens":                 "Molens",
    "atlas_kastelen":               "Kastelen",
    "atlas_groene_rijksmonumenten": "GroeneRijksmonumenten",
    "atlas_grafheuvels":            "Grafheuvels",
    "atlas_stadsgezichten":         "StadsEnDorpsGezichten",
}


# ---------------------------------------------------------------------------
# BAG FILTER
# ---------------------------------------------------------------------------

# Only buildings constructed before this year are kept as "oude gebouwen".
BAG_MAX_BUILD_YEAR = 1900


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

# Directory where output files (GeoPackage, CSV) will be saved.
OUTPUT_DIR = "C:\\GIMA\\Module 6\\Code\\network\\scenic\\results"

# GeoPackage file name for the weighted layers.
OUTPUT_GPKG = "utrecht_scenic_weighted.gpkg"

# CSV file name for the weight lookup table.
OUTPUT_WEIGHT_CSV = "scenic_weight_lookup.csv"

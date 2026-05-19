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
BGT_URL = "https://service.pdok.nl/kadaster/bgt/wfs/v1_1"

# BAG (Basisregistraties Adressen en Gebouwen) — Kadaster WFS
BAG_URL = "https://service.pdok.nl/lv/bag/wfs/v2_0"

# Atlas Leefomgeving — PDOK WFS
ATLAS_URL = "https://geodata.nationaalgeoregister.nl/atlasleefomgeving/wfs"

# RIVM — GeoServer WFS
RIVM_URL = "https://geodata.rivm.nl/geoserver/wfs"

# UtrechtOpen — GeoServer WFS
UTRECHTOPEN_URL = "https://open.utrecht.nl/geoserver/utrechtopen/ows"

# Erfgoedregistratie — GeoServer WFS
ERFGOED_URL = "https://erfgoedregistratie.nl/geoserver/wfs"


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
OUTPUT_DIR = "output"

# GeoPackage file name for the weighted layers.
OUTPUT_GPKG = "utrecht_scenic_weighted.gpkg"

# CSV file name for the weight lookup table.
OUTPUT_WEIGHT_CSV = "scenic_weight_lookup.csv"

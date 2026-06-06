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
# LOCAL DATA PATHS (Vervang deze paden met waar jouw bestanden staan!)
# ---------------------------------------------------------------------------

# Maak een variabele voor je hoofd-datamap, dat is makkelijker
import os
from pathlib import Path

# BASE_DIR points to the directory containing config.py
BASE_DIR = Path(__file__).resolve().parent

# Define your data and results directories relative to the project root
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "results"

# Automatically create the directories if they don't exist yet
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# BGT
PATH_BGT_BENCHES = os.path.join(DATA_DIR, "bgt_straatmeubilair.geojson")
PATH_BGT_WATER   = os.path.join(DATA_DIR, "bgt_waterdeel.geojson")
PATH_BGT_GREEN   = os.path.join(DATA_DIR, "bgt_begroeid.geojson")

# BAG
PATH_BAG_PANDEN  = os.path.join(DATA_DIR, "bag_panden_utrecht.geojson")

# RCE (Rijksmonumenten)
PATH_RCE_MONUMENTEN = os.path.join(DATA_DIR, "rce_rijksmonumenten.geojson")

# Utrecht Lokaal
PATH_UTRECHT_BEELDBEPALEND = os.path.join(DATA_DIR, "utrecht_beeldbepalend.geojson")
PATH_UTRECHT_GEMEENTELIJK  = os.path.join(DATA_DIR, "utrecht_gemeentelijk_erfgoed.geojson")

# ---------------------------------------------------------------------------
# ATLAS LAYER NAMES
# ---------------------------------------------------------------------------
# Maps internal dataset key → WFS layer name on the Atlas Leefomgeving service
# Update these if the remote layer names change.

ATLAS_LAYER_MAP = {
    "atlas_rijksmonumenten": "rijksmonumentpunten",
}


# ---------------------------------------------------------------------------
# BAG FILTER
# ---------------------------------------------------------------------------

# Only buildings constructed before this year are kept as "oude gebouwen".
BAG_MAX_BUILD_YEAR = 1900


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

OUTPUT_GPKG = OUTPUT_DIR / "utrecht_scenic_weighted.gpkg"
OUTPUT_WEIGHT_CSV = OUTPUT_DIR / "scenic_weight_lookup.csv"

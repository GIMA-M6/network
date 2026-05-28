# Utrecht Scenic Routing


---

#### PROJECT STRUCTURE  #####

```
.
├── .github/workflows     #Linking structure to sync Github repository with HuggingFace Server repository
├── hf_deploy             #Contains all files relevant for route planner uploaded to HuggingFace Server
├── network_base          #Contains all basic OSM network files (code and results)
    └── extra               #Contains leftovers of network files
└── scenic                #Contains all files relevant to scenic network
    └── extra               #Contains leftovers of scenic code

```

---

Check API server status on: https://huggingface.co/spaces/OlegBergs/route_backend_api/tree/main

Load, weight, and export scenic geographic datasets for Utrecht (Netherlands).  
Weights are derived from empirical scenicness coefficients (see [Data & Methods](#data--methods)).



```
.
├── data_loader.py        # Loads all raw datasets (OSM, BGT, BAG, Atlas, RIVM, UtrechtOpen)
├── scenic_weights.py     # Assigns normalised scenicness weights to each layer
├── config.py             # All URLs, study area settings, and output paths
├── main.py               # Entry point — runs the full pipeline
├── requirements.txt      # Python dependencies
└── output/               # Created automatically on first run
    ├── utrecht_scenic_weighted.gpkg
    └── scenic_weight_lookup.csv
```

---

## Requirements

- **Python ≥ 3.9**
- Internet access (data is fetched live from public WFS endpoints)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

This runs the full pipeline:

1. **Load** — queries OSM, BGT, BAG, Atlas Leefomgeving, RIVM, and UtrechtOpen WFS services for Utrecht
2. **Weight** — assigns each feature a normalised scenic weight (`0–1`)
3. **Save** — writes a GeoPackage and CSV to the `output/` folder

---

## Outputs

| File | Description |
|---|---|
| `output/utrecht_scenic_weighted.gpkg` | All layers as a multi-layer GeoPackage (EPSG:4326). Each feature has a `scenic_weight` (0–1) and `scenic_weight_raw` column. |
| `output/scenic_weight_lookup.csv` | Layer-level weight lookup table, sorted descending. |

The GeoPackage can be opened directly in QGIS, ArcGIS, or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_file("output/utrecht_scenic_weighted.gpkg", layer="atlas_rijksmonumenten")
```

---

## Data & Methods

### Scenicness Coefficients

Weights are derived from a forest-plot of scene-label coefficients representing the effect of visual scene elements on perceived scenicness (scale: *Change in Scenicness Rating*).

Each dataset layer is mapped to one or more scene labels. The layer weight is the mean of its mapped coefficients, then min-max normalised to `[0, 1]` across all layers.

**Top-weighted layers (≥ 0.90):**

| Layer | Mapped labels | Normalised weight |
|---|---|---|
| `atlas_rijksmonumenten` | Listed Building | ~1.00 |
| `atlas_kastelen` | Listed Building, Manor House | ~0.94 |
| `bag_oude_gebouwen` | Listed Building, Manor House | ~0.94 |
| `utrecht_beeldbepalend_1/2` | Listed Building, Manor House | ~0.94 |
| `atlas_molens` | Listed Building, Natural Landscape | ~0.90 |

**Lowest-weighted layers (negative raw scores → near 0):**

| Layer | Mapped labels | Normalised weight |
|---|---|---|
| `rivm_noise` | Highway, Motor Vehicle, Train | ~0.02 |
| `rivm_air` | Asphalt, Commercial Building, Gas | ~0.00 |
| `osm_boulevard` | Asphalt, Road Surface | ~0.06 |

### Data Sources

| Source | Coverage | Access |
|---|---|---|
| OpenStreetMap (via `osmnx`) | POIs, leisure, water, roads | Public |
| BGT — Kadaster | Benches, water, green areas | Public WFS |
| BAG — Kadaster | Building age (pre-1900) | Public WFS |
| Atlas Leefomgeving | Monuments, castles, mills, stadsgezichten | Public WFS |
| RIVM | Road noise, air quality | Public WFS |
| UtrechtOpen | Beeldbepalende panden | Public WFS |
| Erfgoedregistratie | Gemeentelijk erfgoed | Public WFS |

> **Note:** Several WFS services (RIVM, Atlas Leefomgeving, UtrechtOpen) may be intermittently unavailable or change layer names. Failed layers are silently skipped and returned as empty GeoDataFrames — check the console output for `[SKIP]` messages.

---

## Configuration

Edit `config.py` to change:
- Study area name or fallback bounding box
- WFS service URLs
- BAG building-age filter year
- Output directory and file names

---

## Known Limitations

- WFS endpoints are queried live — results depend on external service availability.
- The `Reservoir` label has a large negative coefficient (−0.55) in the source data; `bgt_water` is mapped to `Watercourse + Water` (moderately negative) rather than `Reservoir` to better reflect Utrecht's canal network.
- Weights are static per layer — they do not vary by feature attributes within a layer.

- How to Upload a New GraphML File to the Project
This guide explains how to replace the routing graph file (utrecht_network.graphml) so it automatically deploys to the route planner.

One-Time Setup (do this once on your PC)
1. Install Git LFS
Git LFS is required to handle the large .graphml file.

Download and install from: https://git-lfs.github.com
After installing, open a terminal (or VS Code terminal) and run:

  git lfs install
2. Clone the repository (if you haven't already)
In VS Code, go to File → Clone Repository and paste the GitHub repo URL.
Or in the terminal:
git clone <your-repo-url>

Uploading a New GraphML File
Step 1 — Replace the file
Navigate to the hf_deploy/ folder in the project and replace utrecht_network.graphml with your new version. Keep the filename exactly the same:
utrecht_network.graphml
Step 2 — Open the terminal in VS Code
Go to Terminal → New Terminal in the top menu.
Step 3 — Stage the file
git add hf_deploy/utrecht_network.graphml
Step 4 — Commit the change
git commit -m "Update routing graph"
Step 5 — Push to GitHub
git push
That's it! GitHub Actions will automatically deploy the new file to the route planner on Hugging Face within a minute or two.

How to Check if the Deploy Worked

Go to the GitHub repository in your browser
Click the Actions tab at the top
You should see a workflow run in progress or completed with a ✅ green checkmark

If you see a ❌ red cross, let Oleg know.

Common Mistakes
ProblemFixForgot to install Git LFSRun git lfs install first, then try againNamed the file differentlyRename it back to utrecht_network.graphml exactlyPush was rejectedMake sure you have write access to the repositoryNothing happened after pushCheck the file is inside the hf_deploy/ folder

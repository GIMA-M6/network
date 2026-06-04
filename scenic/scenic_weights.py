import geopandas as gpd

SCENIC_WEIGHT_LOOKUP = {
    "atlas_kastelen":               0.90,
    "atlas_rijksmonumenten":        0.85,
    "utrecht_beeldbepalend_1":      0.80,
    "atlas_groene_rijksmonumenten": 0.78,
    "atlas_molens":                 0.75,
    "utrecht_beeldbepalend_2":      0.72,
    "bag_oude_gebouwen":            0.70,
    "erfgoed_gemeentelijk":         0.65,
    "osm_ruins":                    0.65,
    "atlas_stadsgezichten":         0.63,
    "osm_museum":                   0.60,
    "osm_theatre":                  0.55,
    "osm_viewpoint":                0.55,
    "bgt_water":                    0.50,
    "bgt_green":                    0.48,
    "osm_leisure":                  0.45,
    "atlas_grafheuvels":            0.45,
    "osm_artwork":                  0.42,
    "osm_memorial":                 0.40,
    "osm_fountain":                 0.35,
    "osm_benches":                  0.25,
    "bgt_benches":                  0.25,
    "osm_boulevard":                0.15,
}


def assign_weights(datasets):
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

        weighted_datasets[layer_name] = gdf

    print(f"\nWeights assigned to {len(present_lookup)} layers.")
    return weighted_datasets, present_lookup
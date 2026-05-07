import osmnx as ox
import geopandas as gpd

def load_osm_scenic_data(polygon):
    tags = {
        "tourism": ["artwork", "viewpoint", "museum"],
        "amenity": ["fountain", "bench", "theatre"],
        "historic": ["memorial", "monument", "ruins"],
        "leisure": True
    }

    pois = ox.features_from_polygon(polygon, tags)
    boulevards = ox.features_from_polygon(polygon, {"highway": "pedestrian"})

    return {
        "artwork": pois[pois.get("tourism") == "artwork"],
        "memorial": pois[pois.get("historic") == "memorial"],
        "viewpoint": pois[pois.get("tourism") == "viewpoint"],
        "fountain": pois[pois.get("amenity") == "fountain"],
        "ruins": pois[pois.get("historic") == "ruins"],
        "theatre": pois[pois.get("amenity") == "theatre"],
        "museum": pois[pois.get("tourism") == "museum"],
        "leisure": pois[pois.get("leisure").notna()],
        "benches": pois[pois.get("amenity") == "bench"],
        "boulevard": boulevards
    }

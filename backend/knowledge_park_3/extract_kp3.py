"""
Knowledge Park 3 (Greater Noida) — Geospatial Data Extraction Script.
Extracts:
1. Road graph from OSM (Knowledge Park 3 area)
2. 3D Building polygons with levels/heights
3. Water bodies and drainage channels
4. Elevation and surface runoff features
"""
import os
import sys
import json

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import osmnx as ox
import geopandas as gpd
from shapely.geometry import mapping

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Knowledge Park 2 & 3, Greater Noida Strict Bounding Box
# Strictly Knowledge Park 2 & 3: Sharda University, GL Bajaj, Galgotias, NIET, GNIOT, IIMT
# Strictly excludes Pari Chowk (east of 77.500) and Alpha sectors (east of 77.505)
S_lat, N_lat = 28.4560, 28.4860
W_lon, E_lon = 77.4780, 77.4980

print("=" * 64)
print("[KP3] EXTRACTING GEOSPATIAL DATA FOR KNOWLEDGE PARK 3, GREATER NOIDA")
print(f"      Latitude:  {S_lat:.4f}N to {N_lat:.4f}N")
print(f"      Longitude: {W_lon:.4f}E to {E_lon:.4f}E")
print("=" * 64)

# Configure OSMnx settings
ox.settings.use_cache = True
ox.settings.log_console = False

# In OSMnx 2.x, bbox is (left, bottom, right, top) = (west, south, east, north)
bbox = (W_lon, S_lat, E_lon, N_lat)

print("\n[1/4] Fetching Road Network from OpenStreetMap...")
G = ox.graph_from_bbox(bbox=bbox, network_type="all", simplify=True)
G = ox.truncate.largest_component(G)
print(f"      [OK] Road Graph extracted: {len(G.nodes):,} nodes | {len(G.edges):,} edges")

print("\n[2/4] Fetching 3D Buildings & Water Bodies...")
tags_buildings = {"building": True}
tags_water = {"natural": "water", "waterway": True, "water": True}

try:
    buildings = ox.features_from_bbox(bbox=bbox, tags=tags_buildings)
except Exception as e:
    print(f"Building query: {e}")
    buildings = gpd.GeoDataFrame()

try:
    water_bodies = ox.features_from_bbox(bbox=bbox, tags=tags_water)
except Exception as e:
    print(f"Water query: {e}")
    water_bodies = gpd.GeoDataFrame()

# Filter polygons only
if len(buildings) > 0:
    buildings = buildings[buildings.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
if len(water_bodies) > 0:
    water_bodies = water_bodies[water_bodies.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()

print(f"      [OK] Extracted {len(buildings):,} buildings and {len(water_bodies):,} water features")

print("\n[3/4] Modeling Elevation (~195m-205m) and Surface Runoff...")
cLat, cLon = 28.4710, 77.4880

# Greater Noida base elevation is ~198m above sea level with gentle slope towards Hindon basin
for n, data in G.nodes(data=True):
    lat_diff = data["y"] - cLat
    lon_diff = data["x"] - cLon
    # Natural terrain depression towards south-east drainage slope
    G.nodes[n]["elevation"] = 200.0 + (lat_diff * 120.0) - (lon_diff * 90.0) + float(np.random.uniform(-0.5, 0.5))

for u, v, k, data in G.edges(data=True, keys=True):
    highway = data.get('highway', 'residential')
    if isinstance(highway, list):
        highway = highway[0]

    # Expressways / Major avenues have high runoff
    coeff = 0.92 if highway in ['primary', 'motorway', 'trunk', 'secondary'] else 0.70
    G.nodes[u]["runoff_coeff"] = coeff
    G.nodes[v]["runoff_coeff"] = coeff

print("\n[4/4] Saving Knowledge Park 3 Assets...")

# 1. GraphML
graphml_path = os.path.join(OUTPUT_DIR, "kp3_focused.graphml")
ox.save_graphml(G, graphml_path)
print(f"      Saved: {graphml_path}")

# 2. Buildings GeoJSON with height
bldg_list = []
for _, row in buildings.iterrows():
    try:
        levels = float(row.get("building:levels", 3)) # Knowledge Park colleges avg 3-5 floors
        height = float(row.get("height", levels * 3.8))
        name = str(row.get("name", "Academic / Institutional Building"))
        bldg_list.append({
            "type": "Feature",
            "geometry": mapping(row.geometry),
            "properties": {
                "name": name,
                "height": height,
                "levels": levels
            }
        })
    except Exception:
        continue

bldg_geojson_path = os.path.join(OUTPUT_DIR, "kp3_buildings.geojson")
with open(bldg_geojson_path, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": bldg_list}, f)
print(f"      Saved: {bldg_geojson_path} ({len(bldg_list)} buildings)")

# 3. Water GeoJSON
water_list = []
for _, row in water_bodies.iterrows():
    try:
        water_list.append({
            "type": "Feature",
            "geometry": mapping(row.geometry),
            "properties": {"name": str(row.get("name", "Drainage / Water Channel"))}
        })
    except Exception:
        continue

water_geojson_path = os.path.join(OUTPUT_DIR, "kp3_water.geojson")
with open(water_geojson_path, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": water_list}, f)
print(f"      Saved: {water_geojson_path} ({len(water_list)} water features)")

# 4. Deck.gl Basemap JSON
deck_nodes, deck_edges = [], []
for i, (n, data) in enumerate(G.nodes(data=True)):
    deck_nodes.append({"id": i, "lon": data['x'], "lat": data['y'], "elev": data['elevation']})
for u, v, data in G.edges(data=True):
    deck_edges.append({"source": [G.nodes[u]['x'], G.nodes[u]['y']], "target": [G.nodes[v]['x'], G.nodes[v]['y']]})

basemap_path = os.path.join(OUTPUT_DIR, "deckgl_basemap_kp3.json")
with open(basemap_path, "w", encoding="utf-8") as f:
    json.dump({"nodes": deck_nodes, "edges": deck_edges}, f)
print(f"      Saved: {basemap_path}")

print(f"\n{'='*64}")
print(f"EXTRACTION COMPLETED! Node Count: {len(G.nodes):,}, Edge Count: {len(G.edges):,}")
print(f"{'='*64}")

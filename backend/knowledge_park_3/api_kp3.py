"""
Knowledge Park 3 (Greater Noida) — Dedicated Digital Twin API.
Completely isolated module for Greater Noida crisis simulation and routing.
"""
import os
import sys
import json
import math
import re
import uuid
import urllib.request
from datetime import datetime, timezone

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import torch
import networkx as nx
import osmnx as ox
import numpy as np
from pydantic import BaseModel
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from train_kp3 import FloodSurrogateModel, get_batched_edge_index

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
T = 12

print("[KP3 API] Loading Knowledge Park 3 Graph...")
GRAPH_PATH = os.path.join(BASE_DIR, "kp3_focused.graphml")
G = ox.load_graphml(GRAPH_PATH)
nodes = list(G.nodes())
num_nodes = len(nodes)
node_to_idx = {node: i for i, node in enumerate(nodes)}

print("[KP3 API] Loading Model Weights and Features...")
val_data = torch.load(os.path.join(BASE_DIR, "val_dataset_kp3.pt"), map_location="cpu", weights_only=False)
X_sample = val_data["X"][0]
edge_index = val_data["edge_index"].to(DEVICE)

static_elev = X_sample[:, 0, 0].to(DEVICE)
static_runoff = X_sample[:, 0, 4].to(DEVICE)
static_flow_acc = X_sample[:, 0, 5].to(DEVICE)

model = FloodSurrogateModel(num_nodes=num_nodes).to(DEVICE)
weights_path = os.path.join(BASE_DIR, "stgcn_weights_kp3.pth")
if os.path.exists(weights_path):
    model.load_state_dict(torch.load(weights_path, map_location=DEVICE))
    print("[KP3 API] Loaded trained weights successfully!")
model.eval()

b_edge = get_batched_edge_index(edge_index, num_nodes, 1, DEVICE)

# Router for Knowledge Park 3 endpoints
kp3_router = APIRouter(tags=["Knowledge Park 3 Digital Twin"])

class StormRequest(BaseModel):
    intensity: float

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    intensity: float

# ── 1. WEATHER (Open-Meteo for Greater Noida coordinates) ──
@kp3_router.get("/weather")
async def get_kp3_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=28.4728&longitude=77.4985&current=rain,precipitation&timezone=Asia/Kolkata"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EvacX-KP3/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        current = data.get("current", {})
        rain = current.get("rain", 0.0)
        precip = current.get("precipitation", 0.0)
        rate = max(rain, precip)

        if rate == 0:
            intensity = 0.05
            condition = "Clear / Dry"
        elif rate < 2.5:
            intensity = 0.20
            condition = "Light Rain"
        elif rate < 7.5:
            intensity = 0.45
            condition = "Moderate Rain"
        elif rate < 30.0:
            intensity = 0.75
            condition = "Heavy Rain"
        else:
            intensity = 1.0
            condition = "Violent Storm"

        return {
            "location": "Knowledge Park 3, Greater Noida",
            "rain_mm": rate,
            "condition": condition,
            "intensity": intensity,
            "time": current.get("time", ""),
        }
    except Exception as e:
        return {"error": str(e), "intensity": 0.3, "condition": "Offline Default"}

# ── 2. SIMULATION ──
@kp3_router.post("/simulate")
async def simulate_kp3_flood(req: StormRequest):
    intensity = max(0.0, min(1.0, req.intensity))
    envelope = torch.exp(-0.5 * ((torch.arange(T, dtype=torch.float32, device=DEVICE) - T / 2) / 2.0) ** 2)
    X_new = torch.zeros((1, num_nodes, T, 6), device=DEVICE)

    for t in range(T):
        X_new[0, :, t, 0] = static_elev
        X_new[0, :, t, 1] = intensity * envelope[t]
        X_new[0, :, t, 2] = (intensity * envelope[:t+1].sum()) / 12.0
        X_new[0, :, t, 3] = t / float(T)
        X_new[0, :, t, 4] = static_runoff
        X_new[0, :, t, 5] = static_flow_acc

    with torch.no_grad():
        out = model(X_new, b_edge)
    depths = out[0].cpu().numpy()
    if intensity <= 0.05:
        depths.fill(0.0)

    max_depths = depths.max(axis=1)
    node_depths = {nodes[i]: float(max_depths[i]) for i in range(num_nodes)}

    roads = []
    for u, v, edata in G.edges(data=True):
        d_u = node_depths.get(u, 0.0)
        d_v = node_depths.get(v, 0.0)
        avg_depth = (d_u + d_v) / 2.0
        roads.append({
            "from": [float(G.nodes[u]['x']), float(G.nodes[u]['y'])],
            "to":   [float(G.nodes[v]['x']), float(G.nodes[v]['y'])],
            "depth": round(avg_depth, 2)
        })

    points = [{"lon": float(G.nodes[nodes[i]]['x']), "lat": float(G.nodes[nodes[i]]['y']), "depth": float(max_depths[i])} for i in range(num_nodes)]

    timeline = []
    for t in range(T):
        timeline.append([round(float(depths[i, t]), 2) for i in range(num_nodes)])

    features = []
    for i, node in enumerate(nodes):
        node_depth_timeline = [round(float(depths[i, t]), 3) for t in range(T)]
        max_d = round(float(max_depths[i]), 3)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [G.nodes[node]['x'], G.nodes[node]['y']]},
            "properties": {
                "node_id": str(node),
                "depth": max_d,
                "depth_timeline": node_depth_timeline,
                "elevation": round(float(G.nodes[node].get("elevation", 200.0)), 1),
            }
        })

    return {
        "location": "Knowledge Park 3, Greater Noida",
        "roads": roads,
        "points": points,
        "timeline": timeline,
        "type": "FeatureCollection",
        "features": features,
        "summary": {
            "total_nodes": num_nodes,
            "max_flood_depth": round(float(np.max(depths)), 2),
            "flooded_nodes": int(np.sum(max_depths > 0.15)),
            "critical_nodes": int(np.sum(max_depths > 0.50)),
        }
    }

# ── 3. GEOJSON ASSETS ──
def _sanitize_geojson(path: str) -> dict:
    """Load a GeoJSON file and replace NaN/Inf values with safe defaults."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # Replace bare NaN/Infinity tokens (Python float repr) with JSON null
    raw = re.sub(r'\bNaN\b', 'null', raw)
    raw = re.sub(r'\bInfinity\b', 'null', raw)
    raw = re.sub(r'\b-Infinity\b', 'null', raw)
    data = json.loads(raw)
    # Walk features and sanitize property values
    for feat in data.get("features", []):
        props = feat.get("properties") or {}
        for k, v in props.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                props[k] = None
        # Ensure height is always a usable number
        h = props.get("height")
        if h is None or (isinstance(h, float) and math.isnan(h)):
            props["height"] = props.get("levels", 1) * 3.5 if props.get("levels") else 8.0
        elif isinstance(h, (int, float)) and h <= 0:
            props["height"] = 8.0
    return data

@kp3_router.get("/geojson/buildings")
async def get_kp3_buildings():
    p = os.path.join(BASE_DIR, "kp3_buildings.geojson")
    if not os.path.exists(p):
        raise HTTPException(status_code=404, detail="kp3_buildings.geojson not found")
    from fastapi.responses import JSONResponse
    return JSONResponse(content=_sanitize_geojson(p))

@kp3_router.get("/geojson/water")
async def get_kp3_water():
    p = os.path.join(BASE_DIR, "kp3_water.geojson")
    if not os.path.exists(p):
        raise HTTPException(status_code=404, detail="kp3_water.geojson not found")
    from fastapi.responses import JSONResponse
    return JSONResponse(content=_sanitize_geojson(p))

@kp3_router.get("/basemap")
async def get_kp3_basemap():
    p = os.path.join(BASE_DIR, "deckgl_basemap_kp3.json")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/json")
    raise HTTPException(status_code=404, detail="deckgl_basemap_kp3.json not found")

class NearestRouteRequest(BaseModel):
    lat: float
    lon: float
    facility_type: str
    intensity: float

def get_segment_color(avg_depth: float):
    if avg_depth > 0.15:
        return [255, 30, 50, 255]
    elif avg_depth > 0.08:
        return [255, 140, 0, 255]
    elif avg_depth > 0.04:
        return [255, 220, 0, 240]
    else:
        return [74, 222, 128, 255]

def build_kp3_route_response(path, max_depths, G_routing, facility_name=None):
    segments = []
    total_distance = 0.0
    max_depth_on_route = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_keys = G_routing[u][v]
        best_edge = min(edge_keys.values(), key=lambda d: d.get('custom_weight', float('inf')))
        seg_length = float(best_edge.get('length', 50.0))
        total_distance += seg_length

        idx_u = node_to_idx[u]
        idx_v = node_to_idx[v]
        avg_depth = (float(max_depths[idx_u]) + float(max_depths[idx_v])) / 2.0
        max_depth_on_route = max(max_depth_on_route, avg_depth)

        if 'geometry' in best_edge:
            line_coords = list(best_edge['geometry'].coords)
            start_node = (float(G.nodes[u]['x']), float(G.nodes[u]['y']))
            first_geom = (line_coords[0][0], line_coords[0][1])
            if abs(start_node[0] - first_geom[0]) + abs(start_node[1] - first_geom[1]) > 0.0001:
                line_coords = line_coords[::-1]
            coords = [[float(c[0]), float(c[1])] for c in line_coords]
        else:
            coords = [
                [float(G.nodes[u]['x']), float(G.nodes[u]['y'])],
                [float(G.nodes[v]['x']), float(G.nodes[v]['y'])]
            ]

        segments.append({
            "path": coords,
            "depth": round(avg_depth, 2),
            "color": get_segment_color(avg_depth)
        })

    if max_depth_on_route > 0.15:
        risk = "CRITICAL"
    elif max_depth_on_route > 0.08:
        risk = "HIGH"
    elif max_depth_on_route > 0.04:
        risk = "MODERATE"
    else:
        risk = "SAFE"

    full_path = []
    for i, seg in enumerate(segments):
        if i == 0:
            full_path.extend(seg["path"])
        else:
            full_path.extend(seg["path"][1:])

    distance_km = round(total_distance / 1000.0, 2)
    walk_min = round((distance_km / 4.5) * 60)
    bike_min = round((distance_km / 15.0) * 60)
    car_min = round((distance_km / 25.0) * 60)

    res = {
        "status": "success",
        "path": full_path,
        "segments": segments,
        "distance_km": distance_km,
        "max_depth": round(max_depth_on_route, 2),
        "risk_level": risk,
        "eta": {
            "walk": walk_min,
            "bike": bike_min,
            "car": car_min
        }
    }
    if facility_name:
        res["facility_name"] = facility_name
    return res

# KP3 Emergency Facilities mapping
# KP3 Emergency Facilities — strictly within Knowledge Park 2 & 3 sector boundaries
KP3_FACILITIES = [
  {"name": "Sharda Hospital & Trauma Center", "type": "hospital", "lon": 77.482249, "lat": 28.474324},
  {"name": "Knowledge Park 2 Police Chowki", "type": "police", "lon": 77.487900, "lat": 28.469500},
  {"name": "Surajpur Police Station", "type": "police", "lon": 77.489200, "lat": 28.463200},
  {"name": "KP3 Sector Fire Response Post", "type": "fire", "lon": 77.491000, "lat": 28.466800},
  {"name": "GL Bajaj Campus Shelter", "type": "shelter", "lon": 77.488571, "lat": 28.472507},
  {"name": "Sharda University Indoor Hall", "type": "shelter", "lon": 77.484500, "lat": 28.471800},
  {"name": "IIMT College Campus Shelter", "type": "shelter", "lon": 77.491141, "lat": 28.481823},
  {"name": "Amity University Shelter", "type": "shelter", "lon": 77.485255, "lat": 28.465412},
  {"name": "NIET KP3 Sports Hall", "type": "shelter", "lon": 77.490758, "lat": 28.462763},
]

# ── 4. AI SAFE ROUTING IN KP3 ──
@kp3_router.post("/route")
async def calculate_safe_route_kp3(req: RouteRequest):
    orig = ox.distance.nearest_nodes(G, req.start_lon, req.start_lat)
    dest = ox.distance.nearest_nodes(G, req.end_lon, req.end_lat)

    # Compute depths with current intensity
    envelope = torch.exp(-0.5 * ((torch.arange(T, dtype=torch.float32, device=DEVICE) - T / 2) / 2.0) ** 2)
    X_new = torch.zeros((1, num_nodes, T, 6), device=DEVICE)
    for t in range(T):
        X_new[0, :, t, 0] = static_elev
        X_new[0, :, t, 1] = req.intensity * envelope[t]
        X_new[0, :, t, 2] = (req.intensity * envelope[:t+1].sum()) / 12.0
        X_new[0, :, t, 3] = t / float(T)
        X_new[0, :, t, 4] = static_runoff
        X_new[0, :, t, 5] = static_flow_acc

    with torch.no_grad():
        out = model(X_new, b_edge)
    max_depths = out[0].max(dim=1).values.cpu().numpy()

    # Dynamic graph edge weighting
    G_route = G.copy()
    for u, v, k, data in G_route.edges(data=True, keys=True):
        idx_u = node_to_idx[u]
        idx_v = node_to_idx[v]
        d_u = max_depths[idx_u]
        d_v = max_depths[idx_v]
        avg_d = (d_u + d_v) / 2.0
        length = data.get("length", 50.0)

        if avg_d > 30.0: # > 30 cm is impassable
            data["custom_weight"] = 1e9
        else:
            data["custom_weight"] = length * (1.0 + (avg_d / 5.0))

    try:
        path = nx.shortest_path(G_route, source=orig, target=dest, weight="custom_weight")
        return build_kp3_route_response(path, max_depths, G_route)
    except Exception as e:
        return {"status": "error", "message": f"No safe path available: {str(e)}"}

@kp3_router.post("/route/nearest")
async def find_nearest_facility_kp3(req: NearestRouteRequest):
    candidates = [f for f in KP3_FACILITIES if f["type"] == req.facility_type]
    if not candidates:
        return {"status": "error", "message": f"No facilities found of type '{req.facility_type}'"}

    orig = ox.distance.nearest_nodes(G, req.lon, req.lat)

    # Compute depths with current intensity
    envelope = torch.exp(-0.5 * ((torch.arange(T, dtype=torch.float32, device=DEVICE) - T / 2) / 2.0) ** 2)
    X_new = torch.zeros((1, num_nodes, T, 6), device=DEVICE)
    for t in range(T):
        X_new[0, :, t, 0] = static_elev
        X_new[0, :, t, 1] = req.intensity * envelope[t]
        X_new[0, :, t, 2] = (req.intensity * envelope[:t+1].sum()) / 12.0
        X_new[0, :, t, 3] = t / float(T)
        X_new[0, :, t, 4] = static_runoff
        X_new[0, :, t, 5] = static_flow_acc

    with torch.no_grad():
        out = model(X_new, b_edge)
    max_depths = out[0].max(dim=1).values.cpu().numpy()

    G_route = G.copy()
    for u, v, k, data in G_route.edges(data=True, keys=True):
        idx_u = node_to_idx[u]
        idx_v = node_to_idx[v]
        d_u = max_depths[idx_u]
        d_v = max_depths[idx_v]
        avg_d = (d_u + d_v) / 2.0
        length = data.get("length", 50.0)

        if avg_d > 30.0:
            data["custom_weight"] = 1e9
        else:
            data["custom_weight"] = length * (1.0 + (avg_d / 5.0))

    best_path = None
    best_dist = float("inf")
    best_fac = None

    for fac in candidates:
        dest = ox.distance.nearest_nodes(G, fac["lon"], fac["lat"])
        try:
            p = nx.shortest_path(G_route, source=orig, target=dest, weight="custom_weight")
            d = nx.path_weight(G_route, p, weight="custom_weight")
            if d < best_dist:
                best_dist = d
                best_path = p
                best_fac = fac
        except Exception:
            continue

    if not best_path:
        return {"status": "error", "message": f"No safe path to any {req.facility_type}"}

    return build_kp3_route_response(best_path, max_depths, G_route, facility_name=best_fac["name"])

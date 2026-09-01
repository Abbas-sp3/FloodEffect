"""
Fix KP3 buildings GeoJSON (NaN heights) and fetch real infrastructure
from Overpass API for Knowledge Park 3, Greater Noida.
"""
import json, math, re, os, urllib.request, urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── 1. Fix buildings heights ───────────────────────────────────────────────
print("[1/2] Fixing kp3_buildings.geojson heights...")
bldg_path = os.path.join(BASE_DIR, "kp3_buildings.geojson")
with open(bldg_path, "r", encoding="utf-8") as f:
    raw = f.read()

# Replace Python NaN/Infinity tokens
raw = re.sub(r'\bNaN\b', 'null', raw)
raw = re.sub(r'\bInfinity\b', 'null', raw)
raw = re.sub(r'\b-Infinity\b', 'null', raw)
data = json.loads(raw)

fixed = 0
for feat in data.get("features", []):
    props = feat.get("properties") or {}
    # Fix height
    h = props.get("height")
    lvl = props.get("levels")
    if h is None or (isinstance(h, float) and math.isnan(h)):
        if lvl and not (isinstance(lvl, float) and math.isnan(lvl)):
            props["height"] = float(lvl) * 3.5
        else:
            props["height"] = 9.0   # default single storey
        fixed += 1
    elif isinstance(h, (int, float)) and h <= 0:
        props["height"] = 9.0
        fixed += 1

    # Clean name
    nm = props.get("name", "")
    if nm == "nan" or nm is None:
        props["name"] = ""

    # Fix levels
    lv = props.get("levels")
    if lv is None or (isinstance(lv, float) and math.isnan(lv)):
        props["levels"] = None

print(f"   Fixed {fixed} buildings with missing heights.")
with open(bldg_path, "w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))
print("   Saved kp3_buildings.geojson")

# ─── 2. Fetch real infrastructure from Overpass API ─────────────────────────
print("[2/2] Fetching real infrastructure from Overpass API...")

# KP3 / Greater Noida bbox (south, west, north, east)
BBOX = "28.455,77.475,28.495,77.525"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

QUERIES = {
    "hospital": f"""
[out:json][timeout:30];
(
  node["amenity"="hospital"]({BBOX});
  way["amenity"="hospital"]({BBOX});
  node["amenity"="clinic"]({BBOX});
  way["amenity"="clinic"]({BBOX});
  node["healthcare"="hospital"]({BBOX});
  way["healthcare"="hospital"]({BBOX});
);
out center;
""",
    "police": f"""
[out:json][timeout:30];
(
  node["amenity"="police"]({BBOX});
  way["amenity"="police"]({BBOX});
);
out center;
""",
    "fire": f"""
[out:json][timeout:30];
(
  node["amenity"="fire_station"]({BBOX});
  way["amenity"="fire_station"]({BBOX});
);
out center;
""",
    "shelter": f"""
[out:json][timeout:30];
(
  node["amenity"="shelter"]({BBOX});
  way["amenity"="shelter"]({BBOX});
  node["emergency"="assembly_point"]({BBOX});
  node["amenity"="community_centre"]({BBOX});
  way["amenity"="community_centre"]({BBOX});
);
out center;
""",
}

infra = []

def query_overpass(q):
    data_enc = urllib.parse.urlencode({"data": q}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL, data=data_enc,
        headers={"User-Agent": "EvacX-KP3/1.0", "Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

for typ, query in QUERIES.items():
    try:
        result = query_overpass(query)
        elements = result.get("elements", [])
        print(f"   {typ}: found {len(elements)} elements")
        for el in elements:
            # Get coordinates
            if el["type"] == "node":
                lat, lon = el["lat"], el["lon"]
            elif el["type"] == "way" and "center" in el:
                lat, lon = el["center"]["lat"], el["center"]["lon"]
            else:
                continue

            name = el.get("tags", {}).get("name", "")
            if not name:
                name = el.get("tags", {}).get("name:en", "")
            if not name:
                name = f"Unnamed {typ.title()}"

            infra.append({
                "name": name,
                "type": typ,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "osm_id": el["id"],
            })
    except Exception as e:
        print(f"   WARNING: {typ} query failed: {e}")

print(f"\n   Total real infrastructure found: {len(infra)}")
for item in infra:
    print(f"     [{item['type']}] {item['name']} ({item['lat']}, {item['lon']})")

# Save
out_path = os.path.join(BASE_DIR, "kp3_infra.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(infra, f, indent=2, ensure_ascii=False)
print(f"\n   Saved to kp3_infra.json")
print("\n[Done] All KP3 data fixed and ready.")

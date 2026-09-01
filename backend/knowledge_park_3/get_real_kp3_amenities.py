import urllib.request
import urllib.parse
import json

query = """
[out:json][timeout:25];
(
  node["amenity"](28.455,77.480,28.485,77.518);
  way["amenity"](28.455,77.480,28.485,77.518);
  node["emergency"](28.455,77.480,28.485,77.518);
  node["healthcare"](28.455,77.480,28.485,77.518);
  node["building"](28.455,77.480,28.485,77.518);
  way["building"](28.455,77.480,28.485,77.518);
);
out center;
"""

req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=urllib.parse.urlencode({'data': query}).encode('utf-8'),
    headers={'User-Agent': 'EvacX/1.0'}
)

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode('utf-8'))

    elements = data.get('elements', [])
    print(f'Total OSM elements in KP3 bbox: {len(elements)}')

    named_facilities = []
    for el in elements:
        tags = el.get('tags', {})
        name = tags.get('name', tags.get('name:en', ''))
        amenity = tags.get('amenity', tags.get('healthcare', tags.get('emergency', tags.get('building', ''))))
        lat = el.get('lat') or (el.get('center', {}).get('lat'))
        lon = el.get('lon') or (el.get('center', {}).get('lon'))
        if name and lat and lon:
            named_facilities.append({
                'name': name,
                'amenity': amenity,
                'lat': lat,
                'lon': lon,
                'tags': tags
            })
            print(f'[{amenity}] {name} -> lat={lat:.6f}, lon={lon:.6f}')

    with open('knowledge_park_3/osm_kp3_real_facilities.json', 'w', encoding='utf-8') as f:
        json.dump(named_facilities, f, indent=2)
except Exception as e:
    print('Error:', e)

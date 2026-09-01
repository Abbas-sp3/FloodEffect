import osmnx as ox

g = ox.load_graphml('knowledge_park_3/kp3_focused.graphml')

facilities = [
    {'name': 'Sharda Hospital & Trauma Center', 'type': 'hospital', 'lon': 77.482249, 'lat': 28.474324},
    {'name': 'Kailash Hospital Greater Noida', 'type': 'hospital', 'lon': 77.505000, 'lat': 28.470884},
    {'name': 'Knowledge Park Police Station', 'type': 'police', 'lon': 77.498500, 'lat': 28.468500},
    {'name': 'Pari Chowk Traffic Police Post', 'type': 'police', 'lon': 77.508200, 'lat': 28.464000},
    {'name': 'Kasna Fire Station Response Post', 'type': 'fire', 'lon': 77.506500, 'lat': 28.465500},
    {'name': 'India Expo Mart Relief Shelter', 'type': 'shelter', 'lon': 77.498342, 'lat': 28.461727},
    {'name': 'GL Bajaj Campus Shelter', 'type': 'shelter', 'lon': 77.488571, 'lat': 28.472507},
    {'name': 'IIMT College Campus Shelter', 'type': 'shelter', 'lon': 77.491141, 'lat': 28.481823},
    {'name': 'HIMT Institute Shelter', 'type': 'shelter', 'lon': 77.499955, 'lat': 28.471728},
    {'name': 'Cambridge School Relief Center', 'type': 'shelter', 'lon': 77.499590, 'lat': 28.478192},
]

print("=== VERIFYING GRAPH SNAPPING ===")
for f in facilities:
    n, dist = ox.distance.nearest_nodes(g, f['lon'], f['lat'], return_dist=True)
    nx_lon = g.nodes[n]['x']
    nx_lat = g.nodes[n]['y']
    print(f"[{f['type'].upper()}] {f['name']}:")
    print(f"  Exact: ({f['lat']:.6f}, {f['lon']:.6f}) -> Nearest Node Dist: {dist:.1f}m -> Graph: ({nx_lat:.6f}, {nx_lon:.6f})")

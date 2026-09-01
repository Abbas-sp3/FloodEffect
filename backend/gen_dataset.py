import os, sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import osmnx as ox
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPHML  = os.path.join(BASE_DIR, "kc_valley_focused.graphml")
OUT_FILE = os.path.join(BASE_DIR, "val_dataset.pt")
T = 12

print("Loading graph...")
G = ox.load_graphml(GRAPHML)
nodes = list(G.nodes())
N = len(nodes)
print(f"Graph has {N} nodes")

print("Building edge_index...")
node_to_idx = {n: i for i, n in enumerate(nodes)}
src, dst = [], []
for u, v in G.edges():
    if u in node_to_idx and v in node_to_idx:
        src.append(node_to_idx[u])
        dst.append(node_to_idx[v])
edge_index = torch.tensor([src, dst], dtype=torch.long)
print(f"edge_index shape: {edge_index.shape}")

print("Extracting node features...")
cLat, cLon = 12.9357, 77.6717
elev = np.array(
    [900.0 + (G.nodes[n]["y"] - cLat)*350.0 + (G.nodes[n]["x"] - cLon)*250.0 for n in nodes],
    dtype=np.float32
)
runoff = np.full(N, 0.65, dtype=np.float32)
for u, v, k, data in G.edges(keys=True, data=True):
    hw = data.get("highway", "residential")
    if isinstance(hw, list): hw = hw[0]
    coeff = 0.90 if hw in ["primary","motorway","trunk","secondary"] else 0.65
    if u in node_to_idx: runoff[node_to_idx[u]] = coeff
    if v in node_to_idx: runoff[node_to_idx[v]] = coeff

degrees = np.array([G.degree(n) for n in nodes], dtype=np.float32)
flow_acc = (degrees - degrees.min()) / (degrees.max() - degrees.min() + 1e-8)
elev_n   = (elev - elev.min()) / (elev.max() - elev.min() + 1e-8)

print("Building X tensor...")
intensity = 0.3
X = torch.zeros((1, N, T, 6), dtype=torch.float32)
envelope = torch.exp(-0.5 * ((torch.arange(T, dtype=torch.float32) - T/2) / 2.0)**2)
e_t = torch.tensor(elev_n,  dtype=torch.float32)
r_t = torch.tensor(runoff,  dtype=torch.float32)
f_t = torch.tensor(flow_acc,dtype=torch.float32)
for t in range(T):
    X[0, :, t, 0] = e_t
    X[0, :, t, 1] = intensity * envelope[t]
    X[0, :, t, 2] = (intensity * envelope[:t+1].sum()) / 12.0
    X[0, :, t, 3] = t / float(T)
    X[0, :, t, 4] = r_t
    X[0, :, t, 5] = f_t

y = torch.zeros((1, N, T), dtype=torch.float32)
dataset = {"X": X, "y": y, "edge_index": edge_index, "y_mean": 0.0, "y_std": 1.0}
torch.save(dataset, OUT_FILE)
print(f"Saved val_dataset.pt  X={tuple(X.shape)}  edge_index={tuple(edge_index.shape)}")

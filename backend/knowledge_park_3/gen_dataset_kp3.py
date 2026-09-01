"""
Knowledge Park 3 (Greater Noida) — Dataset Generation Script.
Generates spatio-temporal graph tensors (X, y, edge_index) from the KP3 road network.
"""
import os
import sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import torch
import osmnx as ox
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPHML = os.path.join(BASE_DIR, "kp3_focused.graphml")
VAL_OUT = os.path.join(BASE_DIR, "val_dataset_kp3.pt")
TRAIN_OUT = os.path.join(BASE_DIR, "train_dataset_kp3.pt")
T = 12

def generate():
    print("=" * 60)
    print("STEP 2 — Generating KP3 Spatio-Temporal Dataset")
    print("=" * 60)
    
    if not os.path.exists(GRAPHML):
        print(f"ERROR: {GRAPHML} not found! Run extract_kp3.py first.")
        return

    print("Loading Knowledge Park 3 graph...")
    G = ox.load_graphml(GRAPHML)
    nodes = list(G.nodes())
    N = len(nodes)
    print(f"Graph has {N} nodes, {len(G.edges)} edges")

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
    cLat, cLon = 28.4728, 77.4985
    elev = np.array([
        float(G.nodes[n].get("elevation", 200.0 + (G.nodes[n]["y"] - cLat)*120.0 - (G.nodes[n]["x"] - cLon)*90.0))
        for n in nodes
    ], dtype=np.float32)

    runoff = np.full(N, 0.70, dtype=np.float32)
    for u, v, k, data in G.edges(keys=True, data=True):
        hw = data.get("highway", "residential")
        if isinstance(hw, list):
            hw = hw[0]
        coeff = 0.92 if hw in ["primary", "motorway", "trunk", "secondary"] else 0.70
        if u in node_to_idx:
            runoff[node_to_idx[u]] = coeff
        if v in node_to_idx:
            runoff[node_to_idx[v]] = coeff

    degrees = np.array([G.degree(n) for n in nodes], dtype=np.float32)
    flow_acc = (degrees - degrees.min()) / (degrees.max() - degrees.min() + 1e-8)
    elev_n = (elev - elev.min()) / (elev.max() - elev.min() + 1e-8)

    print("Building Spatio-Temporal feature tensor X across multiple storm scenarios...")
    
    # Generate multiple storm scenarios (intensities 0.1 to 1.0) for rich training
    intensities = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    num_samples = len(intensities)
    
    X_all = torch.zeros((num_samples, N, T, 6), dtype=torch.float32)
    y_all = torch.zeros((num_samples, N, T), dtype=torch.float32)
    
    envelope = torch.exp(-0.5 * ((torch.arange(T, dtype=torch.float32) - T/2) / 2.0)**2)
    e_t = torch.tensor(elev_n, dtype=torch.float32)
    r_t = torch.tensor(runoff, dtype=torch.float32)
    f_t = torch.tensor(flow_acc, dtype=torch.float32)

    for idx, intensity in enumerate(intensities):
        for t in range(T):
            rain_inst = intensity * envelope[t]
            rain_cum = (intensity * envelope[:t+1].sum()) / 12.0
            
            X_all[idx, :, t, 0] = e_t
            X_all[idx, :, t, 1] = rain_inst
            X_all[idx, :, t, 2] = rain_cum
            X_all[idx, :, t, 3] = t / float(T)
            X_all[idx, :, t, 4] = r_t
            X_all[idx, :, t, 5] = f_t
            
            # Realistic drainage physics:
            # Water drains from high to low ground. Only true low-lying depressions (elev_n < 0.45)
            # and major runoff convergence junctions accumulate standing water.
            # Base wetness on standard roads is minimal (< 1.5 cm).
            drainage_mask = (elev_n < 0.40).astype(np.float32)
            depression_depth = np.maximum(0.0, 0.40 - elev_n) * 3.5  # deeper in true lowest basins
            channel_acc = (f_t.numpy() ** 2) * 1.8 * r_t.numpy()
            
            # Flood depth in centimeters (matching Bangalore cm target scale)
            # Baseline road splash: 0.1 to 1.5 cm
            # Low-lying flood corridors: 10 cm to 60 cm
            node_ponding_cm = (
                rain_cum * (0.8 + 2.2 * channel_acc) +
                (rain_cum ** 1.3) * (depression_depth * 45.0 + channel_acc * 30.0) * drainage_mask
            )
            
            y_all[idx, :, t] = torch.clamp(torch.tensor(node_ponding_cm, dtype=torch.float32), min=0.0, max=65.0)

    # Save validation dataset (first scenario)
    val_dataset = {
        "X": X_all[2:3], # 0.3 intensity sample
        "y": y_all[2:3],
        "edge_index": edge_index,
        "y_mean": float(y_all.mean()),
        "y_std": float(y_all.std())
    }
    torch.save(val_dataset, VAL_OUT)

    # Save full training dataset
    train_dataset = {
        "X": X_all,
        "y": y_all,
        "edge_index": edge_index,
        "y_mean": float(y_all.mean()),
        "y_std": float(y_all.std())
    }
    torch.save(train_dataset, TRAIN_OUT)
    
    print(f"Saved: {VAL_OUT}  X={tuple(val_dataset['X'].shape)}")
    print(f"Saved: {TRAIN_OUT}  X={tuple(train_dataset['X'].shape)}")
    print("DONE! Feature dataset generated.")

if __name__ == "__main__":
    generate()

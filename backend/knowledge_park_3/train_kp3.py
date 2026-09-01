"""
Knowledge Park 3 (Greater Noida) — STGCN Model Training Script.
Trains the Spatio-Temporal Graph Convolutional Neural Network on KP3's road graph.
"""
import os
import sys
import time

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torch_geometric.nn as geom_nn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_SIZE = 4
EPOCHS = 60
LEARNING_RATE = 0.002
HIDDEN_DIM = 64
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class FloodDataset(Dataset):
    def __init__(self, pt_path):
        data = torch.load(pt_path, map_location="cpu", weights_only=False)
        self.X = data["X"]
        self.y = data["y"]
        self.edge_index = data["edge_index"]
        self.y_mean = data.get("y_mean", 0.0)
        self.y_std = data.get("y_std", 1.0)

    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def get_batched_edge_index(edge_index, num_nodes, batch_size, device):
    E = edge_index.shape[1]
    b_edge = edge_index.repeat(1, batch_size).to(device)
    offsets = torch.arange(batch_size, device=device).repeat_interleave(E) * num_nodes
    return b_edge + offsets.unsqueeze(0)

class STGCN_Cell(nn.Module):
    def __init__(self, in_dim, hidden_dim):
        super().__init__()
        self.gcn = geom_nn.GCNConv(in_dim, hidden_dim)
        self.gru = nn.GRUCell(hidden_dim, hidden_dim)

    def forward(self, x, edge_index, h):
        gcn_out = torch.relu(self.gcn(x, edge_index))
        h_new = self.gru(gcn_out, h)
        return h_new

class FloodSurrogateModel(nn.Module):
    def __init__(self, num_nodes, num_features=6, hidden_dim=HIDDEN_DIM):
        super().__init__()
        self.num_nodes = num_nodes
        self.hidden_dim = hidden_dim

        self.feat_proj = nn.Linear(num_features, 32)
        self.stgcn = STGCN_Cell(32, hidden_dim)
        self.out_proj = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Softplus()
        )

    def forward(self, X, edge_index):
        B, N, T, F = X.shape
        X_flat = X.view(B * N, T, F)
        h = torch.zeros(B * N, self.hidden_dim, device=X.device)
        predictions = []

        for t in range(T):
            x_t = self.feat_proj(X_flat[:, t, :])
            h = self.stgcn(x_t, edge_index, h)
            pred_t = self.out_proj(h)
            predictions.append(pred_t)

        out = torch.stack(predictions, dim=1) # [B*N, T, 1]
        out = out.view(B, N, T)
        return out

def train():
    print("=" * 60)
    print(f"STEP 3 — Training STGCN Model for Knowledge Park 3 ({DEVICE})")
    print("=" * 60)

    train_path = os.path.join(BASE_DIR, "train_dataset_kp3.pt")
    val_path = os.path.join(BASE_DIR, "val_dataset_kp3.pt")

    if not os.path.exists(train_path):
        print(f"ERROR: {train_path} not found! Run gen_dataset_kp3.py first.")
        return

    train_ds = FloodDataset(train_path)
    val_ds = FloodDataset(val_path)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=1, shuffle=False)

    num_nodes = train_ds.X.shape[1]
    base_edge_index = train_ds.edge_index
    print(f"Nodes: {num_nodes:,} | Training Samples: {len(train_ds)}")

    model = FloodSurrogateModel(num_nodes=num_nodes).to(DEVICE)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    weights_path = os.path.join(BASE_DIR, "stgcn_weights_kp3.pth")
    checkpoint_path = os.path.join(BASE_DIR, "stgcn_checkpoint_kp3.pth")

    start_time = time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0

        for batch_X, batch_y in train_loader:
            B = batch_X.shape[0]
            batch_X = batch_X.to(DEVICE)
            batch_y = batch_y.to(DEVICE)

            batched_edges = get_batched_edge_index(base_edge_index, num_nodes, B, DEVICE)

            optimizer.zero_grad()
            pred = model(batch_X, batched_edges)
            loss = criterion(pred, batch_y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item() * B

        avg_train_loss = total_loss / len(train_ds)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for val_X, val_y in val_loader:
                val_X = val_X.to(DEVICE)
                val_y = val_y.to(DEVICE)
                val_edges = base_edge_index.to(DEVICE)
                v_pred = model(val_X, val_edges)
                val_loss += criterion(v_pred, val_y).item()

        if epoch % 10 == 0 or epoch == 1 or epoch == EPOCHS:
            print(f"Epoch {epoch:3d}/{EPOCHS} | Train MSE: {avg_train_loss:.5f} | Val MSE: {val_loss:.5f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), weights_path)
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "num_nodes": num_nodes,
            }, checkpoint_path)

    elapsed = time.time() - start_time
    print(f"\n[OK] Training Complete in {elapsed:.2f}s! Best Val MSE: {best_val_loss:.5f}")
    print(f"     Saved Weights: {weights_path}")
    print(f"     Saved Checkpoint: {checkpoint_path}")

if __name__ == "__main__":
    train()

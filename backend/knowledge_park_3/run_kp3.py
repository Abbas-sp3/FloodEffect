"""
Standalone server for EvacX — Knowledge Park 3, Greater Noida.
Run with: python run_kp3.py
Runs on port 8001 (or configurable via KP3_PORT).
"""
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from api_kp3 import kp3_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title="EvacX — Knowledge Park 3, Greater Noida",
    description="Dedicated STGCN Digital Twin & Flood AI Engine for Knowledge Park 3, Greater Noida.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kp3_router, prefix="/kp3")
app.include_router(kp3_router, prefix="")

@app.get("/")
async def root():
    viewer = os.path.join(BASE_DIR, "kp3_viewer.html")
    if os.path.exists(viewer):
        with open(viewer, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {
        "city": "Greater Noida",
        "zone": "Knowledge Park 3 & Pari Chowk",
        "service": "EvacX Knowledge Park 3 Digital Twin API",
        "endpoints": {
            "simulate": "/kp3/simulate",
            "safe_route": "/kp3/route",
            "weather": "/kp3/weather",
            "3d_buildings": "/kp3/geojson/buildings",
            "water": "/kp3/geojson/water",
            "basemap": "/kp3/basemap"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "location": "Knowledge Park 3, Greater Noida", "stgcn": "active"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("KP3_PORT", "8001"))
    print(f"\n[EvacX KP3] Starting dedicated Knowledge Park 3 server on http://localhost:{port}")
    uvicorn.run("run_kp3:app", host="0.0.0.0", port=port, reload=False)

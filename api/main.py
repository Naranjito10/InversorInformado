from __future__ import annotations
import sys
from pathlib import Path

# Asegurar que la raíz del proyecto está en el path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import listings, scraper, export, zones, monitor

app = FastAPI(title="InversorInformado API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings.router)
app.include_router(scraper.router)
app.include_router(export.router)
app.include_router(zones.router)
app.include_router(monitor.router)


@app.get("/health")
def health():
    return {"status": "ok"}
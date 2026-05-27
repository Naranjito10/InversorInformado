from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from api.auth import get_current_user
from api.routers import listings, scraper, export, zones, monitor, auth, fuentes, telegram

app = FastAPI(title="InversorInformado API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

_protected = {"dependencies": [Depends(get_current_user)]}
app.include_router(listings.router, **_protected)
app.include_router(scraper.router, **_protected)
app.include_router(export.router, **_protected)
app.include_router(zones.router, **_protected)
app.include_router(monitor.router, **_protected)
app.include_router(fuentes.router, **_protected)
app.include_router(telegram.router, **_protected)



@app.get("/health")
def health():
    return {"status": "ok"}

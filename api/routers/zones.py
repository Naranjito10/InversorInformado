from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter
from api.schemas import ZoneOut

router = APIRouter(prefix="/api/zones", tags=["zones"])

ZONES_FILE = Path(__file__).parent.parent.parent / "config" / "zones.json"


@lru_cache(maxsize=1)
def _load_zones() -> dict:
    return json.loads(ZONES_FILE.read_text(encoding="utf-8"))["zones"]


@router.get("", response_model=list[ZoneOut])
def get_zones():
    zones = _load_zones()
    result = []
    for key, zone in zones.items():
        disponibles = [p for p, url in zone["portals"].items() if url]
        result.append(ZoneOut(
            key=key,
            label=zone["label"],
            portales_disponibles=disponibles,
        ))
    return sorted(result, key=lambda z: z.label)
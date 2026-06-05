from __future__ import annotations

from fastapi import APIRouter

from api.schemas import ZoneOut
from api.services.scraper_service import load_zones

router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.get("", response_model=list[ZoneOut])
def get_zones():
    zones = load_zones()
    result = []
    for key, zone in zones.items():
        disponibles = [p for p, url in zone["portals"].items() if url]
        result.append(ZoneOut(
            key=key,
            label=zone["label"],
            portales_disponibles=disponibles,
        ))
    return sorted(result, key=lambda z: z.label)

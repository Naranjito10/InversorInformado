from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

ZONES_FILE = Path(__file__).parent.parent.parent / "config" / "zones.json"


@lru_cache(maxsize=1)
def load_zones() -> dict:
    return json.loads(ZONES_FILE.read_text(encoding="utf-8"))["zones"]


def get_zones_list() -> list[dict]:
    zones = load_zones()
    result = []
    for key, zone in zones.items():
        disponibles = [p for p, url in zone["portals"].items() if url]
        result.append({"key": key, "label": zone["label"], "portales_disponibles": disponibles})
    return sorted(result, key=lambda z: z["label"])


def build_search_targets(
    zona_label: str,
    portales: list[str],
    precio_min: Optional[int],
    precio_max: Optional[int],
    max_pages: int,
) -> list[dict]:
    zones = load_zones()
    zone_key = next(
        (k for k, z in zones.items() if z["label"].strip().lower() == zona_label.strip().lower()),
        None,
    )
    if not zone_key:
        return []

    zone = zones[zone_key]
    targets = []
    for portal in portales:
        base_url = zone["portals"].get(portal)
        if not base_url:
            continue
        url = _build_url(portal, base_url, precio_min, precio_max)
        targets.append({
            "source": portal,
            "name": f"{zone['label']} - {portal.capitalize()}",
            "url": url,
            "max_pages": max_pages,
            "max_results": 100,
            "filters": {k: v for k, v in {"price_min": precio_min, "price_max": precio_max}.items() if v is not None},
        })
    return targets


def _build_url(portal: str, base: str, price_min: Optional[int], price_max: Optional[int]) -> str:
    if portal == "idealista":
        url = base.rstrip("/")
        if price_min and price_max:
            url += f"/con-precio-hasta_{price_max},precio-desde_{price_min}"
        elif price_max:
            url += f"/con-precio-hasta_{price_max}"
        elif price_min:
            url += f"/precio-desde_{price_min}"
        return url + "/?ordenado-por=fecha-publicacion-desc"
    if portal == "fotocasa":
        params: dict = {"sortType": "publishingDate", "sortOrderDesc": "true"}
        if price_min:
            params["priceMin"] = str(price_min)
        if price_max:
            params["priceMax"] = str(price_max)
        sep = "&" if "?" in base else "?"
        return base + sep + urlencode(params)
    if portal == "pisos":
        url = base.rstrip("/")
        if "fecharecientedesde" not in url:
            url += "/fecharecientedesde-desc"
        return url + "/"
    if portal == "casaradar":
        url = base.rstrip("/")
        params: dict = {}
        if price_min:
            params["precio_min"] = str(price_min)
        if price_max:
            params["precio_max"] = str(price_max)
        if params:
            sep = "&" if "?" in url else "?"
            return url + sep + urlencode(params)
        return url + "/"
    return base


def run_cycle_background() -> None:
    from scraper.runner import run_cycle
    run_cycle()


def run_targets_background(targets: list[dict]) -> None:
    from scraper.runner import run_targets
    run_targets(targets)
"""Build portal search URLs with price and sort filters from zones.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from .tally_parser import ScrapeRequest

ROOT = Path(__file__).parent.parent
ZONES_FILE = ROOT / "config" / "zones.json"


def load_zones() -> dict:
    return json.loads(ZONES_FILE.read_text(encoding="utf-8"))["zones"]


def _label_to_key(zones: dict, zone_label: str) -> Optional[str]:
    """Case-insensitive label → zone_key lookup."""
    target = zone_label.strip().lower()
    for key, zone in zones.items():
        if zone["label"].strip().lower() == target:
            return key
    return None


def _build_idealista_url(base: str, price_min: Optional[int], price_max: Optional[int]) -> str:
    """Inject price segment and sort param into an Idealista URL.

    Input:  https://www.idealista.com/venta-viviendas/{zone}/
    Output: https://www.idealista.com/venta-viviendas/{zone}/con-precio-hasta_N,precio-desde_N/?ordenado-por=fecha-publicacion-desc
    """
    url = base.rstrip("/")
    if price_min is not None and price_max is not None:
        url += f"/con-precio-hasta_{price_max},precio-desde_{price_min}"
    elif price_max is not None:
        url += f"/con-precio-hasta_{price_max}"
    elif price_min is not None:
        url += f"/precio-desde_{price_min}"
    url += "/?ordenado-por=fecha-publicacion-desc"
    return url


def _build_fotocasa_url(base: str, price_min: Optional[int], price_max: Optional[int]) -> str:
    """Append price and sort query params to a Fotocasa URL.

    Input:  https://www.fotocasa.es/es/comprar/viviendas/{zone}/l
    Output: https://www.fotocasa.es/...?priceMin=N&priceMax=N&sortType=publishingDate&sortOrderDesc=true
    """
    params: dict = {"sortType": "publishingDate", "sortOrderDesc": "true"}
    if price_min is not None:
        params["priceMin"] = str(price_min)
    if price_max is not None:
        params["priceMax"] = str(price_max)
    sep = "&" if "?" in base else "?"
    return base + sep + urlencode(params)


def _build_pisos_url(base: str) -> str:
    """Add sort segment to a pisos.com URL (price filtering is post-scraping only).

    Input:  https://www.pisos.com/venta/pisos-{slug}/
    Output: https://www.pisos.com/venta/pisos-{slug}/fecharecientedesde-desc/
    """
    url = base.rstrip("/")
    if "fecharecientedesde" not in url:
        url += "/fecharecientedesde-desc"
    return url + "/"


def build_targets(req: ScrapeRequest, zones: dict) -> list[dict]:
    """Produce a list of search_targets dicts ready for runner.run_targets()."""
    zone_key = _label_to_key(zones, req.zone_label)
    if zone_key is None:
        return []

    zone = zones[zone_key]
    zone_label = zone["label"]
    portals_map: dict = zone["portals"]

    targets = []
    for portal in req.portals:
        base_url: Optional[str] = portals_map.get(portal)
        if not base_url:
            continue  # portal not available for this zone

        if portal == "idealista":
            url = _build_idealista_url(base_url, req.price_min, req.price_max)
        elif portal == "fotocasa":
            url = _build_fotocasa_url(base_url, req.price_min, req.price_max)
        elif portal == "pisos":
            url = _build_pisos_url(base_url)
        else:
            url = base_url  # habitaclia: no URL-level filters

        targets.append({
            "source": portal,
            "name": f"{zone_label} - {portal.capitalize()} - Compra",
            "url": url,
            "max_pages": req.max_pages,
            "max_results": req.max_results,
            "filters": {
                k: v for k, v in {
                    "price_min": req.price_min,
                    "price_max": req.price_max,
                }.items() if v is not None
            },
        })

    return targets

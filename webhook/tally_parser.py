"""Parse Tally webhook payloads into structured scraping parameters."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


_PORTAL_NAME_MAP = {
    "idealista": "idealista",
    "fotocasa": "fotocasa",
    "habitaclia": "habitaclia",
    "pisos.com": "pisos",
    "pisos": "pisos",
}


@dataclass
class ScrapeRequest:
    zone_label: str
    price_min: Optional[int]
    price_max: Optional[int]
    portals: list[str]
    max_pages: int = 3
    max_results: int = 100


def _extract_checkboxes(value: Any) -> list[str]:
    """Handle both string-list and object-list checkbox values from Tally."""
    if not value:
        return []
    result = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            result.append(item.get("text") or item.get("value") or "")
    return [x for x in result if x]


def parse_tally_payload(payload: dict) -> ScrapeRequest:
    """Extract scraping parameters from a Tally FORM_RESPONSE webhook body."""
    fields: list[dict] = payload.get("data", {}).get("fields", [])

    zone_label = ""
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    portals: list[str] = []
    max_pages = 3
    max_results = 100

    for f in fields:
        label: str = f.get("label", "").strip()
        value: Any = f.get("value")

        label_lower = label.lower()

        if "zona" in label_lower:
            zone_label = str(value).strip() if value else ""

        elif "mínimo" in label_lower or "minimo" in label_lower or "min" in label_lower:
            try:
                price_min = int(float(str(value))) if value not in (None, "") else None
            except (ValueError, TypeError):
                pass

        elif "máximo" in label_lower or "maximo" in label_lower or "max" in label_lower:
            try:
                price_max = int(float(str(value))) if value not in (None, "") else None
            except (ValueError, TypeError):
                pass

        elif "página" in label_lower or "pagina" in label_lower or "page" in label_lower:
            try:
                max_pages = max(1, int(float(str(value)))) if value not in (None, "") else 3
            except (ValueError, TypeError):
                pass

        elif "portale" in label_lower or (
            "portal" in label_lower and "página" not in label_lower and "pagina" not in label_lower
        ):
            raw = _extract_checkboxes(value) if isinstance(value, list) else (
                [str(value)] if value else []
            )
            portals = [
                _PORTAL_NAME_MAP[name.lower()]
                for name in raw
                if name.lower() in _PORTAL_NAME_MAP
            ]

        elif "resultado" in label_lower or "result" in label_lower:
            try:
                max_results = max(1, int(float(str(value)))) if value not in (None, "") else 100
            except (ValueError, TypeError):
                pass

    _default_portals = ["idealista", "fotocasa", "habitaclia", "pisos"]
    return ScrapeRequest(
        zone_label=zone_label,
        price_min=price_min,
        price_max=price_max,
        portals=list(dict.fromkeys(portals)) if portals else _default_portals,
        max_pages=max_pages,
        max_results=max_results,
    )

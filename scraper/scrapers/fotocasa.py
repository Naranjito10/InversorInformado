"""Scraper para Fotocasa.es.

Fotocasa inyecta todos los datos en <script id="__initial_props__"> como JSON.
Path: data["initialSearch"]["result"]["realEstates"] (lista de inmuebles).
Features detalladas (surface/rooms/bathrooms/floor) en resultsV2.items,
indexadas por realEstateAdId.
"""
from __future__ import annotations

import json
import re
from typing import Iterator, Optional
from urllib.parse import urljoin

from .base import BaseScraper


class FotocasaScraper(BaseScraper):
    SOURCE = "fotocasa"
    USE_JS = True

    BASE = "https://www.fotocasa.es"
    _SCRIPT_RE = re.compile(
        r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>', re.DOTALL
    )

    def _extract_initial_props(self, html: str) -> Optional[dict]:
        m = self._SCRIPT_RE.search(html)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    def parse_search_page(self, html: str, base_url: str) -> Iterator[dict]:
        data = self._extract_initial_props(html)
        if not data:
            self.log.warning("fotocasa_no_initial_props")
            return

        try:
            result = data["initialSearch"]["result"]
            real_estates = result.get("realEstates") or []
            v2_items = (result.get("resultsV2") or {}).get("items") or []
        except (KeyError, TypeError):
            self.log.warning("fotocasa_unexpected_json_structure")
            return

        # Index v2 items by realEstateAdId for O(1) feature lookup
        v2_index: dict = {
            it["realEstateAdId"]: it
            for it in v2_items
            if isinstance(it, dict) and it.get("realEstateAdId")
        }

        for raw in real_estates:
            try:
                yield self._convert_item(raw, v2_index)
            except Exception as exc:  # noqa: BLE001
                self.log.warning("item_parse_error", extra={"error": str(exc)})

    def _convert_item(self, raw: dict, v2_index: dict) -> dict:
        item: dict = {}

        # URL: detail["es-ES"] is the canonical path
        detail = raw.get("detail") or {}
        path = detail.get("es-ES") or detail.get("es")
        item["url"] = urljoin(self.BASE, path) if path else None

        # Título
        item["titulo"] = raw.get("title") or raw.get("name") or raw.get("prettyName")

        # Precio
        item["precio_venta"] = raw.get("rawPrice") or raw.get("price")

        # Description is a plain string here
        item["description"] = raw.get("description") if isinstance(raw.get("description"), str) else None

        # Features from v2 (surface/rooms/bathrooms/floor)
        v2 = v2_index.get(raw.get("realEstateAdId") or "")
        feats = (v2.get("features") or {}) if v2 else {}
        item["metros_cuadrados"] = feats.get("surface")
        item["habitaciones"] = feats.get("rooms")
        item["banos"] = feats.get("bathrooms")
        item["planta"] = feats.get("floor")
        item["ascensor"] = feats.get("elevator")
        item["terraza"] = feats.get("terrace") or feats.get("balcony")
        item["garaje"] = feats.get("parking") or feats.get("garage")
        item["estado"] = feats.get("conservationState") or feats.get("state")
        item["certificado_energetico"] = (
            (feats.get("energyCertificate") or {}).get("rating")
            if isinstance(feats.get("energyCertificate"), dict)
            else feats.get("energyCertificate")
        )
        item["tipo_propiedad"] = raw.get("rawPropertySubtype") or raw.get("typology")

        # Localizacion
        addr = raw.get("address") or {}
        item["barrio"] = addr.get("neighborhood") or addr.get("district")
        item["municipio"] = (addr.get("municipality") or "").strip() or addr.get("city")
        item["provincia"] = addr.get("province")
        coords = raw.get("coordinates") or {}
        item["lat"] = coords.get("latitude")
        item["lon"] = coords.get("longitude")

        # Fallback titulo si el JSON no lo trae
        if not item.get("titulo"):
            parts = [item.get("barrio"), item.get("municipio")]
            loc = ", ".join(p for p in parts if p)
            item["titulo"] = f"Vivienda en {loc}" if loc else None

        return item

    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        # Pattern: /l  →  /l/2  →  /l/3
        m = re.search(r"/l(?:/(\d+))?/?$", current_url)
        if m:
            current_page = int(m.group(1) or 1)
            next_page = current_page + 1
            if m.group(1):
                return re.sub(r"/l/\d+/?$", f"/l/{next_page}", current_url)
            return current_url.rstrip("/") + f"/{next_page}"
        return None

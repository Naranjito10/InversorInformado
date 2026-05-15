"""Scraper para Fotocasa.es.

Fotocasa expone bastantes datos en el atributo `data-*` de las tarjetas y a
veces en JSON inline (`__NEXT_DATA__`). Intentamos primero JSON, despues HTML.
"""
from __future__ import annotations

import json
import re
from typing import Iterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper


class FotocasaScraper(BaseScraper):
    SOURCE = "fotocasa"
    USE_JS = True

    BASE = "https://www.fotocasa.es"

    def _extract_next_data(self, html: str) -> Optional[dict]:
        """Fotocasa usa Next.js: hay un <script id=__NEXT_DATA__> con todo."""
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return None
        try:
            return json.loads(script.string)
        except Exception:
            return None

    def _walk_for_realestates(self, data: dict) -> Iterator[dict]:
        """Encuentra recursivamente lista de inmuebles en el JSON."""
        if not isinstance(data, dict):
            return
        # Patrones conocidos: data.props.pageProps.initialSearch.result.realEstates
        candidates = []
        try:
            candidates.append(
                data["props"]["pageProps"]["initialSearch"]["result"]["realEstates"]
            )
        except (KeyError, TypeError):
            pass
        try:
            candidates.append(
                data["props"]["pageProps"]["initialProps"]["data"]["realEstates"]
            )
        except (KeyError, TypeError):
            pass

        for lst in candidates:
            if isinstance(lst, list):
                yield from lst
                return

        # Fallback: busqueda recursiva por clave 'realEstates'
        stack = [data]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, val in current.items():
                    if key == "realEstates" and isinstance(val, list):
                        yield from val
                        return
                    stack.append(val)
            elif isinstance(current, list):
                stack.extend(current)

    def parse_search_page(self, html: str, base_url: str) -> Iterator[dict]:
        data = self._extract_next_data(html)
        items_from_json = list(self._walk_for_realestates(data)) if data else []

        if items_from_json:
            for it in items_from_json:
                try:
                    yield self._convert_json_item(it)
                except Exception as exc:  # noqa: BLE001
                    self.log.warning("item_parse_error", extra={"error": str(exc)})
            return

        # --- Fallback HTML ---
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(
            "article.re-CardPackPremium, article.re-CardPack, "
            "article[class*='re-Card']"
        )
        for card in cards:
            try:
                item: dict = {}
                link = card.select_one("a[href*='/d']") or card.select_one("a")
                if not link:
                    continue
                item["url"] = urljoin(self.BASE, link.get("href", ""))
                item["titulo"] = link.get("title") or link.get_text(strip=True)

                price = card.select_one("[class*='Price'], [class*='price']")
                if price:
                    item["precio_venta"] = price.get_text(strip=True)

                # Features inline
                features = card.select("[class*='Features'] li, [class*='features'] li")
                for f in features:
                    txt = f.get_text(" ", strip=True).lower()
                    if "m²" in txt or "m2" in txt:
                        item["metros_cuadrados"] = txt
                    elif "hab" in txt:
                        item["habitaciones"] = txt
                    elif "baño" in txt or "bano" in txt:
                        item["banos"] = txt

                # Localizacion (suele estar en el header de la card)
                loc = card.select_one("[class*='Location'], [class*='location']")
                if loc:
                    parts = [p.strip() for p in loc.get_text(",", strip=True).split(",") if p.strip()]
                    if parts:
                        item["barrio"] = parts[0]
                    if len(parts) > 1:
                        item["municipio"] = parts[-1]

                desc = card.select_one("[class*='Description'], p")
                if desc:
                    item["description"] = desc.get_text(" ", strip=True)

                yield item
            except Exception as exc:  # noqa: BLE001
                self.log.warning("item_parse_error", extra={"error": str(exc)})

    def _convert_json_item(self, raw: dict) -> dict:
        """Mapea un realEstate del JSON al dict crudo estandar."""
        item: dict = {}
        detail = raw.get("detailedType") or {}
        addr = raw.get("address") or {}
        loc = raw.get("location") or addr

        slug = raw.get("detail", {}).get("es", {}).get("slug") if isinstance(raw.get("detail"), dict) else None
        path = raw.get("link") or raw.get("url") or (f"/d/{slug}" if slug else None)
        item["url"] = urljoin(self.BASE, path) if path else None
        item["titulo"] = raw.get("description", {}).get("es") if isinstance(raw.get("description"), dict) else raw.get("title")

        # Precios
        trans = (raw.get("transactions") or [{}])[0] if raw.get("transactions") else {}
        item["precio_venta"] = trans.get("value") or raw.get("price")

        # Caracteristicas
        feats = raw.get("features") or {}
        item["metros_cuadrados"] = feats.get("surface")
        item["habitaciones"] = feats.get("rooms")
        item["banos"] = feats.get("bathrooms")
        item["planta"] = feats.get("floor")
        item["ascensor"] = feats.get("elevator")
        item["terraza"] = feats.get("terrace") or feats.get("balcony")
        item["garaje"] = feats.get("parking") or feats.get("garage")
        item["estado"] = feats.get("conservationState") or feats.get("state")
        item["certificado_energetico"] = (feats.get("energyCertificate") or {}).get("rating") \
            if isinstance(feats.get("energyCertificate"), dict) else feats.get("energyCertificate")

        # Localizacion
        item["barrio"] = (loc.get("neighborhood") or {}).get("name") \
            if isinstance(loc.get("neighborhood"), dict) else loc.get("neighborhood")
        item["municipio"] = (loc.get("town") or {}).get("name") \
            if isinstance(loc.get("town"), dict) else loc.get("town")
        item["provincia"] = (loc.get("province") or {}).get("name") \
            if isinstance(loc.get("province"), dict) else loc.get("province")
        coords = raw.get("coordinates") or {}
        item["lat"] = coords.get("latitude") or raw.get("latitude")
        item["lon"] = coords.get("longitude") or raw.get("longitude")

        # Descripcion
        item["description"] = raw.get("description", {}).get("es") if isinstance(raw.get("description"), dict) else None

        return item

    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        # Patron: /l, /l/2, /l/3 ...
        m = re.search(r"/l(?:/(\d+))?/?$", current_url)
        if m:
            current_page = int(m.group(1) or 1)
            next_page = current_page + 1
            if m.group(1):
                return re.sub(r"/l/\d+/?$", f"/l/{next_page}", current_url)
            return current_url.rstrip("/") + f"/{next_page}"
        return None

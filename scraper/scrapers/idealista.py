"""Scraper para Idealista.com.

Notas:
- Idealista bloquea agresivamente con DataDome. Conviene usar Scrapling con
  StealthyFetcher (USE_JS = True).
- Estructura de busqueda: https://www.idealista.com/venta-viviendas/<zona>/
- Los anuncios estan dentro de <article class="item">.
- Respetar siempre robots.txt y los Terminos de Servicio.
"""
from __future__ import annotations

import re
from typing import Iterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper


class IdealistaScraper(BaseScraper):
    SOURCE = "idealista"
    USE_JS = True  # imprescindible contra DataDome

    BASE = "https://www.idealista.com"

    def parse_search_page(self, html: str, base_url: str) -> Iterator[dict]:
        soup = BeautifulSoup(html, "lxml")

        # Localización de página: extraída una vez y compartida como fallback
        page_municipio: Optional[str] = None
        page_barrio: Optional[str] = None
        bc = soup.select(".breadcrumb-geo li, nav.breadcrumb li")
        if len(bc) >= 2:
            page_municipio = bc[-2].get_text(strip=True)
            page_barrio = bc[-1].get_text(strip=True)
        elif len(bc) == 1:
            page_municipio = bc[0].get_text(strip=True)

        # Idealista usa <article class="item ..." data-element-id="...">
        articles = soup.select("article.item, article[data-element-id]")

        for art in articles:
            try:
                item: dict = {}

                # URL + titulo
                link = art.select_one("a.item-link") or art.select_one("a[href*='/inmueble/']")
                if not link:
                    continue
                href = link.get("href", "")
                item["url"] = urljoin(self.BASE, href)
                item["titulo"] = link.get_text(strip=True) or link.get("title")

                # Precio
                price_el = art.select_one(".item-price, .price-row .price")
                if price_el:
                    item["precio_venta"] = price_el.get_text(strip=True)

                # Detalles (m2, habitaciones, planta) - lista de <span>
                details = art.select(".item-detail, .item-detail-char span")
                for d in details:
                    txt = d.get_text(" ", strip=True).lower()
                    if "m²" in txt or "m2" in txt:
                        item["metros_cuadrados"] = txt
                    elif "hab" in txt:
                        item["habitaciones"] = txt
                    elif "planta" in txt or "bajo" in txt or "entrep" in txt or "ático" in txt:
                        item["planta"] = d.get_text(strip=True)
                    elif "ascensor" in txt:
                        item["ascensor"] = "sin ascensor" not in txt

                # Descripcion
                desc_el = art.select_one(".item-description")
                if desc_el:
                    item["description"] = desc_el.get_text(" ", strip=True)

                # Localización por artículo (si existe), si no, fallback de página
                loc_el = art.select_one(".item-location, [class*='location']")
                if loc_el:
                    parts = [p.strip() for p in loc_el.get_text(",", strip=True).split(",") if p.strip()]
                    item["municipio"] = parts[0] if parts else page_municipio
                    item["barrio"] = parts[-1] if len(parts) >= 2 else page_barrio
                else:
                    item["municipio"] = page_municipio
                    item["barrio"] = page_barrio

                yield item
            except Exception as exc:  # noqa: BLE001
                self.log.warning("item_parse_error", extra={"error": str(exc)})
                continue

    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        # Idealista usa <a class="icon-arrow-right-after">Siguiente</a>
        nxt = soup.select_one("a.icon-arrow-right-after, li.next a")
        if nxt and nxt.get("href"):
            return urljoin(self.BASE, nxt["href"])
        # Fallback: pagina-N en la URL
        m = re.search(r"pagina-(\d+)", current_url)
        if m:
            new_page = int(m.group(1)) + 1
            return current_url.replace(f"pagina-{m.group(1)}", f"pagina-{new_page}")
        # Primera paginacion: anadir pagina-2
        if page_num == 1 and not current_url.endswith("/"):
            return current_url.rstrip("/") + f"/pagina-2"
        if page_num == 1:
            return current_url + "pagina-2"
        return None

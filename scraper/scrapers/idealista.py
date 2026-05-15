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
                    elif "planta" in txt or "bajo" in txt or "entrep" in txt:
                        item["planta"] = txt
                    elif "ascensor" in txt:
                        item["ascensor"] = "sin ascensor" not in txt

                # Descripcion / features extra
                desc_el = art.select_one(".item-description")
                if desc_el:
                    item["description"] = desc_el.get_text(" ", strip=True)

                # Localizacion (la zona suele estar en el title o en h1 padre)
                # Idealista no la da inline en cada item; se extrae del breadcrumb
                # de la pagina de busqueda. Lo guardamos a partir del slug de la URL.
                slug_match = re.search(r"/inmueble/\d+/", item["url"])
                if slug_match:
                    # En la pagina de detalle vendran barrio/municipio reales.
                    pass

                # Etiqueta de zona en la pagina (h1)
                h1 = soup.select_one("h1")
                if h1:
                    item.setdefault("description", "")
                    item["description"] = f"{h1.get_text(' ', strip=True)} | {item['description']}"

                # Intentamos extraer municipio/barrio de breadcrumb
                bc = soup.select(".breadcrumb-geo li, nav.breadcrumb li")
                if bc and len(bc) >= 2:
                    item["municipio"] = bc[-1].get_text(strip=True) if bc else None
                    if len(bc) >= 3:
                        item["barrio"] = bc[-1].get_text(strip=True)
                        item["municipio"] = bc[-2].get_text(strip=True)

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

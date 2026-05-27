"""Scraper para Habitaclia.com."""
from __future__ import annotations

import re
from typing import Iterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper


class HabitacliaScraper(BaseScraper):
    SOURCE = "habitaclia"
    USE_JS = True

    BASE = "https://www.habitaclia.com"

    def parse_search_page(self, html: str, base_url: str) -> Iterator[dict]:
        soup = BeautifulSoup(html, "lxml")

        # Cada listing es un <article class="list-item-container ...">
        cards = soup.select("article.list-item-container")
        for card in cards:
            try:
                item: dict = {}

                # URL: viene en data-href del article (sin params de tracking)
                # o en el link del título si data-href no está
                url = card.get("data-href", "")
                if not url:
                    title_link = card.select_one("h3.list-item-title a")
                    url = title_link["href"] if title_link and title_link.get("href") else ""
                if not url:
                    continue
                # Limpiar params de tracking y hacer URL absoluta
                url = url.split("?")[0]
                item["url"] = urljoin(self.BASE, url) if not url.startswith("http") else url

                # Título
                title_a = card.select_one("h3.list-item-title a")
                item["titulo"] = title_a.get_text(strip=True) if title_a else ""

                # Precio: <span itemprop="price">750.000 €</span>
                price_el = card.select_one("span[itemprop='price']")
                if price_el:
                    item["precio_venta"] = price_el.get_text(strip=True)

                # Localización: "Barcelona - Sant Antoni"
                loc_el = card.select_one("p.list-item-location span, p.list-item-location")
                if loc_el:
                    parts = [p.strip() for p in loc_el.get_text(",", strip=True).split("-") if p.strip()]
                    if parts:
                        item["barrio"] = parts[-1].strip()
                    if len(parts) > 1:
                        item["municipio"] = parts[0].strip()

                # Features: "116m² - 2 habitaciones - 2 baños - 6.466€/m²"
                feat_el = card.select_one("p.list-item-feature")
                if feat_el:
                    txt = feat_el.get_text(" ", strip=True).lower()
                    m2 = re.search(r"(\d[\d.,]+)\s*m", txt)
                    if m2:
                        item["metros_cuadrados"] = m2.group(1).replace(".", "").replace(",", ".")
                    hab = re.search(r"(\d+)\s*habitaci", txt)
                    if hab:
                        item["habitaciones"] = int(hab.group(1))
                    ban = re.search(r"(\d+)\s*ba[ñn]", txt)
                    if ban:
                        item["banos"] = int(ban.group(1))
                    planta_m = re.search(
                        r"(\d+)[ºªº°]?\s*planta|planta\s*(\d+)"
                        r"|\b(planta baja|bajo|entresuelo|[aá]tico|semis[oó]tano|s[oó]tano)\b",
                        txt,
                    )
                    if planta_m:
                        item["planta"] = planta_m.group(1) or planta_m.group(2) or planta_m.group(3)

                # Descripción
                desc_el = card.select_one("p.list-item-description")
                if desc_el:
                    item["description"] = desc_el.get_text(" ", strip=True)

                yield item
            except Exception as exc:  # noqa: BLE001
                self.log.warning("item_parse_error", extra={"error": str(exc)})

    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        nxt = soup.select_one("a.next, a[rel='next'], a.pagination-next, a[aria-label='Siguiente']")
        if nxt and nxt.get("href"):
            return urljoin(self.BASE, nxt["href"])
        # Patrón: viviendas-distrito_eixample-barcelona.htm → -2.htm → -3.htm
        m = re.search(r"-(\d+)\.htm$", current_url)
        if m:
            next_num = int(m.group(1)) + 1
            return re.sub(r"-\d+\.htm$", f"-{next_num}.htm", current_url)
        if current_url.endswith(".htm") and page_num == 1:
            return current_url.replace(".htm", "-2.htm")
        return None

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
        cards = soup.select(
            "article.list-item-container, article[class*='list-item'], "
            "li.list-item"
        )
        for card in cards:
            try:
                item: dict = {}
                link = card.select_one("a[href*='/vivienda-en-'], a[href*='/inmueble']") \
                    or card.select_one("a.list-item-title, h3 a, h2 a")
                if not link:
                    continue
                item["url"] = urljoin(self.BASE, link.get("href", ""))
                item["titulo"] = link.get_text(strip=True) or link.get("title")

                # Precio
                price = card.select_one(".list-item-price, [class*='price']")
                if price:
                    item["precio_venta"] = price.get_text(strip=True)

                # Features
                features = card.select(".list-item-feature, [class*='feature'] li, ul.list-feature li")
                for f in features:
                    txt = f.get_text(" ", strip=True).lower()
                    if "m²" in txt or "m2" in txt:
                        item["metros_cuadrados"] = txt
                    elif "hab" in txt or "dorm" in txt:
                        item["habitaciones"] = txt
                    elif "baño" in txt or "bano" in txt:
                        item["banos"] = txt
                    elif "planta" in txt:
                        item["planta"] = txt

                # Localizacion
                loc = card.select_one(".list-item-location, [class*='location']")
                if loc:
                    parts = [p.strip() for p in loc.get_text(",", strip=True).split(",") if p.strip()]
                    if parts:
                        item["barrio"] = parts[0]
                    if len(parts) > 1:
                        item["municipio"] = parts[-1]

                desc = card.select_one(".list-item-description, p")
                if desc:
                    item["description"] = desc.get_text(" ", strip=True)

                yield item
            except Exception as exc:  # noqa: BLE001
                self.log.warning("item_parse_error", extra={"error": str(exc)})

    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        nxt = soup.select_one("a.next, a[rel='next'], a.pagination-next")
        if nxt and nxt.get("href"):
            return urljoin(self.BASE, nxt["href"])
        # Patron habitaclia: -N.htm
        m = re.search(r"-(\d+)\.htm$", current_url)
        if m:
            next_page = int(m.group(1)) + 1
            return re.sub(r"-\d+\.htm$", f"-{next_page}.htm", current_url)
        if current_url.endswith(".htm") and page_num == 1:
            return current_url.replace(".htm", "-2.htm")
        return None

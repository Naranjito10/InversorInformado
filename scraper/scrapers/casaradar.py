"""Scraper para Casaradar.es.

Casaradar es un agregador mas pequeno, normalmente sin JS challenges agresivos.
"""
from __future__ import annotations

import re
from typing import Iterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper


class CasaradarScraper(BaseScraper):
    SOURCE = "casaradar"
    USE_JS = False  # generalmente HTML estatico

    BASE = "https://www.casaradar.es"

    def parse_search_page(self, html: str, base_url: str) -> Iterator[dict]:
        soup = BeautifulSoup(html, "lxml")
        # Estructura tipica de agregadores
        cards = soup.select(
            "article.property, div.property-card, div.listing-item, "
            "article[class*='listing']"
        )
        if not cards:
            # Fallback: cualquier <a> que apunte a /comprar/<id>
            cards = soup.select("a[href*='/comprar/']")

        for card in cards:
            try:
                item: dict = {}
                if card.name == "a":
                    link = card
                    parent = card.parent or card
                else:
                    link = card.select_one("a[href*='/comprar/'], a[href*='/inmueble']")
                    parent = card
                    if not link:
                        link = card.select_one("a")
                if not link:
                    continue

                item["url"] = urljoin(self.BASE, link.get("href", ""))
                item["titulo"] = (link.get("title") or link.get_text(strip=True))[:200]

                price = parent.select_one("[class*='price'], .precio")
                if price:
                    item["precio_venta"] = price.get_text(strip=True)

                # Features
                features = parent.select("[class*='feature'] li, [class*='detail'] li, .specs li")
                for f in features:
                    txt = f.get_text(" ", strip=True).lower()
                    if "m²" in txt or "m2" in txt:
                        item["metros_cuadrados"] = txt
                    elif "hab" in txt:
                        item["habitaciones"] = txt
                    elif "baño" in txt or "bano" in txt:
                        item["banos"] = txt

                loc = parent.select_one("[class*='location'], [class*='zone'], .zona")
                if loc:
                    parts = [p.strip() for p in loc.get_text(",", strip=True).split(",") if p.strip()]
                    if parts:
                        item["barrio"] = parts[0]
                    if len(parts) > 1:
                        item["municipio"] = parts[-1]

                desc = parent.select_one("p.description, [class*='description']")
                if desc:
                    item["description"] = desc.get_text(" ", strip=True)

                yield item
            except Exception as exc:  # noqa: BLE001
                self.log.warning("item_parse_error", extra={"error": str(exc)})

    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        nxt = soup.select_one("a.next, a[rel='next'], a.page-next")
        if nxt and nxt.get("href"):
            return urljoin(self.BASE, nxt["href"])
        # Patron generico ?page=N
        m = re.search(r"[?&]page=(\d+)", current_url)
        if m:
            new_page = int(m.group(1)) + 1
            return re.sub(r"page=\d+", f"page={new_page}", current_url)
        sep = "&" if "?" in current_url else "?"
        return f"{current_url}{sep}page={page_num + 1}"

"""Scraper para pisos.com."""
from __future__ import annotations

import re
from typing import Iterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper


class PisosScraper(BaseScraper):
    SOURCE = "pisos"
    USE_JS = False  # httpx + Fetcher es suficiente, no necesita Chromium

    BASE = "https://www.pisos.com"

    def parse_search_page(self, html: str, base_url: str) -> Iterator[dict]:
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select("div.ad-preview"):
            try:
                item: dict = {}

                # URL: data-lnk-href es relativo ("/comprar/piso-...")
                url = card.get("data-lnk-href", "")
                if not url:
                    title_a = card.select_one("a.ad-preview__title")
                    url = title_a["href"] if title_a and title_a.get("href") else ""
                if not url:
                    continue
                item["url"] = urljoin(self.BASE, url)

                # Título
                title_el = card.select_one("a.ad-preview__title")
                item["titulo"] = title_el.get_text(strip=True) if title_el else ""

                # Precio: "450.000 €"
                price_el = card.select_one("span.ad-preview__price")
                if price_el:
                    item["precio_venta"] = price_el.get_text(strip=True)

                # Subtítulo: "Centre (Granollers)" o "Eixample (Barcelona)"
                sub_el = card.select_one("p.ad-preview__subtitle")
                if sub_el:
                    sub = sub_el.get_text(strip=True)
                    m = re.match(r"^(.+?)\s*\((.+)\)$", sub)
                    if m:
                        item["barrio"] = m.group(1).strip()
                        item["municipio"] = m.group(2).strip()
                    else:
                        item["municipio"] = sub

                # Características: ["3 habs.", "2 baños", "116 m²", "3ª planta"]
                for feat in card.select("p.ad-preview__char"):
                    txt = feat.get_text(strip=True).lower()
                    m2 = re.search(r"([\d.,]+)\s*m", txt)
                    if m2 and ("m²" in txt or "m2" in txt or "m " in txt):
                        item["metros_cuadrados"] = m2.group(1).replace(".", "").replace(",", ".")
                    elif "hab" in txt:
                        n = re.search(r"(\d+)", txt)
                        if n:
                            item["habitaciones"] = int(n.group(1))
                    elif "planta" in txt or "bajo" in txt or "ático" in txt or "atico" in txt:
                        item["planta"] = feat.get_text(strip=True)
                    elif "baño" in txt or "bano" in txt:
                        n = re.search(r"(\d+)", txt)
                        if n:
                            item["banos"] = int(n.group(1))

                # Descripción
                desc_el = card.select_one("p.ad-preview__description")
                if desc_el:
                    item["description"] = desc_el.get_text(" ", strip=True)

                # Fotos — thumbnails de la card
                foto_urls: list[str] = []
                for img in card.select("img"):
                    src = img.get("data-src") or img.get("src") or ""
                    if src and not src.startswith("data:") and any(
                        ext in src.lower() for ext in (".jpg", ".jpeg", ".png", ".webp")
                    ):
                        foto_urls.append(src)
                item["foto_urls"] = foto_urls[:10]

                yield item
            except Exception as exc:  # noqa: BLE001
                self.log.warning("item_parse_error", extra={"error": str(exc)})

    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        # Preferir patrón URL para mantener el filtro de zona (ej. eixample-barcelona)
        # en vez del link nativo que puede ampliar al área genérica (barcelona).
        m = re.search(r"/(\d+)/$", current_url)
        if m:
            next_n = int(m.group(1)) + 1
            return re.sub(r"/\d+/$", f"/{next_n}/", current_url)
        if current_url.endswith("/") and page_num == 1:
            return f"{current_url}2/"

        # Fallback: link "Siguiente" del HTML
        soup = BeautifulSoup(html, "lxml")
        nxt = soup.select_one("div.pagination__next a, a.pagination__next")
        if nxt and nxt.get("href"):
            return urljoin(self.BASE, nxt["href"])
        return None

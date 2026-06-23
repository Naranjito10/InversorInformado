"""Clase base para todos los scrapers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional

from ..infrastructure.logger import get_logger
from ..models import Listing


@dataclass
class ScraperResult:
    source: str
    listings: list[Listing] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    pages_fetched: int = 0

    @property
    def count(self) -> int:
        return len(self.listings)


class BaseScraper(ABC):
    """Interfaz comun para scrapers."""

    SOURCE: str = "base"
    USE_JS: bool = False  # True si el portal requiere JS rendering

    def __init__(self) -> None:
        self.log = get_logger(self.SOURCE)

    @abstractmethod
    def parse_search_page(self, html: str, base_url: str) -> Iterator[dict]:
        """Yields dicts crudos de cada anuncio en una pagina de busqueda."""

    @abstractmethod
    def next_page_url(self, html: str, current_url: str, page_num: int) -> Optional[str]:
        """Devuelve la URL de la siguiente pagina, o None si es la ultima."""

    def scrape_search(
        self,
        search_url: str,
        max_pages: int = 3,
        max_results: int = 100,
    ) -> ScraperResult:
        """
        Recorre paginas de busqueda hasta alcanzar max_pages O max_results,
        lo que ocurra primero.
        """
        from ..infrastructure.http_client import fetch_with_delay
        from ..services.normalizer import normalize

        result = ScraperResult(source=self.SOURCE)
        url = search_url
        page = 1

        while url and page <= max_pages and len(result.listings) < max_results:
            self.log.info("page_fetch_start", extra={"url": url, "page": page})
            html = fetch_with_delay(url, use_js=self.USE_JS)
            if not html:
                result.errors.append({"url": url, "stage": "fetch"})
                break
            result.pages_fetched += 1

            try:
                raw_items = list(self.parse_search_page(html, url))
            except Exception as exc:  # noqa: BLE001
                self.log.error("parse_error", extra={"url": url, "error": str(exc)})
                result.errors.append({"url": url, "stage": "parse", "error": str(exc)})
                break

            self.log.info(
                "page_parsed", extra={"url": url, "page": page, "items": len(raw_items)},
            )
            if page == 1 and len(raw_items) == 0:
                self.log.warning("page1_empty_html_snippet", extra={"url": url, "html": html[:600]})

            for raw in raw_items:
                if len(result.listings) >= max_results:
                    break
                try:
                    if not raw.get("url"):
                        continue
                    listing = normalize(self.SOURCE, raw)
                    result.listings.append(listing)
                except Exception as exc:  # noqa: BLE001
                    self.log.warning(
                        "normalize_error",
                        extra={"raw": raw.get("url"), "error": str(exc)},
                    )
                    result.errors.append({
                        "url": raw.get("url"), "stage": "normalize", "error": str(exc),
                    })

            url = self.next_page_url(html, url, page)
            page += 1

        return result

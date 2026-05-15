"""Scrapers individuales por portal inmobiliario."""

from .base import BaseScraper, ScraperResult
from .idealista import IdealistaScraper
from .fotocasa import FotocasaScraper
from .habitaclia import HabitacliaScraper
from .casaradar import CasaradarScraper

__all__ = [
    "BaseScraper",
    "ScraperResult",
    "IdealistaScraper",
    "FotocasaScraper",
    "HabitacliaScraper",
    "CasaradarScraper",
]


def get_scraper(source: str) -> BaseScraper:
    """Factory: devuelve la instancia de scraper para una fuente."""
    mapping = {
        "idealista": IdealistaScraper,
        "fotocasa": FotocasaScraper,
        "habitaclia": HabitacliaScraper,
        "casaradar": CasaradarScraper,
    }
    cls = mapping.get(source.lower())
    if cls is None:
        raise ValueError(f"Fuente desconocida: {source}")
    return cls()

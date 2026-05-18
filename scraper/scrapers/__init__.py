"""Scrapers individuales por portal inmobiliario."""

from .base import BaseScraper, ScraperResult
from .casaradar import CasaradarScraper
from .fotocasa import FotocasaScraper
from .habitaclia import HabitacliaScraper
from .idealista import IdealistaScraper
from .pisos import PisosScraper

__all__ = [
    "BaseScraper",
    "ScraperResult",
    "CasaradarScraper",
    "FotocasaScraper",
    "HabitacliaScraper",
    "IdealistaScraper",
    "PisosScraper",
]


def get_scraper(source: str) -> BaseScraper:
    """Factory: devuelve la instancia de scraper para una fuente."""
    mapping = {
        "casaradar": CasaradarScraper,
        "fotocasa": FotocasaScraper,
        "habitaclia": HabitacliaScraper,
        "idealista": IdealistaScraper,
        "pisos": PisosScraper,
    }
    cls = mapping.get(source.lower())
    if cls is None:
        raise ValueError(f"Fuente desconocida: {source}")
    return cls()

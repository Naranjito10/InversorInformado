"""Scrapers individuales por portal inmobiliario."""

from .base import BaseScraper, ScraperResult
from .fotocasa import FotocasaScraper
from .habitaclia import HabitacliaScraper
from .idealista import IdealistaScraper
from .pisos import PisosScraper

__all__ = [
    "BaseScraper",
    "ScraperResult",
    "FotocasaScraper",
    "HabitacliaScraper",
    "IdealistaScraper",
    "PisosScraper",
]


def get_scraper(source: str) -> BaseScraper:
    """Factory: devuelve la instancia de scraper para una fuente."""
    mapping = {
        "fotocasa": FotocasaScraper,
        "habitaclia": HabitacliaScraper,
        "idealista": IdealistaScraper,
        "pisos": PisosScraper,
    }
    cls = mapping.get(source.lower())
    if cls is None:
        raise ValueError(f"Fuente desconocida: {source}")
    return cls()

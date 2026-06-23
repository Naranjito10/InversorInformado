"""Geocodificación con Nominatim (OpenStreetMap). Gratis, sin API key."""
from __future__ import annotations
import logging

log = logging.getLogger(__name__)

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut
    _geocoder = Nominatim(user_agent="InversorInformado/1.0")
    _HAS_GEOPY = True
except ImportError:
    _HAS_GEOPY = False


def geocode(address: str, municipio: str) -> tuple[float, float] | None:
    """
    Geocodifica dirección libre + municipio vía Nominatim.
    Devuelve (lat, lon) o None si no se encuentra la ubicación.
    El caller gestiona el rate-limit sleep.

    No hace fallback a nivel de municipio: una coordenada de centro de ciudad
    produciría una referencia catastral aleatoria al consultar el OVC.
    """
    if not _HAS_GEOPY:
        log.error("geocoder_geopy_not_installed")
        return None

    parts = [p for p in [address.strip(), municipio.strip()] if p]
    if not parts:
        return None
    query = ", ".join(parts) + ", España"

    try:
        location = _geocoder.geocode(query, country_codes="es", timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except GeocoderTimedOut:
        log.warning("geocode_timeout", extra={"query": query})
    except Exception as exc:  # noqa: BLE001
        log.error("geocode_failed", extra={"query": query, "error": str(exc)})

    return None

"""
CatastroEnricher — enriquece listings con datos del Catastro Español (OVC REST).

Flujo por listing:
  1. Geocodifica dirección → (lat, lon) vía Nominatim si no hay coords
  2. Consulta_RCCOOR REST → obtiene referencia catastral (PC1+PC2)
  3. Consulta_DNPRC REST  → obtiene año de construcción y superficie
  4. Deriva ite_obligatoria = (año_actual - anyo_construccion) >= 50

URL del OVC: http://ovc.catastro.meh.es/OVCServWeb/OVCWcfLibres/RESTServiceLibres.svc
  - Solo disponible vía HTTP (no HTTPS). El Catastro está migrando de ovc.catastro.meh.es
    a la Sede Electrónica pero los servicios WCF libres aún no están en el nuevo dominio.
  - La disponibilidad es intermitente; cuando el servicio está caído el circuit breaker
    evita spamear peticiones fallidas durante el resto del batch.

Circuit breaker: tras _OVC_DOWN_AFTER_FAILURES consecutivos, no se intenta más
hasta que pasen _OVC_DOWN_BACKOFF_HOURS. Se resetea al reiniciar el servidor.
"""
from __future__ import annotations
import logging
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

import httpx

from scraper.infrastructure import db
from .base import BaseEnricher
from .geocoder import geocode

log = logging.getLogger(__name__)

# RCCOOR: GET sobre OVCCoordenadas.asmx (confirmado funcional)
_OVC_RCCOOR = "http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx/Consulta_RCCOOR"
# DNPRC: SOAP POST sobre OVCCallejeroRC.asmx (solo disponible vía SOAP)
_OVC_SOAP = "http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejeroRC.asmx"

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_HEADERS_GET = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}
_HEADERS_SOAP = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": "http://www.catastro.meh.es/Consulta_DNPRC",
    "User-Agent": _UA,
}
_TIMEOUT = 12
_RATE_SLEEP = 1.1
_GEOCODE_RETRY_DAYS = 7

# Circuit breaker — estado en memoria (se resetea al reiniciar)
_OVC_DOWN_AFTER_FAILURES = 3
_OVC_DOWN_BACKOFF_HOURS = 4
_ovc_consecutive_failures = 0
_ovc_down_until: datetime | None = None


def _ovc_is_down() -> bool:
    if _ovc_down_until is None:
        return False
    return datetime.now(timezone.utc) < _ovc_down_until


def _ovc_record_failure() -> None:
    global _ovc_consecutive_failures, _ovc_down_until
    _ovc_consecutive_failures += 1
    if _ovc_consecutive_failures >= _OVC_DOWN_AFTER_FAILURES:
        _ovc_down_until = datetime.now(timezone.utc) + timedelta(hours=_OVC_DOWN_BACKOFF_HOURS)
        _ovc_consecutive_failures = 0
        log.warning(
            "catastro_ovc_circuit_open",
            extra={"down_until": _ovc_down_until.isoformat(), "backoff_hours": _OVC_DOWN_BACKOFF_HOURS},
        )


def _ovc_record_success() -> None:
    global _ovc_consecutive_failures, _ovc_down_until
    _ovc_consecutive_failures = 0
    _ovc_down_until = None


def _find_text(root: ET.Element, local_tag: str) -> str | None:
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == local_tag:
            return elem.text
    return None


class CatastroEnricher(BaseEnricher):
    name = "catastro"

    def needs_enrichment(self, listing_row: dict) -> bool:
        if listing_row.get("referencia_catastral"):
            return False
        if not listing_row.get("municipio"):
            return False
        if _ovc_is_down():
            return False  # circuit breaker abierto, no intentar

        meta = listing_row.get("enrichment_meta") or {}
        failed_at_str = meta.get("catastro_geocode_failed_at")
        if failed_at_str:
            try:
                failed_at = datetime.fromisoformat(failed_at_str)
                if (datetime.now(timezone.utc) - failed_at).days < _GEOCODE_RETRY_DAYS:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    def enrich(self, listing_row: dict) -> dict:
        results: dict = {}
        listing_id = listing_row.get("id")

        lat = listing_row.get("latitud") or listing_row.get("lat")
        lon = listing_row.get("longitud") or listing_row.get("lon")

        if not (lat and lon):
            titulo = listing_row.get("titulo") or ""
            municipio = listing_row.get("municipio", "")
            coords = geocode(titulo, municipio)
            if coords is None:
                log.warning("catastro_geocode_failed", extra={"id": listing_id})
                db.merge_enrichment_meta(listing_id, {
                    "catastro_geocode_failed_at": datetime.now(timezone.utc).isoformat()
                })
                return {}
            lat, lon = coords
            time.sleep(_RATE_SLEEP)

        if not listing_row.get("latitud"):
            results["latitud"] = lat
            results["longitud"] = lon

        rc = self._get_rc_by_coords(lat, lon)
        if not rc:
            log.warning("catastro_rc_not_found", extra={"id": listing_id, "lat": lat, "lon": lon})
            return results
        results["referencia_catastral"] = rc
        time.sleep(_RATE_SLEEP)

        details = self._get_building_details(rc)
        if details:
            anyo = details.get("anyo_construccion")
            if anyo:
                results["anyo_construccion"] = anyo
                results["ite_obligatoria"] = (date.today().year - anyo) >= 50
            if details.get("superficie_catastral"):
                results["superficie_catastral"] = details["superficie_catastral"]

        return results

    def _get_rc_by_coords(self, lat: float, lon: float) -> str | None:
        """
        Consulta_RCCOOR GET (OVCCoordenadas.asmx): coordenadas → PC1+PC2.
        SRS se embebe en la URL para evitar que httpx codifique ':' → '%3A'.
        """
        url = f"{_OVC_RCCOOR}?SRS=EPSG:4326&Coordenada_X={lon}&Coordenada_Y={lat}"
        try:
            with httpx.Client(follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS_GET, timeout=_TIMEOUT)
            resp.raise_for_status()

            if "<html" in resp.text[:200].lower():
                log.warning("catastro_rccoor_html", extra={"lat": lat, "lon": lon, "body": resp.text[:200]})
                _ovc_record_failure()
                return None

            root = ET.fromstring(resp.text)
            pc1 = _find_text(root, "pc1")
            pc2 = _find_text(root, "pc2")
            if pc1 and pc2:
                _ovc_record_success()
                return f"{pc1}{pc2}"

            log.warning("catastro_rccoor_no_pc", extra={"lat": lat, "lon": lon, "body": resp.text[:200]})
            return None
        except httpx.HTTPStatusError as exc:
            log.error("catastro_rccoor_failed", extra={
                "lat": lat, "lon": lon,
                "status": exc.response.status_code,
                "body": exc.response.text[:200],
            })
            _ovc_record_failure()
        except Exception as exc:  # noqa: BLE001
            log.error("catastro_rccoor_failed", extra={"lat": lat, "lon": lon, "error": str(exc)})
            _ovc_record_failure()
        return None

    def _get_building_details(self, rc: str) -> dict | None:
        """Consulta_DNPRC GET (OVCCallejeroRC.asmx): RC → año construcción y superficie."""
        pc1 = rc[:7]
        pc2 = rc[7:14] if len(rc) >= 14 else ""
        url = f"{_OVC_SOAP}/Consulta_DNPRC?Provincia=&Municipio=&RC.PC1={pc1}&RC.PC2={pc2}&RC.Car=&RC.CC1=&RC.CC2="
        try:
            with httpx.Client(follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS_GET, timeout=_TIMEOUT)
            resp.raise_for_status()

            if "<html" in resp.text[:200].lower():
                log.warning("catastro_dnprc_html", extra={"rc": rc, "body": resp.text[:200]})
                return None

            root = ET.fromstring(resp.text)
            details: dict = {}
            anoint = _find_text(root, "anoint")
            if anoint:
                try:
                    details["anyo_construccion"] = int(anoint)
                except ValueError:
                    pass
            sfc = _find_text(root, "sfc")
            if sfc:
                try:
                    details["superficie_catastral"] = int(sfc)
                except ValueError:
                    pass
            return details or None
        except httpx.HTTPStatusError as exc:
            log.error("catastro_dnprc_failed", extra={
                "rc": rc,
                "url": url,
                "status": exc.response.status_code,
                "body": exc.response.text[:200],
            })
        except Exception as exc:  # noqa: BLE001
            log.error("catastro_dnprc_failed", extra={"rc": rc, "url": url, "error": str(exc)})
        return None

"""
CatastroEnricher — enriquece listings con datos del Catastro Español (OVC REST).

Flujo actual (lo que la API OVC expone libremente):
  1. Geocodifica dirección → (lat, lon) vía Nominatim si no hay coords
  2. INSPIRE WFS bbox → nationalCadastralReference (más tolerante que RCCOOR ante coords imprecisas)

Campos que escribe: referencia_catastral, latitud, longitud, anyo_construccion,
superficie_catastral, ite_obligatoria.

Flujo completo:
  1. Geocodifica dirección → (lat, lon) vía Nominatim si no hay coords
  2. INSPIRE WFS bbox → referencia_catastral (PC1+PC2)
  3. HTML scraping Sede Electrónica → anyo_construccion y superficie_catastral
     URL: https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCListaBienes.aspx?rc1=&rc2=
     Nota: la API OVC NO expone año/superficie para viviendas residenciales (privacidad).

Circuit breaker: tras _OVC_DOWN_AFTER_FAILURES consecutivos, no se intenta más
hasta que pasen _OVC_DOWN_BACKOFF_HOURS. Se resetea al reiniciar el servidor.
"""
from __future__ import annotations
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup

from scraper.infrastructure import db
from .base import BaseEnricher
from .geocoder import geocode

log = logging.getLogger(__name__)

_OVC_BASE = "http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC"
# INSPIRE WFS: bbox → nationalCadastralReference (reemplaza RCCOOR — tolerante ante coords imprecisas)
_INSPIRE_WFS = "http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"
_WFS_BBOX_DELTA = 0.0002  # ~22 metros en cada dirección
# Sede Electrónica: HTML scraping → año construcción y superficie
_SEDE_URL = "https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCListaBienes.aspx"
_SEDE_RETRY_DAYS = 30
# Municipio texto → códigos numéricos Catastro (distintos de los INE) — reservado para futura extensión
_OVC_MUNICIPIO = f"{_OVC_BASE}/OVCCallejeroCodigos.asmx/ConsultaMunicipioCodigos"
# DNPRC: RC + códigos Catastro → dirección/año/superficie — reservado para futura extensión
_OVC_DNPRC = f"{_OVC_BASE}/OVCCallejeroCodigos.asmx/Consulta_DNPRC_Codigos"

# Caché en memoria: "BARCELONA" → ("8", "900")
_municipio_codes_cache: dict[str, tuple[str, str]] = {}

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_HEADERS_GET = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
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
        meta = listing_row.get("enrichment_meta") or {}
        has_rc = bool(listing_row.get("referencia_catastral"))
        has_anyo = listing_row.get("anyo_construccion") is not None

        if has_rc and has_anyo:
            return False  # completamente enriquecido

        if has_rc:
            # Tiene RC pero falta año — intentar scraping Sede Electrónica
            failed_at_str = meta.get("catastro_sede_failed_at")
            if failed_at_str:
                try:
                    failed_at = datetime.fromisoformat(failed_at_str)
                    if (datetime.now(timezone.utc) - failed_at).days < _SEDE_RETRY_DAYS:
                        return False
                except (ValueError, TypeError):
                    pass
            return True

        # Sin RC: necesita geocodificación + WFS
        if _ovc_is_down():
            return False
        if not listing_row.get("municipio"):
            return False
        for key in ("catastro_geocode_failed_at", "catastro_wfs_failed_at"):
            failed_at_str = meta.get(key)
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

        rc = listing_row.get("referencia_catastral")

        if not rc:
            # Paso 1: obtener coordenadas
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

            # Paso 2: INSPIRE WFS → RC
            rc = self._get_rc_by_coords(lat, lon)
            if rc:
                results["referencia_catastral"] = rc
            else:
                if listing_id:
                    db.merge_enrichment_meta(listing_id, {
                        "catastro_wfs_failed_at": datetime.now(timezone.utc).isoformat()
                    })
                return results

        # Paso 3: Sede Electrónica → año construcción y superficie
        if listing_row.get("anyo_construccion") is None:
            sede_data = self._scrape_building_year(rc, listing_id)
            if sede_data:
                anyo = sede_data.get("anyo_construccion")
                if anyo:
                    results["anyo_construccion"] = anyo
                    results["ite_obligatoria"] = (date.today().year - anyo) >= 50
                if sede_data.get("superficie_catastral"):
                    results["superficie_catastral"] = sede_data["superficie_catastral"]

        return results

    def _scrape_building_year(self, rc: str, listing_id: str | None = None) -> dict | None:
        """
        HTML scraping de Sede Electrónica → año construcción y superficie.
        Los datos de año/superficie para viviendas NO están en la API OVC por privacidad.
        """
        pc1, pc2 = rc[:7], rc[7:14] if len(rc) >= 14 else rc[7:]
        url = f"{_SEDE_URL}?rc1={pc1}&rc2={pc2}"
        try:
            with httpx.Client(follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS_GET, timeout=20)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(separator=" ", strip=True)

            details: dict = {}

            # Formato A: página de bien inmueble individual — "Año de construcción: YYYY"
            for pattern in (
                r"[Aa]ño\s+(?:de\s+)?[Cc]onstrucci[oó]n\D{0,10}(\d{4})",
                r"[Aa]ntig[üu]edad\D{0,10}(\d{4})",
                r"[Cc]onstrucci[oó]n\D{0,10}(\d{4})",
            ):
                m = re.search(pattern, text)
                if m:
                    anyo = int(m.group(1))
                    if 1850 <= anyo <= date.today().year:
                        details["anyo_construccion"] = anyo
                    break

            # Formato B: lista de inmuebles — "Residencial | 132 m 2 | 8,14% | 1929"
            # El año es el último campo tras el pipe; range 1[89]xx o 20xx descarta superficies
            if "anyo_construccion" not in details:
                m = re.search(r"\|\s*(1[89]\d{2}|20[012]\d)\b", text)
                if m:
                    anyo = int(m.group(1))
                    if 1850 <= anyo <= date.today().year:
                        details["anyo_construccion"] = anyo

            # Superficie construida — solo en formato A (en formato B es por unidad, no total)
            m = re.search(r"[Ss]uperficie\s+(?:construida|total)\D{0,15}(\d+)\s*m", text)
            if m:
                try:
                    details["superficie_catastral"] = int(m.group(1))
                except ValueError:
                    pass

            if details:
                log.info("catastro_sede_scraped", extra={"rc": rc, **details})
            else:
                log.warning("catastro_sede_no_data", extra={"rc": rc, "sample": text[:400]})
                if listing_id:
                    db.merge_enrichment_meta(listing_id, {
                        "catastro_sede_failed_at": datetime.now(timezone.utc).isoformat()
                    })

            return details or None
        except Exception as exc:  # noqa: BLE001
            log.error("catastro_sede_failed", extra={"rc": rc, "error": str(exc)})
            if listing_id:
                db.merge_enrichment_meta(listing_id, {
                    "catastro_sede_failed_at": datetime.now(timezone.utc).isoformat()
                })
            return None

    # ── Métodos reservados para futura extensión ─────────────────────────────
    # Cuando se implemente el HTML scraper de Sede Electrónica para anyo_construccion,
    # estos métodos serán necesarios para construir la URL de consulta DNPRC.

    def _get_municipio_codes(self, municipio: str) -> tuple[str, str] | None:
        """ConsultaMunicipioCodigos → (cd, cmc) en sistema Catastro (≠ INE). Necesario para DNPRC."""
        key = municipio.upper().strip()
        if key in _municipio_codes_cache:
            return _municipio_codes_cache[key]
        url = f"{_OVC_MUNICIPIO}?CodigoProvincia=&CodigoMunicipio=&CodigoMunicipioINE=&Municipio={key}"
        try:
            with httpx.Client(follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS_GET, timeout=_TIMEOUT)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            # Iterar <muni> buscando <nm> que coincida (la respuesta puede incluir varios)
            for muni_elem in root.iter():
                tag = muni_elem.tag.split("}")[-1] if "}" in muni_elem.tag else muni_elem.tag
                if tag != "muni":
                    continue
                nm = _find_text(muni_elem, "nm")
                if not nm or nm.upper().strip() != key:
                    continue
                # Códigos Catastro están en <locat><cd> y <locat><cmc> (distintos de INE en <loine>)
                cd = _find_text(muni_elem, "cd")
                cmc = _find_text(muni_elem, "cmc")
                if cd and cmc:
                    result = (cd.strip(), cmc.strip())
                    _municipio_codes_cache[key] = result
                    log.info("catastro_municipio_codes", extra={"municipio": municipio, "cd": cd, "cmc": cmc})
                    return result
            log.warning("catastro_municipio_codes_not_found", extra={"municipio": municipio, "body": resp.text[:300]})
        except Exception as exc:  # noqa: BLE001
            log.warning("catastro_municipio_codes_failed", extra={"municipio": municipio, "error": str(exc)})
        return None

    def _get_rc_by_coords(self, lat: float, lon: float) -> str | None:
        """INSPIRE WFS bbox → nationalCadastralReference. Tolera coords en calle/acera (±22m)."""
        bbox = (
            f"{lat - _WFS_BBOX_DELTA},{lon - _WFS_BBOX_DELTA},"
            f"{lat + _WFS_BBOX_DELTA},{lon + _WFS_BBOX_DELTA},EPSG:4326"
        )
        url = (
            f"{_INSPIRE_WFS}?service=wfs&version=2.0.0&request=getfeature"
            f"&TYPENAMES=cp:CadastralParcel&BBOX={bbox}"
        )
        try:
            with httpx.Client(follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS_GET, timeout=_TIMEOUT)
            resp.raise_for_status()

            if "<html" in resp.text[:200].lower():
                log.warning("catastro_wfs_html", extra={"lat": lat, "lon": lon, "body": resp.text[:200]})
                _ovc_record_failure()
                return None

            root = ET.fromstring(resp.text)
            rc = _find_text(root, "nationalCadastralReference")
            if rc:
                _ovc_record_success()
                log.info("catastro_wfs_rc_found", extra={"lat": lat, "lon": lon, "rc": rc.strip()})
                return rc.strip()

            log.warning("catastro_wfs_no_rc", extra={"lat": lat, "lon": lon, "body": resp.text[:400]})
            return None
        except httpx.HTTPStatusError as exc:
            log.error("catastro_wfs_failed", extra={
                "lat": lat, "lon": lon,
                "status": exc.response.status_code,
                "body": exc.response.text[:200],
            })
            _ovc_record_failure()
        except Exception as exc:  # noqa: BLE001
            log.error("catastro_wfs_failed", extra={"lat": lat, "lon": lon, "error": str(exc)})
            _ovc_record_failure()
        return None

    def _get_building_details(
        self,
        rc: str,
        listing_id: str | None = None,
        cod_provincia: str = "",
        cod_municipio: str = "",
    ) -> dict | None:
        """Consulta_DNPRC_Codigos GET: RC + códigos numéricos → año construcción y superficie."""
        url = f"{_OVC_DNPRC}?CodigoProvincia={cod_provincia}&CodigoMunicipio={cod_municipio}&CodigoMunicipioINE=&RC={rc}"
        try:
            with httpx.Client(follow_redirects=False) as client:
                resp = client.get(url, headers=_HEADERS_GET, timeout=_TIMEOUT)
            log.info("catastro_dnprc_raw", extra={
                "rc": rc,
                "status": resp.status_code,
                "location": resp.headers.get("location", ""),
                "content_type": resp.headers.get("content-type", ""),
                "body": resp.text[:300],
            })
            resp.raise_for_status()

            if "<html" in resp.text[:200].lower():
                log.warning("catastro_dnprc_html", extra={"rc": rc, "body": resp.text[:200]})
                if listing_id:
                    db.merge_enrichment_meta(listing_id, {
                        "catastro_dnprc_failed_at": datetime.now(timezone.utc).isoformat()
                    })
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
            if listing_id:
                db.merge_enrichment_meta(listing_id, {
                    "catastro_dnprc_failed_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as exc:  # noqa: BLE001
            log.error("catastro_dnprc_failed", extra={"rc": rc, "url": url, "error": str(exc)})
        return None

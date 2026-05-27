"""Normalizador: convierte datos crudos de cada fuente al esquema unificado."""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

from ..models import Listing


# ---------------------------------------------------------------------------
# Helpers de parseo
# ---------------------------------------------------------------------------

_PRICE_RE = re.compile(r"(\d[\d\.\s ]*)\s*(?:€|EUR)?", re.IGNORECASE)
_INT_RE = re.compile(r"(\d+)")
_M2_RE = re.compile(r"(\d+[\.,]?\d*)\s*m[²¹ 2]?", re.IGNORECASE)


def clean_int(text: Optional[str]) -> Optional[int]:
    """'1.250.000 €' -> 1250000; '85 m²' -> 85; None si no hay numero."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return int(text)
    s = str(text)
    # Quitar separadores de miles y espacios
    s = s.replace(".", "").replace(",", ".").replace(" ", " ")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return int(float(m.group(0)))
    except (ValueError, TypeError):
        return None


def clean_float(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).replace(".", "").replace(",", ".").replace(" ", " ")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except (ValueError, TypeError):
        return None


def clean_str(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    s = " ".join(str(text).split())
    return s or None


def parse_bool(text: Any) -> Optional[bool]:
    """Detecta presencia de feature en una descripcion."""
    if text is None:
        return None
    if isinstance(text, bool):
        return text
    s = str(text).lower()
    truthy = ["si", "sí", "con ", "incluye", "yes", "true"]
    falsy = ["sin ", "no ", "false"]
    if any(t in s for t in truthy):
        return True
    if any(t in s for t in falsy):
        return False
    return None


def canonical_url(url: str) -> str:
    """Quita query strings y fragments para deduplicar."""
    try:
        p = urlparse(url.strip())
        return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", "", ""))
    except Exception:
        return url


def detect_features(text: str) -> dict[str, Optional[bool]]:
    """Detecta ascensor / terraza / garaje en texto libre.

    Prioridad a las negaciones ('sin ascensor'), luego presencia positiva.
    """
    s = (text or "").lower()

    def _feature(positive: list[str], negative: list[str]) -> Optional[bool]:
        if any(n in s for n in negative):
            return False
        if any(p in s for p in positive):
            return True
        return None

    return {
        "ascensor": _feature(["ascensor"], ["sin ascensor"]),
        "terraza":  _feature(["terraza", "balcón", "balcon"], ["sin terraza", "sin balcón", "sin balcon"]),
        "garaje":   _feature(["garaje", "parking", "plaza de garaje"], ["sin garaje", "sin parking"]),
    }


def detect_estado(text: str) -> Optional[str]:
    """Detecta estado en texto libre."""
    if not text:
        return None
    s = text.lower()
    if "a reformar" in s or "para reformar" in s or "para reform" in s or "rehab" in s:
        return "a reformar"
    if "obra nueva" in s or "a estrenar" in s or "nueva construcción" in s:
        return "nuevo"
    if "buen estado" in s or "reformado" in s or "segunda mano" in s:
        return "buen estado"
    return None


def detect_cee(text: str) -> Optional[str]:
    """Detecta certificado energetico A-G."""
    if not text:
        return None
    # Acepta: 'certificado', 'consumo', 'etiqueta', 'energetic*'
    m = re.search(
        r"(?:certificado|consumo|etiqueta|energétic\w*|energetic\w*)[^A-G]{0,30}([A-G])\b",
        text,
        re.I,
    )
    if m:
        return m.group(1).upper()
    return None


_HOUSE_SUBTYPES = {"house", "chalet", "semidetached_house", "terraced_house", "villa", "country_house", "farm"}
_FLAT_SUBTYPES = {"flat", "duplex", "penthouse", "ground_floor", "studio", "apartment", "loft"}

_HOUSE_TITLE_WORDS = ["chalet", "villa", "adosado", "unifamiliar", "casa independiente"]
_FLAT_TITLE_WORDS = ["piso", "apartamento", "estudio", "loft", "dúplex", "duplex"]


def detect_tipo_propiedad(raw_subtype: Any, titulo: str, url: str) -> Optional[str]:
    """Detecta si es Casa o Piso a partir del subtipo crudo, título o URL."""
    if raw_subtype:
        s = str(raw_subtype).lower().replace("-", "_")
        if s in _HOUSE_SUBTYPES or "house" in s or "chalet" in s or "villa" in s:
            return "Casa"
        if s in _FLAT_SUBTYPES or "flat" in s or "apartment" in s:
            return "Piso"
    text = ((titulo or "") + " " + (url or "")).lower()
    if any(w in text for w in _HOUSE_TITLE_WORDS):
        return "Casa"
    if any(w in text for w in _FLAT_TITLE_WORDS):
        return "Piso"
    return None


_PLANTA_MAP = {
    "0": "Bajo", "bajo": "Bajo", "planta baja": "Bajo", "pb": "Bajo",
    "entresuulo": "Entresuelo", "entresuelo": "Entresuelo",
    "atico": "Ático", "ático": "Ático",
    "semisotano": "Semisótano", "semisótano": "Semisótano",
    "sotano": "Sótano", "sótano": "Sótano",
}


def normalize_planta(v: Any) -> Optional[str]:
    """Normaliza la planta: 0/'bajo'→'Bajo', 1→'1ª', 'ático'→'Ático', etc."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s or s == "none":
        return None
    if s in _PLANTA_MAP:
        return _PLANTA_MAP[s]
    # "3ª planta", "planta 3", "3 planta"
    m = re.search(r"(\d+)[ºªº°]?\s*planta|planta\s*(\d+)", s)
    if m:
        n = int(m.group(1) or m.group(2))
        return "Bajo" if n == 0 else f"{n}ª"
    # Numero suelto o con sufijo: "1", "1ª", "2º"
    m = re.match(r"^(\d+)[ºªº°]?$", s)
    if m:
        n = int(m.group(1))
        return "Bajo" if n == 0 else f"{n}ª"
    return clean_str(str(v))


# ---------------------------------------------------------------------------
# Normalizador principal
# ---------------------------------------------------------------------------

def normalize(source: str, raw: dict[str, Any]) -> Listing:
    """
    Convierte un dict crudo (extraido por un scraper concreto) a un Listing.

    El scraper de cada fuente debe devolver un dict con las claves estandar
    que abajo se procesan; los campos opcionales se rellenan a None.
    """
    url = canonical_url(str(raw.get("url", "")))

    precio = clean_int(raw.get("precio_venta") or raw.get("precio"))
    m2 = clean_int(raw.get("metros_cuadrados") or raw.get("m2"))

    precio_m2 = None
    if precio and m2 and m2 > 0:
        precio_m2 = round(precio / m2)
    elif raw.get("precio_m2"):
        precio_m2 = clean_int(raw.get("precio_m2"))

    # Texto libre para detectar features si los campos directos no vienen
    description = " ".join(
        str(raw.get(k, "")) for k in ("titulo", "description", "descripcion", "features")
    )
    feats = detect_features(description)

    listing = Listing(
        url=url,
        fuente=source,
        titulo=clean_str(raw.get("titulo") or raw.get("title")),

        precio_venta=precio,
        ibi=clean_int(raw.get("ibi")),
        comunidad=clean_int(raw.get("comunidad")),
        derramas_pendientes=clean_int(raw.get("derramas_pendientes")),
        precio_m2=precio_m2,

        metros_cuadrados=m2,
        habitaciones=clean_int(raw.get("habitaciones") or raw.get("rooms")),
        banos=clean_int(raw.get("banos") or raw.get("bathrooms")),
        planta=normalize_planta(raw.get("planta") if raw.get("planta") is not None else raw.get("floor")),
        tipo_propiedad=detect_tipo_propiedad(
            raw.get("tipo_propiedad"),
            raw.get("titulo") or raw.get("title") or "",
            str(raw.get("url", "")),
        ),
        ascensor=raw.get("ascensor") if isinstance(raw.get("ascensor"), bool) else feats["ascensor"],
        terraza=raw.get("terraza") if isinstance(raw.get("terraza"), bool) else feats["terraza"],
        garaje=raw.get("garaje") if isinstance(raw.get("garaje"), bool) else feats["garaje"],
        estado=clean_str(raw.get("estado")) or detect_estado(description),
        certificado_energetico=clean_str(raw.get("certificado_energetico"))
                               or detect_cee(description),

        barrio=clean_str(raw.get("barrio") or raw.get("neighborhood")),
        municipio=clean_str(raw.get("municipio") or raw.get("city")),
        provincia=clean_str(raw.get("provincia") or raw.get("province")),
        lat=clean_float(raw.get("lat") or raw.get("latitude")),
        lon=clean_float(raw.get("lon") or raw.get("longitude")),

        alquiler_estimado=clean_int(raw.get("alquiler_estimado")),
        precio_zona_m2=clean_int(raw.get("precio_zona_m2")),

        raw_data=raw,
    )
    return listing
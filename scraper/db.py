"""Capa de acceso a Supabase: upsert con deduplicacion por URL."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import config
from .logger import get_logger
from .models import Listing

log = get_logger("db")

try:
    from supabase import create_client, Client  # type: ignore
    _HAS_SUPABASE = True
except ImportError:
    _HAS_SUPABASE = False
    Client = None  # type: ignore


_client: Optional["Client"] = None


def get_client() -> Optional["Client"]:
    """Devuelve el cliente Supabase (singleton), o None si no esta configurado."""
    global _client
    if _client is not None:
        return _client
    if not _HAS_SUPABASE:
        log.error("supabase_not_installed")
        return None
    if not config.supabase.enabled:
        log.warning("supabase_not_configured")
        return None
    _client = create_client(config.supabase.url, config.supabase.key)
    return _client


def get_existing(url: str) -> Optional[dict]:
    """Devuelve la fila existente para una URL, o None."""
    client = get_client()
    if client is None:
        return None
    try:
        res = (
            client.table("listings")
            .select("*")
            .eq("url", url)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
    except Exception as exc:  # noqa: BLE001
        log.error("db_get_failed", extra={"url": url, "error": str(exc)})
    return None


def upsert_listing(listing: Listing) -> Optional[dict]:
    """
    Inserta o actualiza una vivienda en Supabase.

    Logica:
    - Si no existe: insert con primera_deteccion = ahora, veces_visto = 1
    - Si existe: update con veces_visto +=1; si precio bajo, bajada_precio = true
    - El trigger SQL recalcula derivados (precio_m2, rentabilidad, score, etc.)

    Devuelve la fila final o None si falla.
    """
    client = get_client()
    if client is None:
        return None

    payload = listing.to_db_dict()
    existing = get_existing(listing.url)
    now = datetime.now(timezone.utc).isoformat()

    try:
        if existing is None:
            payload["primera_deteccion"] = now
            payload["ultima_actualizacion"] = now
            payload["veces_visto"] = 1
            payload["activo"] = True
            res = client.table("listings").insert(payload).execute()
            log.info(
                "listing_inserted",
                extra={"url": listing.url, "fuente": listing.fuente,
                       "precio": listing.precio_venta},
            )
            return res.data[0] if res.data else None

        # Actualizacion
        update_payload = {**payload}
        update_payload["veces_visto"] = (existing.get("veces_visto") or 1) + 1
        update_payload["ultima_actualizacion"] = now
        update_payload["activo"] = True

        # Mantener primera_deteccion original
        update_payload.pop("primera_deteccion", None)

        # bajada_precio se calcula en el trigger SQL al detectar cambio
        # pero por si el trigger no esta, marcamos aqui tambien:
        old_price = existing.get("precio_venta")
        new_price = listing.precio_venta
        if old_price and new_price and new_price < old_price:
            update_payload["bajada_precio"] = True

        res = (
            client.table("listings")
            .update(update_payload)
            .eq("url", listing.url)
            .execute()
        )
        log.info(
            "listing_updated",
            extra={
                "url": listing.url,
                "fuente": listing.fuente,
                "old_price": old_price,
                "new_price": new_price,
            },
        )
        return res.data[0] if res.data else None

    except Exception as exc:  # noqa: BLE001
        log.error("db_upsert_failed", extra={"url": listing.url, "error": str(exc)})
        return None


def mark_inactive(urls_seen: set[str], source: str) -> int:
    """
    Marca como `activo=false` los anuncios de una fuente que NO se vieron
    en el ultimo scraping (probablemente vendidos/retirados).

    Llamar al final de un ciclo completo de una fuente.
    """
    client = get_client()
    if client is None:
        return 0
    try:
        # Traer todos los activos de la fuente
        existing = (
            client.table("listings")
            .select("id,url")
            .eq("fuente", source)
            .eq("activo", True)
            .execute()
        )
        to_deactivate = [
            row["id"] for row in (existing.data or [])
            if row["url"] not in urls_seen
        ]
        if not to_deactivate:
            return 0
        client.table("listings").update({"activo": False}).in_("id", to_deactivate).execute()
        log.info("listings_deactivated", extra={"fuente": source, "count": len(to_deactivate)})
        return len(to_deactivate)
    except Exception as exc:  # noqa: BLE001
        log.error("db_deactivate_failed", extra={"fuente": source, "error": str(exc)})
        return 0


def get_price_drops_last_24h(min_score: int = 60, min_pct: float = 5.0) -> list[dict]:
    """Lista de anuncios con bajada significativa de precio en las ultimas 24h."""
    client = get_client()
    if client is None:
        return []
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        res = (
            client.table("listings")
            .select("*")
            .eq("bajada_precio", True)
            .gte("score", min_score)
            .gte("ultima_actualizacion", since)
            .execute()
        )
        return res.data or []
    except Exception as exc:  # noqa: BLE001
        log.error("db_query_failed", extra={"error": str(exc)})
        return []


def get_high_score_listings(min_score: int = 80, limit: int = 50) -> list[dict]:
    """Top N viviendas con score alto."""
    client = get_client()
    if client is None:
        return []
    try:
        res = (
            client.table("listings")
            .select("*")
            .gte("score", min_score)
            .eq("activo", True)
            .order("score", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as exc:  # noqa: BLE001
        log.error("db_query_failed", extra={"error": str(exc)})
        return []


def query_listings(filters: dict | None = None, limit: int = 1000) -> list[dict]:
    """
    Query generica con filtros opcionales para exportar/dashboards.

    Filtros soportados:
        municipio, barrio, fuente, score_label, activo,
        precio_min, precio_max, rentabilidad_min, score_min,
        fecha_desde, fecha_hasta
    """
    client = get_client()
    if client is None:
        return []
    filters = filters or {}
    try:
        q = client.table("listings").select("*")
        for key in ("municipio", "barrio", "fuente", "score_label"):
            if filters.get(key):
                q = q.eq(key, filters[key])
        if "activo" in filters:
            q = q.eq("activo", filters["activo"])
        if filters.get("precio_min") is not None:
            q = q.gte("precio_venta", filters["precio_min"])
        if filters.get("precio_max") is not None:
            q = q.lte("precio_venta", filters["precio_max"])
        if filters.get("rentabilidad_min") is not None:
            q = q.gte("rentabilidad_bruta", filters["rentabilidad_min"])
        if filters.get("score_min") is not None:
            q = q.gte("score", filters["score_min"])
        if filters.get("fecha_desde"):
            q = q.gte("primera_deteccion", filters["fecha_desde"])
        if filters.get("fecha_hasta"):
            q = q.lte("primera_deteccion", filters["fecha_hasta"])

        q = q.order("score", desc=True).limit(limit)
        res = q.execute()
        return res.data or []
    except Exception as exc:  # noqa: BLE001
        log.error("db_query_failed", extra={"error": str(exc)})
        return []

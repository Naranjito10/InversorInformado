"""Capa de acceso a Supabase: upsert con deduplicacion por URL."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import config
from .logger import get_logger
from ..models import Listing

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
    - Si no existe: insert con primera_deteccion = ahora, veces_visto = 1, status = 'activo'
    - Si existe: update con veces_visto +=1; si precio bajo, bajada_precio = true
      Nunca sobrescribe status, disabled_reason ni duplicate_candidate_of en updates.
    - El trigger SQL recalcula derivados (precio_m2, rentabilidad, score, etc.)
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

        # Nunca sobrescribir en re-scrape — preservar estado gestionado manualmente
        update_payload.pop("status", None)
        update_payload.pop("disabled_reason", None)
        update_payload.pop("duplicate_candidate_of", None)
        update_payload.pop("primera_deteccion", None)

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
    Marca como `status='inactivo'` los anuncios de una fuente que NO se vieron
    en el ultimo scraping (probablemente vendidos/retirados).
    """
    client = get_client()
    if client is None:
        return 0
    try:
        existing = (
            client.table("listings")
            .select("id,url")
            .eq("fuente", source)
            .eq("status", "activo")
            .execute()
        )
        to_deactivate = [
            row["id"] for row in (existing.data or [])
            if row["url"] not in urls_seen
        ]
        if not to_deactivate:
            return 0
        client.table("listings").update({
            "status": "inactivo",
            "disabled_reason": "no_visto_scraper",
        }).in_("id", to_deactivate).execute()
        log.info("listings_deactivated", extra={"fuente": source, "count": len(to_deactivate)})
        return len(to_deactivate)
    except Exception as exc:  # noqa: BLE001
        log.error("db_deactivate_failed", extra={"fuente": source, "error": str(exc)})
        return 0


def find_near_duplicate(listing: "Listing", tolerance: float = 0.10) -> Optional[dict]:
    """
    Busca un anuncio activo que sea probablemente el mismo piso:
    mismo municipio, precio y metros_cuadrados dentro de ±tolerance, habitaciones igual.
    """
    client = get_client()
    if client is None:
        return None
    if not (listing.municipio and listing.precio_venta and listing.metros_cuadrados):
        return None
    try:
        price_lo = int(listing.precio_venta * (1 - tolerance))
        price_hi = int(listing.precio_venta * (1 + tolerance))
        m2_lo = int(listing.metros_cuadrados * (1 - tolerance))
        m2_hi = int(listing.metros_cuadrados * (1 + tolerance))

        q = (
            client.table("listings")
            .select("url,fuente,titulo,precio_venta,metros_cuadrados,habitaciones,barrio,municipio")
            .eq("municipio", listing.municipio)
            .eq("status", "activo")
            .neq("url", listing.url)
            .gte("precio_venta", price_lo)
            .lte("precio_venta", price_hi)
            .gte("metros_cuadrados", m2_lo)
            .lte("metros_cuadrados", m2_hi)
        )
        if listing.habitaciones is not None:
            q = q.eq("habitaciones", listing.habitaciones)

        res = q.limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as exc:  # noqa: BLE001
        log.error("db_near_duplicate_failed", extra={"url": listing.url, "error": str(exc)})
        return None


def get_pending_review_listings(limit: int = 100) -> list[dict]:
    """Devuelve anuncios pendientes de revisión, enriquecidos con datos del original."""
    client = get_client()
    if client is None:
        return []
    try:
        res = (
            client.table("listings")
            .select("*")
            .eq("status", "pendiente_revision")
            .order("primera_deteccion", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        for row in rows:
            original_url = row.get("duplicate_candidate_of")
            row["original_info"] = None
            if original_url:
                try:
                    orig = (
                        client.table("listings")
                        .select("titulo,precio_venta,metros_cuadrados,habitaciones,barrio,municipio,primera_deteccion,url")
                        .eq("url", original_url)
                        .limit(1)
                        .execute()
                    )
                    row["original_info"] = orig.data[0] if orig.data else None
                except Exception:
                    pass
        return rows
    except Exception as exc:  # noqa: BLE001
        log.error("db_query_failed", extra={"error": str(exc)})
        return []


def approve_pending(listing_id: str) -> bool:
    """Aprueba un candidato a duplicado: lo mantiene activo y quita la marca de revisión."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("listings").update({
            "status": "activo",
            "duplicate_candidate_of": None,
        }).eq("id", listing_id).execute()
        log.info("listing_approved", extra={"id": listing_id})
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("db_approve_failed", extra={"id": listing_id, "error": str(exc)})
        return False


def reject_pending(listing_id: str) -> bool:
    """Rechaza un candidato a duplicado: lo descarta y registra el motivo."""
    client = get_client()
    if client is None:
        return False
    try:
        client.table("listings").update({
            "status": "descartado",
            "disabled_reason": "duplicado_antiguo_elegido",
        }).eq("id", listing_id).execute()
        log.info("listing_rejected", extra={"id": listing_id})
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("db_reject_failed", extra={"id": listing_id, "error": str(exc)})
        return False


def keep_new_listing(listing_id: str) -> bool:
    """
    'Dejar el nuevo': activa el candidato nuevo y descarta el original.
    El nuevo listing apunta al original via duplicate_candidate_of.
    """
    client = get_client()
    if client is None:
        return False
    try:
        res = (
            client.table("listings")
            .select("id,duplicate_candidate_of")
            .eq("id", listing_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            log.error("keep_new_not_found", extra={"id": listing_id})
            return False

        original_url = res.data[0].get("duplicate_candidate_of")
        if original_url:
            client.table("listings").update({
                "status": "descartado",
                "disabled_reason": "duplicado_nuevo_elegido",
            }).eq("url", original_url).execute()

        client.table("listings").update({
            "status": "activo",
            "duplicate_candidate_of": None,
        }).eq("id", listing_id).execute()

        log.info("keep_new_listing", extra={"id": listing_id, "original_url": original_url})
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("db_keep_new_failed", extra={"id": listing_id, "error": str(exc)})
        return False


def get_price_drops_last_24h(min_score: int = 60, min_pct: float = 5.0) -> list[dict]:  # noqa: ARG001
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
            .eq("status", "activo")
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
        municipio, barrio, fuente, score_label, activo (bool, maps to status='activo'),
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
            if filters["activo"]:
                q = q.eq("status", "activo")
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

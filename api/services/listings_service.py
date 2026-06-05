from __future__ import annotations
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from scraper.models import Listing
from scraper.infrastructure.db import (
    approve_pending, get_client, get_existing, get_pending_review_listings,
    keep_new_listing as db_keep_new, query_listings, reject_pending,
    upsert_listing,
)
from scraper.infrastructure.logger import get_logger
from api.schemas import StatsOut

log = get_logger("listings_service")


def get_listings(filters: dict, limit: int = 200) -> list[dict]:
    return query_listings(filters=filters, limit=limit)


def create_manual_listing(data: dict) -> dict:
    from scraper.runner import _enrich_local_score
    listing = Listing(**data)
    _enrich_local_score(listing)
    existed = get_existing(listing.url) is not None
    result = upsert_listing(listing)
    return {"status": "updated" if existed else "inserted", "ok": result is not None}


def check_urls_exist(urls: list[str]) -> dict[str, bool]:
    if not urls:
        return {}
    client = get_client()
    if client is None:
        return {url: False for url in urls}
    try:
        res = client.table("listings").select("url").in_("url", urls).execute()
        existing = {row["url"] for row in (res.data or [])}
        return {url: url in existing for url in urls}
    except Exception as exc:
        log.error("check_urls_exist_failed", extra={"error": str(exc)})
        return {url: False for url in urls}


def bulk_import_listings(listings: list[dict]) -> dict:
    from scraper.runner import _enrich_local_score
    inserted = updated = errors = 0
    error_details: list[dict] = []
    for item in listings:
        try:
            listing = Listing(**item)
            _enrich_local_score(listing)
            existed = get_existing(listing.url) is not None
            result = upsert_listing(listing)
            if result is not None:
                if existed:
                    updated += 1
                else:
                    inserted += 1
            else:
                errors += 1
                error_details.append({"url": item.get("url", "?"), "error": "Error al guardar en BD"})
        except ValidationError as exc:
            errors += 1
            error_details.append({"url": item.get("url", "?"), "error": str(exc)})
        except Exception as exc:
            errors += 1
            error_details.append({"url": item.get("url", "?"), "error": str(exc)})
    return {"inserted": inserted, "updated": updated, "errors": errors, "error_details": error_details}


def get_pending_review(limit: int = 100) -> list[dict]:
    return get_pending_review_listings(limit=limit)


def approve_listing(listing_id: str) -> bool:
    return approve_pending(listing_id)


def reject_listing(listing_id: str) -> bool:
    return reject_pending(listing_id)


def keep_new_listing(listing_id: str) -> bool:
    return db_keep_new(listing_id)


def get_zonas() -> list[dict]:
    client = get_client()
    if client is None:
        return []
    try:
        res = client.table("listings").select("municipio,barrio").eq("status", "activo").limit(3000).execute()
        rows = res.data or []

        municipios = sorted({r["municipio"] for r in rows if r.get("municipio")})
        barrios_by_muni: dict[str, set[str]] = {}
        for r in rows:
            if r.get("barrio") and r.get("municipio"):
                barrios_by_muni.setdefault(r["municipio"], set()).add(r["barrio"])

        result: list[dict] = []
        for m in municipios:
            result.append({"tipo": "municipio", "valor": m, "label": m})
        for municipio, barrios in sorted(barrios_by_muni.items()):
            for barrio in sorted(barrios):
                result.append({"tipo": "barrio", "valor": barrio, "label": f"{barrio} · {municipio}", "municipio": municipio})
        return result
    except Exception as exc:
        log.error("get_zonas_failed", extra={"error": str(exc)})
        return []


def get_stats() -> StatsOut:
    una_semana = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    todos = query_listings(filters={"activo": True}, limit=5000)
    nuevos = query_listings(filters={"activo": True, "fecha_desde": una_semana}, limit=5000)

    scores = [l["score"] for l in todos if l.get("score") is not None]
    score_medio = round(sum(scores) / len(scores), 1) if scores else 0.0
    bajadas = sum(1 for l in todos if l.get("bajada_precio"))

    por_fuente: dict[str, int] = {}
    por_label: dict[str, int] = {}
    for l in todos:
        fuente = l.get("fuente") or "desconocido"
        label = l.get("score_label") or "sin_label"
        por_fuente[fuente] = por_fuente.get(fuente, 0) + 1
        por_label[label] = por_label.get(label, 0) + 1

    return StatsOut(
        total_activos=len(todos),
        nuevos_esta_semana=len(nuevos),
        score_medio=score_medio,
        bajadas_precio=bajadas,
        por_fuente=por_fuente,
        por_label=por_label,
    )

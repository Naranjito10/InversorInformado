from __future__ import annotations
from datetime import datetime, timedelta, timezone
from scraper.infrastructure.db import (
    approve_pending, get_pending_review_listings, query_listings, reject_pending,
)
from api.schemas import StatsOut


def get_listings(filters: dict, limit: int = 200) -> list[dict]:
    return query_listings(filters=filters, limit=limit)


def create_manual_listing(data: dict) -> dict:
    from scraper.models import Listing
    from scraper.infrastructure.db import upsert_listing, get_existing
    from scraper.runner import _enrich_local_score
    listing = Listing(**data)
    _enrich_local_score(listing)
    existed = get_existing(listing.url) is not None
    result = upsert_listing(listing)
    return {"status": "updated" if existed else "inserted", "ok": result is not None}


def check_urls_exist(urls: list[str]) -> dict[str, bool]:
    from scraper.infrastructure.db import get_client
    if not urls:
        return {}
    client = get_client()
    if client is None:
        return {url: False for url in urls}
    try:
        res = client.table("listings").select("url").in_("url", urls).execute()
        existing = {row["url"] for row in (res.data or [])}
        return {url: url in existing for url in urls}
    except Exception:
        return {url: False for url in urls}


def bulk_import_listings(listings: list[dict]) -> dict:
    from scraper.models import Listing
    from scraper.infrastructure.db import upsert_listing, get_existing
    from scraper.runner import _enrich_local_score
    from pydantic import ValidationError
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
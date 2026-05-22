from __future__ import annotations
from datetime import datetime, timedelta, timezone
from scraper.infrastructure.db import (
    approve_pending, get_pending_review_listings, query_listings, reject_pending,
)
from api.schemas import StatsOut


def get_listings(filters: dict, limit: int = 200) -> list[dict]:
    return query_listings(filters=filters, limit=limit)


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
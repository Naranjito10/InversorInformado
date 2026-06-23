"""
Runner de enriquecimiento por lotes.

Lee umbrales desde la tabla config, consulta los listings elegibles
y ejecuta todos los enriquecedores registrados sobre cada uno.
"""
from __future__ import annotations
import logging
from scraper.infrastructure import db
from scraper import enrichers as enricher_registry

log = logging.getLogger(__name__)


def run_batch() -> dict:
    """
    Ciclo de enriquecimiento:
    1. Lee enrichment_threshold_cheap y enrichment_batch_limit de config.
    2. Obtiene listings activos con score >= threshold.
    3. Para cada listing, ejecuta cada enriquecedor registrado.
    4. Persiste los campos devueltos con set_enrichment_field().

    Devuelve stats: {processed, fields_written, errors}.
    """
    threshold = int(db.get_config_value("enrichment_threshold_cheap") or 40)
    batch_limit = int(db.get_config_value("enrichment_batch_limit") or 100)

    listings = db.query_listings_for_enrichment(min_score=threshold, limit=batch_limit)
    log.info("enrichment_batch_start", extra={"listings": len(listings), "threshold": threshold})

    all_enrichers = enricher_registry.get_all()
    stats: dict = {"processed": 0, "fields_written": 0, "errors": 0}

    for row in listings:
        listing_id = row.get("id")
        for enricher in all_enrichers:
            if not enricher.needs_enrichment(row):
                continue
            try:
                fields = enricher.enrich(row)
                for field, value in fields.items():
                    db.set_enrichment_field(listing_id, field, enricher.name, value)
                    stats["fields_written"] += 1
                    row[field] = value  # actualiza en memoria para enriquecedores posteriores
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "enricher_failed",
                    extra={"enricher": enricher.name, "id": listing_id, "error": str(exc)},
                )
                stats["errors"] += 1
        stats["processed"] += 1

    log.info("enrichment_batch_done", extra=stats)
    return stats

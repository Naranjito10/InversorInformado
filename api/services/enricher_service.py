from __future__ import annotations
from scraper import enricher_runner
from scraper import queue_worker


def run_enrichment_background() -> dict:
    """Encola un ciclo de enriquecimiento en el worker compartido."""
    queue_worker.submit(enricher_runner.run_batch)
    return {"status": "queued", "message": "Enriquecimiento encolado"}

from __future__ import annotations
from fastapi import APIRouter
from api.services import enricher_service

router = APIRouter(prefix="/api/enricher", tags=["enricher"])


@router.post("/run")
def trigger_enrichment():
    """Encola un ciclo de enriquecimiento en background."""
    return enricher_service.run_enrichment_background()

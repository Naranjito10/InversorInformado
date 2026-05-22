from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks, HTTPException
from api.schemas import SearchRequest, SearchResponse
from api.services import scraper_service

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


@router.post("/run")
def run_cycle(background_tasks: BackgroundTasks):
    """Lanza un ciclo completo con los targets de search_targets.json."""
    background_tasks.add_task(scraper_service.run_cycle_background)
    return {"status": "queued", "message": "Ciclo de scraping iniciado en background"}


@router.post("/search", response_model=SearchResponse)
def custom_search(req: SearchRequest, background_tasks: BackgroundTasks):
    """Lanza una búsqueda personalizada por zona, portales y precio."""
    targets = scraper_service.build_search_targets(
        zona_label=req.zona,
        portales=req.portales,
        precio_min=req.precio_min,
        precio_max=req.precio_max,
        max_pages=req.max_pages,
    )

    if not targets:
        raise HTTPException(
            status_code=404,
            detail=f"Zona '{req.zona}' no encontrada o sin portales disponibles",
        )

    background_tasks.add_task(scraper_service.run_targets_background, targets)

    return SearchResponse(
        status="queued",
        zona=req.zona,
        portales=req.portales,
        targets=len(targets),
        search_urls=[t["url"] for t in targets],
    )
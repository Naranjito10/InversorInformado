from __future__ import annotations
from fastapi import APIRouter, HTTPException
from api.schemas import SearchRequest, SearchResponse
from api.services import scraper_service
from scraper import state as scraper_state
from scraper import queue_worker

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


@router.get("/status")
def get_status():
    return scraper_state.get()


@router.post("/status/dismiss")
def dismiss_status():
    scraper_state.dismiss()
    return {"ok": True}


@router.post("/run")
def run_cycle():
    """Lanza un ciclo completo con los targets de search_targets.json."""
    current = scraper_state.get()
    if current["running"]:
        scraper_state.inc_queued()
    else:
        scraper_state.set_running(message="Preparando ciclo completo...")
    queue_worker.submit(scraper_service.run_cycle_background)
    return {"status": "queued", "message": "Ciclo de scraping iniciado en background"}


@router.post("/search", response_model=SearchResponse)
def custom_search(req: SearchRequest):
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

    current = scraper_state.get()
    if current["running"]:
        scraper_state.inc_queued()
    else:
        portales_str = ", ".join(req.portales)
        scraper_state.set_running(message=f"Preparando búsqueda en {portales_str}...")

    queue_worker.submit(scraper_service.run_targets_background, targets)

    return SearchResponse(
        status="queued",
        zona=req.zona,
        portales=req.portales,
        targets=len(targets),
        search_urls=[t["url"] for t in targets],
    )
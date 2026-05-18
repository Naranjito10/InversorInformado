"""FastAPI webhook server: receives Tally form submissions and runs the scraper."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Ensure project root is on sys.path so `scraper` is importable.
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from .tally_parser import parse_tally_payload  # noqa: E402
from .url_builder import build_targets, load_zones  # noqa: E402

log = logging.getLogger("webhook")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="RealStateAnalyse Webhook", version="1.0.0")

_zones: dict | None = None


def _get_zones() -> dict:
    global _zones
    if _zones is None:
        _zones = load_zones()
    return _zones


def _run_scraping(targets: list[dict]) -> None:
    """Background task: import runner lazily to avoid loading scraper at startup."""
    try:
        from scraper.runner import run_targets  # type: ignore[import]
        stats = run_targets(targets)
        log.info(
            "scrape_done targets=%d new=%d updated=%d errors=%d",
            stats.total_targets,
            stats.total_new,
            stats.total_updated,
            stats.total_errors,
        )
    except Exception:
        log.exception("scrape_background_failed")


@app.post("/webhook/tally")
async def tally_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """Receive a Tally FORM_RESPONSE and queue a scraping run."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    req = parse_tally_payload(payload)

    if not req.zone_label:
        raise HTTPException(status_code=422, detail="Zona field is missing or empty")

    zones = _get_zones()
    targets = build_targets(req, zones)

    if not targets:
        return JSONResponse(
            status_code=200,
            content={
                "status": "no_targets",
                "message": f"Zone '{req.zone_label}' not found or no portals available.",
                "zone": req.zone_label,
            },
        )

    background_tasks.add_task(_run_scraping, targets)

    log.info("scrape_queued zone=%s portals=%s targets=%d", req.zone_label, req.portals, len(targets))
    return JSONResponse(
        status_code=202,
        content={
            "status": "queued",
            "zone": req.zone_label,
            "portals": req.portals,
            "targets": len(targets),
            "price_min": req.price_min,
            "price_max": req.price_max,
            "max_pages": req.max_pages,
            "max_results": req.max_results,
            "search_urls": [t["url"] for t in targets],
        },
    )


@app.get("/health")
async def health() -> dict:
    zones = _get_zones()
    return {"status": "ok", "zones_loaded": len(zones)}

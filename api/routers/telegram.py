from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scraper.services.reports import ReportType, publish_report
from scraper.infrastructure.config import config

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class PublishReportRequest(BaseModel):
    type: ReportType
    title: str
    body: str
    zone: Optional[str] = None


@router.post("/publish")
def publish(req: PublishReportRequest):
    """Publica un informe en el canal público de Telegram."""
    if not config.telegram.channel_enabled:
        raise HTTPException(
            status_code=503,
            detail="Canal de Telegram no configurado. Revisa TELEGRAM_BOT_TOKEN y TELEGRAM_CHANNEL_ID en .env",
        )

    ok = publish_report(
        report_type=req.type,
        title=req.title,
        body=req.body,
        zone=req.zone,
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Error al enviar el mensaje a Telegram")

    return {"status": "published", "channel_id": config.telegram.channel_id, "type": req.type}


@router.get("/status")
def status():
    """Comprueba si el canal está configurado."""
    return {
        "alerts_configured": config.telegram.enabled,
        "channel_configured": config.telegram.channel_enabled,
        "channel_id": config.telegram.channel_id or None,
    }

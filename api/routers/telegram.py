from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scraper.services.reports import ReportType, publish_report
from scraper.infrastructure.config import config
from api.services import telegram_service
from api.services.reports_service import get_report
from api.services.scheduler_service import run_weekly_publish

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


@router.get("/log")
def get_telegram_log():
    """Historial de mensajes enviados al canal."""
    return telegram_service.get_log()


@router.post("/publish-report/{report_id}")
def publish_report_from_id(report_id: str):
    """Genera resumen del informe con Claude y lo publica en el canal."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    try:
        text = telegram_service.publish_report_summary(report_id, report)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"status": "published", "preview": text[:100]}


@router.post("/generate-weekly")
def generate_weekly_report():
    """Genera y publica el informe semanal automático (también llamado por el scheduler)."""
    return run_weekly_publish()

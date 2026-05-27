from __future__ import annotations

from typing import Optional

import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scraper.services.reports import ReportType, publish_report
from scraper.services.alerts import publish_to_channel
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


@router.get("/log")
def get_telegram_log():
    """Historial de mensajes enviados al canal."""
    from scraper.infrastructure.db import get_client
    client = get_client()
    res = client.table("telegram_log").select("*").order("sent_at", desc=True).limit(100).execute()
    return res.data or []


@router.post("/publish-report/{report_id}")
def publish_report_from_id(report_id: str):
    """Genera resumen del informe con Claude y lo publica en el canal."""
    from scraper.infrastructure.db import get_client
    from api.services.reports_service import get_report

    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    data = report["data"]
    p = data.get("property", {})
    m = data.get("market", {})
    s = data.get("scores", {})

    ai_client = anthropic.Anthropic()
    prompt = f"""Genera un mensaje corto para el canal de Telegram @inversorinformado sobre este análisis de inversión.
El mensaje debe tener: emoji 📊, barrio y municipio, precio, precio/m², rentabilidad bruta, score global.
Al final añade: "👉 Análisis completo: https://inversorinformado.vercel.app/login"
Máximo 5 líneas. Usa HTML de Telegram (<b>, <i>). Sin JSON, solo el texto del mensaje.

Datos:
- Dirección: {p.get('direccion', '?')}, {p.get('barrio', '?')}, {p.get('municipio', '?')}
- Precio: {p.get('precio', '?')} €
- Precio/m²: {round(p.get('precio', 0) / max(p.get('metros', 1), 1))} € (media zona: {m.get('precio_m2_zona_medio', '?')} €)
- Rentabilidad bruta: {m.get('rentabilidad_bruta', '?')}%
- Score global: {s.get('global', '?')}/100 ({s.get('global_grade', '?')})
"""
    response = ai_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    ok = publish_to_channel(text)
    if not ok:
        raise HTTPException(status_code=502, detail="Error publicando en Telegram")

    db_client = get_client()
    db_client.table("telegram_log").insert({
        "type": "from_report",
        "content": text,
        "report_id": report_id,
        "status": "sent",
    }).execute()

    return {"status": "published", "preview": text[:100]}


@router.post("/generate-weekly")
def generate_weekly_report():
    """Genera y publica el informe semanal automático (también llamado por el scheduler)."""
    from api.services.scheduler_service import run_weekly_publish
    result = run_weekly_publish()
    return result

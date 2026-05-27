from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import anthropic

from scraper.infrastructure.db import get_client
from scraper.services.alerts import publish_to_channel
from scraper.infrastructure.logger import get_logger

log = get_logger("scheduler")


def get_top_properties_for_weekly(limit: int = 5) -> list[dict]:
    """Propiedades con mejor score no publicadas en los últimos 14 días."""
    client = get_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    res = (
        client.table("listings")
        .select("id, titulo, barrio, municipio, precio_venta, metros_cuadrados, habitaciones, score, url")
        .eq("activo", True)
        .or_(f"last_featured_at.is.null,last_featured_at.lt.{cutoff}")
        .order("score", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def mark_properties_featured(ids: list[str]) -> None:
    client = get_client()
    now = datetime.now(timezone.utc).isoformat()
    for pid in ids:
        client.table("listings").update({"last_featured_at": now}).eq("id", pid).execute()


def generate_weekly_text(properties: list[dict]) -> str:
    if not properties:
        return ""

    listings_text = "\n".join([
        f"- {p.get('barrio', '?')}, {p.get('municipio', '?')}: "
        f"{p.get('precio_venta', '?')} € · {p.get('metros_cuadrados', '?')}m² · "
        f"Score {p.get('score', '?')}/100"
        for p in properties
    ])

    ai_client = anthropic.Anthropic()
    prompt = f"""Genera el informe semanal de oportunidades para el canal Telegram @inversorinformado.
Formato: encabezado con semana y año, luego las oportunidades en formato HTML Telegram (<b>, <i>).
Al final añade el footer: "💎 ¿Quieres análisis exclusivos? https://inversorinformado.vercel.app/login"
Máximo 10 líneas en total. Solo el texto, sin explicaciones.

Oportunidades de esta semana:
{listings_text}
"""
    response = ai_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def run_weekly_publish() -> dict:
    """Lógica principal del job. Puede ser llamada por el scheduler o manualmente."""
    log.info("weekly_publish_start")
    props = get_top_properties_for_weekly()
    if not props:
        log.warning("weekly_publish_no_properties")
        return {"status": "skipped", "reason": "No hay propiedades nuevas para publicar"}

    text = generate_weekly_text(props)
    if not text:
        return {"status": "skipped", "reason": "Claude no generó texto"}

    ok = publish_to_channel(text)
    status = "sent" if ok else "failed"

    client = get_client()
    client.table("telegram_log").insert({
        "type": "auto",
        "content": text,
        "report_id": None,
        "status": status,
    }).execute()

    if ok:
        mark_properties_featured([str(p["id"]) for p in props])
        log.info("weekly_publish_done", extra={"count": len(props)})
    else:
        log.error("weekly_publish_telegram_failed")

    return {"status": status, "properties_featured": len(props), "preview": text[:120]}


def init_scheduler(app) -> None:
    """Inicializa APScheduler y registra el job lunes+jueves a las 10:00."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="Europe/Madrid")
    scheduler.add_job(
        run_weekly_publish,
        trigger="cron",
        day_of_week="mon,thu",
        hour=10,
        minute=0,
        id="weekly_publish",
        replace_existing=True,
    )
    scheduler.start()
    log.info("scheduler_started")

    import atexit
    atexit.register(lambda: scheduler.shutdown(wait=False))

from __future__ import annotations

import os

import anthropic

from scraper.infrastructure.db import get_client
from scraper.services.alerts import publish_to_channel

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://inversorinformado.vercel.app")


def get_log() -> list[dict]:
    client = get_client()
    res = (
        client.table("telegram_log")
        .select("*")
        .order("sent_at", desc=True)
        .limit(100)
        .execute()
    )
    return res.data or []


def publish_report_summary(report_id: str, report: dict) -> str:
    """Genera resumen del informe con Claude y lo publica en el canal. Devuelve el texto."""
    data = report["data"]
    p = data.get("property", {})
    m = data.get("market", {})
    s = data.get("scores", {})

    ai_client = anthropic.Anthropic()
    prompt = (
        f"Genera un mensaje corto para el canal de Telegram @inversorinformado sobre este análisis de inversión.\n"
        f"El mensaje debe tener: emoji 📊, barrio y municipio, precio, precio/m², rentabilidad bruta, score global.\n"
        f"Al final añade: \"👉 Análisis completo: {FRONTEND_URL}/login\"\n"
        f"Máximo 5 líneas. Usa HTML de Telegram (<b>, <i>). Sin JSON, solo el texto del mensaje.\n\n"
        f"Datos:\n"
        f"- Dirección: {p.get('direccion', '?')}, {p.get('barrio', '?')}, {p.get('municipio', '?')}\n"
        f"- Precio: {p.get('precio', '?')} €\n"
        f"- Precio/m²: {round(p.get('precio', 0) / max(p.get('metros', 1), 1))} € "
        f"(media zona: {m.get('precio_m2_zona_medio', '?')} €)\n"
        f"- Rentabilidad bruta: {m.get('rentabilidad_bruta', '?')}%\n"
        f"- Score global: {s.get('global', '?')}/100 ({s.get('global_grade', '?')})\n"
    )

    response = ai_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    ok = publish_to_channel(text)
    if not ok:
        raise RuntimeError("Error publicando en Telegram")

    client = get_client()
    client.table("telegram_log").insert({
        "type": "from_report",
        "content": text,
        "report_id": report_id,
        "status": "sent",
    }).execute()

    return text

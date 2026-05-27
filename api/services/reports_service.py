from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Optional

import anthropic
from jinja2 import Environment, FileSystemLoader, select_autoescape

from scraper.infrastructure.db import get_client
from scraper.infrastructure.logger import get_logger

log = get_logger("reports_service")

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)

def _format_price(value):
    """Convierte 385000 → '385.000'"""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)

_jinja_env.filters["format_price"] = _format_price


def create_report(data: dict) -> dict:
    client = get_client()
    res = client.table("reports").insert(data).execute()
    return res.data[0]


def list_reports(report_type: Optional[str] = None) -> list[dict]:
    client = get_client()
    q = client.table("reports").select(
        "id, type, title, property_id, created_at, data"
    ).order("created_at", desc=True)
    if report_type:
        q = q.eq("type", report_type)
    res = q.execute()
    return res.data or []


def get_report(report_id: str) -> Optional[dict]:
    client = get_client()
    res = client.table("reports").select("*").eq("id", report_id).execute()
    if not res.data:
        return None
    return res.data[0]


def render_report_html(report: dict) -> str:
    data = report["data"]
    p = data.get("property", {})
    m = data.get("market", {})
    b = data.get("building", {})
    s = data.get("scores", {})
    a = data.get("amenities", {})

    precio_m2_piso = round(p.get("precio", 0) / max(p.get("metros", 1), 1))
    pos_pct = 0
    if m.get("precio_m2_zona_max", 0) > m.get("precio_m2_zona_min", 0):
        pos_pct = round(
            (precio_m2_piso - m["precio_m2_zona_min"])
            / (m["precio_m2_zona_max"] - m["precio_m2_zona_min"])
            * 100
        )
        pos_pct = max(0, min(100, pos_pct))

    descuento_vs_media = 0
    if m.get("precio_m2_zona_medio"):
        descuento_vs_media = round(
            (1 - precio_m2_piso / m["precio_m2_zona_medio"]) * 100, 1
        )

    demanda_pct_map = {"muy_alta": 87, "alta": 70, "media": 50, "baja": 30}
    demanda_label_map = {"muy_alta": "Muy alta", "alta": "Alta", "media": "Media", "baja": "Baja"}
    demanda_key = m.get("demanda_alquiler", "media")

    alquiler_media_bcn = 19
    dias = m.get("dias_hasta_alquiler", 19)
    velocidad_pct = round((1 - dias / alquiler_media_bcn) * 100) if dias < alquiler_media_bcn else 0

    alquiler_vs_media = m.get("alquiler_vs_media_pct", 0)

    template = _jinja_env.get_template("reports/analysis.html.j2")
    return template.render(
        report_tag=f"Informe de Análisis · {date.today().strftime('%B %Y').capitalize()} · Confidencial",
        report_title="Análisis de Mercado<br>&amp; Rentabilidad",
        fecha_generacion=date.today().strftime("%B %Y").capitalize(),
        current_year=datetime.now().year,
        p={**p, "cee": p.get("cee", "—")},
        m={
            **m,
            "precio_m2_piso": precio_m2_piso,
            "pos_pct_precio_m2": pos_pct,
            "descuento_vs_media": abs(descuento_vs_media),
            "percentil_precio": m.get("percentil_precio", 0),
            "demanda_pct": demanda_pct_map.get(demanda_key, 50),
            "demanda_label": demanda_label_map.get(demanda_key, "Media"),
            "alquiler_vs_media_pct": alquiler_vs_media,
            "velocidad_vs_media_pct": velocidad_pct,
            "rentabilidad_bruta_media_zona": m.get("rentabilidad_bruta_media_zona", 4.1),
            "rentabilidad_neta_media_zona": m.get("rentabilidad_neta_media_zona", 2.8),
            "media_dias_mercado": m.get("media_dias_mercado", 19),
        },
        b=b,
        s=s,
        a=a,
        data=data,
    )


async def render_report_pdf(report: dict) -> bytes:
    from playwright.async_api import async_playwright
    html = render_report_html(report)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf = await page.pdf(format="A4", print_background=True, margin={
            "top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"
        })
        await browser.close()
    return pdf

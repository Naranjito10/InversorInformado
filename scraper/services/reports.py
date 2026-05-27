"""Formateo y publicación de informes periódicos al canal de Telegram."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from .alerts import publish_to_channel
from ..infrastructure.logger import get_logger

log = get_logger("reports")


class ReportType(str, Enum):
    OPORTUNIDADES = "oportunidades"
    MERCADO = "mercado"
    ZONAS = "zonas"


_HEADERS = {
    ReportType.OPORTUNIDADES: "🏆 INFORME DE OPORTUNIDADES",
    ReportType.MERCADO: "📊 INFORME DE MERCADO",
    ReportType.ZONAS: "📍 INFORME DE ZONAS",
}

_FOOTERS = {
    ReportType.OPORTUNIDADES: "💎 ¿Quieres análisis exclusivos? Únete al canal premium.",
    ReportType.MERCADO: "📈 Accede a datos detallados por zona en el canal premium.",
    ReportType.ZONAS: "🔍 Análisis en profundidad disponibles en el canal premium.",
}


def _build_message(
    report_type: ReportType,
    title: str,
    body: str,
    zone: Optional[str] = None,
) -> str:
    week = date.today().isocalendar()[1]
    year = date.today().year
    header = _HEADERS[report_type]
    footer = _FOOTERS[report_type]
    zone_line = f"🗺 Zona: <b>{zone}</b>\n" if zone else ""

    return (
        f"{header} — Semana {week}/{year}\n"
        f"{'─' * 32}\n"
        f"{zone_line}"
        f"<b>{title}</b>\n\n"
        f"{body}\n\n"
        f"{'─' * 32}\n"
        f"{footer}"
    )


def publish_report(
    report_type: ReportType,
    title: str,
    body: str,
    zone: Optional[str] = None,
) -> bool:
    """Formatea y publica un informe en el canal público."""
    text = _build_message(report_type, title, body, zone)
    ok = publish_to_channel(text)
    if ok:
        log.info("report_published", extra={"type": report_type, "title": title})
    else:
        log.warning("report_not_published", extra={"type": report_type})
    return ok

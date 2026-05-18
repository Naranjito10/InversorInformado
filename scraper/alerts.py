"""Sistema de alertas: email (SMTP) y Telegram."""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from .config import config
from .logger import get_logger

log = get_logger("alerts")


def format_alert_message(listing: dict) -> str:
    """Formatea el mensaje estandar de alerta (texto plano / Telegram)."""
    score = listing.get("score") or 0
    barrio = listing.get("barrio") or "—"
    municipio = listing.get("municipio") or "—"
    precio = listing.get("precio_venta")
    precio_m2 = listing.get("precio_m2")
    metros = listing.get("metros_cuadrados") or "—"
    habs = listing.get("habitaciones") or "—"
    estado = listing.get("estado") or "—"
    rb = listing.get("rentabilidad_bruta")
    bajada = listing.get("bajada_precio")
    url = listing.get("url") or ""

    precio_fmt = f"{precio:,}".replace(",", ".") + " €" if precio else "—"
    precio_m2_fmt = f"{precio_m2:,}".replace(",", ".") + " €/m²" if precio_m2 else "—"
    rb_fmt = f"{rb}%" if rb else "—"

    bajada_line = "📉 ¡Precio bajado!\n" if bajada else ""

    return (
        f"🏠 NUEVA OPORTUNIDAD [score: {score}/100]\n"
        f"📍 Barrio: {barrio}, {municipio}\n"
        f"💶 Precio: {precio_fmt} ({precio_m2_fmt})\n"
        f"📐 {metros}m² · {habs}hab · {estado}\n"
        f"📈 Rentabilidad estimada: {rb_fmt}\n"
        f"{bajada_line}"
        f"🔗 {url}"
    )

def format_alert_html(listing: dict) -> str:
    """Version HTML para email."""
    score = listing.get("score") or 0
    color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 50 else "#94a3b8"
    barrio = listing.get("barrio") or "—"
    municipio = listing.get("municipio") or "—"
    precio = listing.get("precio_venta")
    precio_m2 = listing.get("precio_m2")
    metros = listing.get("metros_cuadrados") or "—"
    habs = listing.get("habitaciones") or "—"
    estado = listing.get("estado") or "—"
    rb = listing.get("rentabilidad_bruta")
    url = listing.get("url") or "#"
    bajada = listing.get("bajada_precio")

    precio_fmt = f"{precio:,}".replace(",", ".") + " €" if precio else "—"
    precio_m2_fmt = f"{precio_m2:,}".replace(",", ".") + " €/m²" if precio_m2 else "—"
    rb_fmt = f"{rb}%" if rb else "—"

    bajada_badge = (
        '<span style="background:#a855f7;color:white;padding:2px 8px;border-radius:4px;'
        'font-size:12px;margin-left:8px;">PRECIO BAJADO</span>' if bajada else ""
    )

    return f"""<!DOCTYPE html>
<html><body style="font-family: -apple-system, sans-serif; max-width:600px; margin:auto;">
  <div style="border-left:6px solid {color}; padding:16px 20px; background:#f8fafc;">
    <h2 style="margin:0 0 8px 0;">🏠 Oportunidad detectada
      <span style="background:{color};color:white;padding:4px 10px;border-radius:6px;font-size:14px;">
        Score {score}/100
      </span>
      {bajada_badge}
    </h2>
    <p><strong>📍 {barrio}, {municipio}</strong></p>
    <table style="width:100%; border-collapse: collapse;">
      <tr><td>💶 Precio</td><td><strong>{precio_fmt}</strong> ({precio_m2_fmt})</td></tr>
      <tr><td>📐 Superficie</td><td>{metros} m²</td></tr>
      <tr><td>🛏 Habitaciones</td><td>{habs}</td></tr>
      <tr><td>🔧 Estado</td><td>{estado}</td></tr>
      <tr><td>📈 Rentabilidad bruta</td><td><strong>{rb_fmt}</strong></td></tr>
    </table>
    <p style="margin-top:16px;">
      <a href="{url}" style="background:{color};color:white;padding:10px 20px;
         text-decoration:none;border-radius:6px;display:inline-block;">
        Ver anuncio →
      </a>
    </p>
  </div>
</body></html>"""


# ---------------------------------------------------------------------------
# Email (SMTP)
# ---------------------------------------------------------------------------

def send_email(subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
    """Envia un email via SMTP. Devuelve True si fue enviado."""
    if not config.email.enabled:
        log.debug("email_skipped_not_configured")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.email.from_addr
    msg["To"] = config.email.to_addr
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        context = ssl.create_default_context()
        if config.email.port == 465:
            with smtplib.SMTP_SSL(config.email.host, config.email.port, context=context) as s:
                s.login(config.email.user, config.email.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(config.email.host, config.email.port) as s:
                s.starttls(context=context)
                s.login(config.email.user, config.email.password)
                s.send_message(msg)
        log.info("email_sent", extra={"to": config.email.to_addr, "subject": subject})
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("email_failed", extra={"error": str(exc)})
        return False

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(text: str) -> bool:
    """Envia un mensaje a un chat de Telegram via Bot API."""
    if not config.telegram.enabled:
        log.debug("telegram_skipped_not_configured")
        return False

    try:
        import httpx
    except ImportError:
        log.error("httpx_not_installed_telegram_disabled")
        return False

    url = f"https://api.telegram.org/bot{config.telegram.bot_token}/sendMessage"
    payload = {
        "chat_id": config.telegram.chat_id,
        "text": text,
        "disable_web_page_preview": False,
        "parse_mode": "HTML",
    }
    try:
        r = httpx.post(url, json=payload, timeout=15)
        if r.status_code >= 400:
            log.error("telegram_failed", extra={"status": r.status_code, "body": r.text[:200]})
            return False
        log.info("telegram_sent", extra={"chat_id": config.telegram.chat_id})
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("telegram_failed", extra={"error": str(exc)})
        return False


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------

def notify_opportunity(listing: dict) -> None:
    """
    Envia notificacion para una oportunidad por todos los canales habilitados.

    Reglas (segun el prompt):
    - score_label == 'alto' (anuncio nuevo)
    - bajada_precio == true AND score >= ALERT_MIN_SCORE_PRICE_DROP
    """
    text = format_alert_message(listing)
    html = format_alert_html(listing)
    subject = (
        f"🏠 [{listing.get('score', 0)}/100] "
        f"{listing.get('barrio') or listing.get('municipio') or 'Oportunidad'} "
        f"— {listing.get('precio_venta', '—')} €"
    )

    send_email(subject, text, html)
    send_telegram(text)


def should_alert(listing: dict, was_new: bool = False) -> bool:
    """Decide si una vivienda merece alerta segun los thresholds configurados."""
    score = listing.get("score") or 0
    label = listing.get("score_label") or ""
    bajada = listing.get("bajada_precio") or False

    if was_new and label == "alto":
        return True
    if bajada and score >= config.alerts.min_score_price_drop:
        return True
    return False

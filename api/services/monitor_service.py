from __future__ import annotations

import time

import httpx

from scraper.infrastructure.db import get_client
from scraper.infrastructure.http_client import _is_blocked
from scraper.infrastructure.logger import get_logger

log = get_logger("monitor_service")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}


def get_test_url(portal: str) -> str | None:
    client = get_client()
    if client is None:
        return None
    resp = client.table("fuentes").select("test_url").eq("id", portal).limit(1).execute()
    if resp.data:
        return resp.data[0].get("test_url") or None
    return None


def _is_placeholder(html: str) -> bool:
    lower = html.lower()
    signals = [
        "will be constructed here",
        "something amazing will be constructed",
        "upload your website into the public_html",
        "under construction",
        "coming soon",
        "domain is parked",
        "this domain is for sale",
        "buy this domain",
        "site coming soon",
        "página en construcción",
        "sitio en construcción",
    ]
    return any(s in lower for s in signals)


def _estimate_listings(portal: str, html: str) -> int:
    try:
        if portal == "habitaclia":
            return html.count("list-item-title") or html.count("listingCard")
        if portal == "pisos":
            return html.count("ad-preview") or html.count("listing-item")
        if portal == "idealista":
            return html.count('"item "') or html.count("item-link")
        if portal == "fotocasa":
            return html.count("re-CardPackMain") or html.count("property-list-item")
    except Exception:
        log.warning("estimate_listings_failed", extra={"portal": portal})
    return 0


def test_portal(portal: str) -> dict:
    url = get_test_url(portal)
    if not url:
        return {
            "portal": portal,
            "status": "error",
            "detail": "Sin URL de test configurada para este portal",
        }

    t0 = time.perf_counter()
    try:
        with httpx.Client(headers=_HEADERS, timeout=15, follow_redirects=True) as client:
            r = client.get(url)

        elapsed = round((time.perf_counter() - t0) * 1000)
        html = r.text

        if r.status_code == 404:
            return {
                "portal": portal, "url": url, "status": "error",
                "detail": "URL no encontrada (404) — revisar la URL de test",
                "response_ms": elapsed, "listings_found": 0,
            }
        if r.status_code in (403, 429):
            return {
                "portal": portal, "url": url, "status": "blocked",
                "detail": f"Bloqueado por el servidor (HTTP {r.status_code})",
                "response_ms": elapsed, "listings_found": 0,
            }
        if r.status_code >= 400:
            return {
                "portal": portal, "url": url, "status": "error",
                "detail": f"HTTP {r.status_code}",
                "response_ms": elapsed, "listings_found": 0,
            }

        if _is_blocked(html):
            return {
                "portal": portal, "url": url, "status": "blocked",
                "detail": "Página de desafío detectada (DataDome / Cloudflare)",
                "response_ms": elapsed, "listings_found": 0,
            }

        if _is_placeholder(html):
            return {
                "portal": portal, "url": url, "status": "error",
                "detail": "Portal fuera de servicio — página en construcción o dominio aparcado",
                "response_ms": elapsed, "listings_found": 0,
            }

        count = _estimate_listings(portal, html)
        return {
            "portal": portal, "url": url, "status": "ok",
            "detail": f"{count} anuncios detectados" if count else "Conectado — sin anuncios detectados",
            "response_ms": elapsed, "listings_found": count,
        }

    except httpx.TimeoutException:
        elapsed = round((time.perf_counter() - t0) * 1000)
        return {
            "portal": portal, "url": url, "status": "error",
            "detail": "Timeout — el portal no respondió en 15 s",
            "response_ms": elapsed, "listings_found": 0,
        }
    except Exception as exc:
        elapsed = round((time.perf_counter() - t0) * 1000)
        return {
            "portal": portal, "url": url, "status": "error",
            "detail": str(exc), "response_ms": elapsed, "listings_found": 0,
        }

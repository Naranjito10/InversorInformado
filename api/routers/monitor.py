from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

ROOT = Path(__file__).resolve().parent.parent.parent


def _get_test_url(portal: str) -> str | None:
    from scraper.infrastructure.db import get_client
    client = get_client()
    if client is None:
        return None
    resp = client.table("fuentes").select("test_url").eq("id", portal).limit(1).execute()
    if resp.data:
        return resp.data[0].get("test_url") or None
    return None

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}


@router.post("/test/{portal}")
def test_portal(portal: str):
    """Prueba conectividad real con un portal: status HTTP + detección de bloqueo."""
    url = _get_test_url(portal.lower())
    if not url:
        return {"portal": portal, "status": "error", "detail": "Sin URL de test configurada para este portal"}

    from scraper.infrastructure.http_client import _is_blocked

    t0 = time.perf_counter()
    try:
        with httpx.Client(
            headers=_HEADERS, timeout=15, follow_redirects=True
        ) as client:
            r = client.get(url)

        elapsed = round((time.perf_counter() - t0) * 1000)
        html = r.text

        # 1. Error HTTP real (404, 500, etc.)
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

        # 2. Página de desafío sin error HTTP (DataDome, Cloudflare, etc.)
        if _is_blocked(html):
            return {
                "portal": portal, "url": url, "status": "blocked",
                "detail": "Página de desafío detectada (DataDome / Cloudflare)",
                "response_ms": elapsed, "listings_found": 0,
            }

        # 3. Página placeholder / dominio en construcción o aparcado
        if _is_placeholder(html):
            return {
                "portal": portal, "url": url, "status": "error",
                "detail": "Portal fuera de servicio — página en construcción o dominio aparcado",
                "response_ms": elapsed, "listings_found": 0,
            }

        # 4. OK — intentar estimar anuncios
        count = _estimate_listings(portal, html)
        return {
            "portal": portal, "url": url, "status": "ok",
            "detail": f"{count} anuncios detectados" if count else "Conectado — sin anuncios detectados",
            "response_ms": elapsed, "listings_found": count,
        }

    except httpx.TimeoutException:
        elapsed = round((time.perf_counter() - t0) * 1000)
        return {"portal": portal, "url": url, "status": "error",
                "detail": "Timeout — el portal no respondió en 15 s",
                "response_ms": elapsed, "listings_found": 0}
    except Exception as exc:
        elapsed = round((time.perf_counter() - t0) * 1000)
        return {"portal": portal, "url": url, "status": "error",
                "detail": str(exc), "response_ms": elapsed, "listings_found": 0}


def _is_placeholder(html: str) -> bool:
    """Detecta dominios aparcados, páginas en construcción o placeholders."""
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
    """Cuenta anuncios de forma heurística sin ejecutar el scraper completo."""
    try:
        if portal == "habitaclia":
            return html.count('list-item-title') or html.count('listingCard')
        if portal == "pisos":
            return html.count('ad-preview') or html.count('listing-item')
        if portal == "idealista":
            return html.count('"item "') or html.count('item-link')
        if portal == "fotocasa":
            return html.count('re-CardPackMain') or html.count('property-list-item')
    except Exception:
        pass
    return 0


@router.get("/logs")
def get_logs(lines: int = Query(50, le=500)):
    """Devuelve las últimas N entradas del log JSONL del scraper."""
    log_path = ROOT / "logs" / "scraper.jsonl"
    if not log_path.exists():
        return {"lines": [], "total": 0}

    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        all_lines = [l for l in content.splitlines() if l.strip()]
        last = all_lines[-lines:][::-1]  # más reciente primero
        parsed = []
        for line in last:
            try:
                parsed.append(json.loads(line))
            except Exception:
                parsed.append({"msg": line, "level": "RAW"})
        return {"lines": parsed, "total": len(all_lines)}
    except Exception as exc:
        return {"lines": [], "total": 0, "error": str(exc)}

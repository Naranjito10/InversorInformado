from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi import APIRouter, Query

from api.services.monitor_service import test_portal as _test_portal

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

ROOT = Path(__file__).resolve().parent.parent.parent


@router.post("/test/{portal}")
def test_portal(portal: str):
    """Prueba conectividad real con un portal: status HTTP + detección de bloqueo."""
    return _test_portal(portal.lower())


@router.get("/test-catastro-dnprc")
def test_catastro_dnprc(rc: str = "9319414DF2891G"):
    """Llama directamente al OVC DNPRC y devuelve la respuesta cruda para diagnóstico."""
    pc1 = rc[:7]
    pc2 = rc[7:14] if len(rc) >= 14 else ""
    url = (
        f"http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/"
        f"OVCCallejeroRC.asmx/Consulta_DNPRC"
        f"?Provincia=&Municipio=&RC.PC1={pc1}&RC.PC2={pc2}&RC.Car=&RC.CC1=&RC.CC2="
    )
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }
    try:
        with httpx.Client(follow_redirects=False, timeout=12) as client:
            resp = client.get(url, headers=headers)
        return {
            "url": url,
            "status": resp.status_code,
            "location": resp.headers.get("location", ""),
            "content_type": resp.headers.get("content-type", ""),
            "body": resp.text[:500],
        }
    except Exception as exc:
        return {"url": url, "error": str(exc)}


@router.get("/logs")
def get_logs(lines: int = Query(50, le=500)):
    """Devuelve las últimas N entradas del log JSONL del scraper."""
    log_path = ROOT / "logs" / "scraper.jsonl"
    if not log_path.exists():
        return {"lines": [], "total": 0}

    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        all_lines = [ln for ln in content.splitlines() if ln.strip()]
        last = all_lines[-lines:][::-1]
        parsed = []
        for line in last:
            try:
                parsed.append(json.loads(line))
            except Exception:
                parsed.append({"msg": line, "level": "RAW"})
        return {"lines": parsed, "total": len(all_lines)}
    except Exception as exc:
        return {"lines": [], "total": 0, "error": str(exc)}

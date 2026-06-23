from __future__ import annotations

import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
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
    """Prueba la URL confirmada de DNPRC y el XML completo de RCCOOR."""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
    headers_get = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }
    pc1 = rc[:7]
    pc2 = rc[7:14] if len(rc) >= 14 else rc[7:]
    candidates = [
        # Sede Electrónica — HTML scraping para año construcción y superficie
        ("sede_html", "GET", f"https://www1.sedecatastro.gob.es/CYCBienInmueble/OVCListaBienes.aspx?rc1={pc1}&rc2={pc2}", None, headers_get),
    ]

    results = []
    with httpx.Client(follow_redirects=False, timeout=12) as client:
        for name, method, url, body, hdrs in candidates:
            try:
                if method == "POST":
                    resp = client.post(url, content=body.encode(), headers=hdrs)
                else:
                    resp = client.get(url, headers=hdrs)
                soup = BeautifulSoup(resp.text, "lxml")
                text = soup.get_text(separator=" ", strip=True)
                results.append({
                    "test": name,
                    "url": url,
                    "status": resp.status_code,
                    "content_type": resp.headers.get("content-type", ""),
                    "text": text[:3000],
                })
            except Exception as exc:
                results.append({"test": name, "url": url, "error": str(exc)})

    return {"rc": rc, "results": results}


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

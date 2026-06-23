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
    """Prueba múltiples URLs del OVC DNPRC para encontrar cuál funciona."""
    pc1 = rc[:7]
    pc2 = rc[7:14] if len(rc) >= 14 else ""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
    headers_get = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }
    soap_body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soap:Body>"
        '<Consulta_DNPRC xmlns="http://www.catastro.meh.es/">'
        "<Provincia></Provincia><Municipio></Municipio>"
        f"<RC><PC1>{pc1}</PC1><PC2>{pc2}</PC2><Car></Car><CC1></CC1><CC2></CC2></RC>"
        "</Consulta_DNPRC>"
        "</soap:Body>"
        "</soap:Envelope>"
    )
    headers_soap = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://www.catastro.meh.es/Consulta_DNPRC",
        "User-Agent": ua,
    }

    candidates = [
        # WCF REST service en dominio antiguo (uppercase OVCServWeb)
        ("WCF_REST_old", "GET", f"http://ovc.catastro.meh.es/OVCServWeb/OVCWcfLibres/RESTServiceLibres.svc/Consulta_DNPRC_Libres_Rc?RC.PC1={pc1}&RC.PC2={pc2}&RC.Car=&RC.CC1=&RC.CC2=", None, headers_get),
        # CallejeroRC en Sede Electrónica — GET root
        ("sede_asmx_root", "GET", "https://www1.sedecatastro.gob.es/OVCServWeb/OVCSWLocalizacionRC/OVCCallejeroRC.asmx", None, headers_get),
        # CallejeroRC en Sede Electrónica — GET método
        ("sede_get_method", "GET", f"https://www1.sedecatastro.gob.es/OVCServWeb/OVCSWLocalizacionRC/OVCCallejeroRC.asmx/Consulta_DNPRC?Provincia=&Municipio=&RC.PC1={pc1}&RC.PC2={pc2}&RC.Car=&RC.CC1=&RC.CC2=", None, headers_get),
        # CallejeroRC en Sede Electrónica — SOAP POST
        ("sede_soap_post", "POST", "https://www1.sedecatastro.gob.es/OVCServWeb/OVCSWLocalizacionRC/OVCCallejeroRC.asmx", soap_body, headers_soap),
        # WCF REST en Sede Electrónica
        ("sede_wcf_rest", "GET", f"https://www1.sedecatastro.gob.es/OVCServWeb/OVCWcfLibres/RESTServiceLibres.svc/Consulta_DNPRC_Libres_Rc?RC.PC1={pc1}&RC.PC2={pc2}&RC.Car=&RC.CC1=&RC.CC2=", None, headers_get),
    ]

    results = []
    with httpx.Client(follow_redirects=False, timeout=12) as client:
        for name, method, url, body, hdrs in candidates:
            try:
                if method == "POST":
                    resp = client.post(url, content=body.encode(), headers=hdrs)
                else:
                    resp = client.get(url, headers=hdrs)
                results.append({
                    "test": name,
                    "url": url,
                    "status": resp.status_code,
                    "location": resp.headers.get("location", ""),
                    "content_type": resp.headers.get("content-type", ""),
                    "body": resp.text[:200],
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

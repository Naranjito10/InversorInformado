# Informes & Comunicaciones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir sección Informes (análisis de inversión A4 por piso, generado con IA, descargable como PDF) y sección Comunicaciones (historial y gestión de publicaciones al canal de Telegram + auto-publicación semanal) al frontend y backend de InversorInformado.

**Architecture:** JSON estructurado guardado en Supabase → Jinja2 renderiza el template HTML → Playwright genera PDF. APScheduler embebido en FastAPI ejecuta publicación automática los lunes y jueves. Frontend en React/Vite con Tailwind + React Query siguiendo patrones existentes.

**Tech Stack:** FastAPI, Supabase (supabase-py, `get_client()` de `scraper.infrastructure.db`), Jinja2, Playwright (disponible vía scrapling[all]), APScheduler (ya en requirements.txt), Anthropic SDK, React, TypeScript, Tailwind CSS, React Query, axios.

**Spec:** `docs/superpowers/specs/2026-05-27-informes-comunicaciones-design.md`

---

## Mapa de archivos

### Backend — nuevos
- `api/routers/reports.py` — CRUD reports + HTML/PDF endpoints
- `api/services/reports_service.py` — lógica: crear, listar, AI estimate, render HTML, render PDF
- `api/services/scheduler_service.py` — APScheduler: init, job lunes/jueves, generate_weekly
- `api/templates/reports/analysis.html.j2` — template Jinja2 portado desde `Templates_Informes/informe_inversion_piso.html`
- `tests/test_reports.py` — tests del router de reports

### Backend — modificados
- `api/routers/telegram.py` — añadir `/log`, `/publish-report/:id`, `/generate-weekly`
- `api/main.py` — registrar reports router + iniciar scheduler
- `requirements.txt` — añadir `anthropic`, `jinja2`

### Frontend — nuevos
- `frontend/src/pages/Informes.tsx` — listado de reports
- `frontend/src/pages/InformeNuevo.tsx` — formulario creación (selector piso + form + AI estimate)
- `frontend/src/pages/InformeDetalle.tsx` — vista informe (HTML preview + PDF + publicar)
- `frontend/src/pages/Comunicaciones.tsx` — Telegram hub (historial + compose + scheduler)

### Frontend — modificados
- `frontend/src/services/api.ts` — nuevas funciones para reports y telegram log
- `frontend/src/types/index.ts` — tipos Report, TelegramLogEntry
- `frontend/src/App.tsx` — nuevas rutas + nav links

---

## Task 1: Schema DB + dependencias

**Files:**
- Modify: `requirements.txt`

- [ ] **Añadir dependencias**

Editar `requirements.txt`, añadir debajo de `# Webhook server`:
```
# Reports
anthropic>=0.28.0
jinja2>=3.1.4
```

- [ ] **Instalar**
```bash
pip install anthropic>=0.28.0 jinja2>=3.1.4
```

- [ ] **Crear tablas en Supabase**

Ir al dashboard de Supabase → SQL Editor → ejecutar:

```sql
-- Tabla reports
CREATE TABLE IF NOT EXISTS reports (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type        TEXT NOT NULL DEFAULT 'analysis',
  title       TEXT NOT NULL,
  property_id UUID REFERENCES listings(id) ON DELETE SET NULL,
  data        JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Tabla telegram_log
CREATE TABLE IF NOT EXISTS telegram_log (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type      TEXT NOT NULL,
  content   TEXT NOT NULL,
  report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
  status    TEXT NOT NULL DEFAULT 'sent',
  sent_at   TIMESTAMPTZ DEFAULT now()
);

-- Campo last_featured_at en listings
ALTER TABLE listings ADD COLUMN IF NOT EXISTS last_featured_at TIMESTAMPTZ;
```

- [ ] **Commit**
```bash
git add requirements.txt
git commit -m "feat: add anthropic and jinja2 dependencies for reports"
```

---

## Task 2: Template Jinja2

**Files:**
- Create: `api/templates/reports/analysis.html.j2`

- [ ] **Crear directorio de templates**
```bash
mkdir -p api/templates/reports
```

- [ ] **Portar el template HTML a Jinja2**

Copiar `Templates_Informes/informe_inversion_piso.html` a `api/templates/reports/analysis.html.j2` y reemplazar todos los valores hardcodeados con variables Jinja2. El archivo fuente tiene ~690 líneas; a continuación están todos los reemplazos necesarios:

```
# COVER
"Informe de Análisis · Mayo 2026 · Confidencial"  →  {{ report_tag }}
"Análisis de Mercado<br>&amp; Rentabilidad"        →  {{ report_title }}
"Calle Provença 214, 3º 1ª · Barcelona, Eixample Dret · 08008"  →  {{ p.direccion }} · {{ p.municipio }}, {{ p.barrio }}

# COVER STATS
"385.000 €"        →  {{ p.precio | format_price }} €
"93 m² · 3 hab. · 1 baño"  →  {{ p.metros }} m² · {{ p.habitaciones }} hab. · {{ p.banos }} baño(s)
"4.140 €"          →  {{ m.precio_m2_piso | int }} €
"Media zona: 4.580 €/m²"  →  Media zona: {{ m.precio_m2_zona_medio | int }} €/m²
"5,4%"             →  {{ m.rentabilidad_bruta }}%
"Media zona: 4,1%"  →  Media zona: {{ m.rentabilidad_bruta_media_zona }}%

# VERDICT BAR
"Valoración general: ..."  →  <strong style="color:#fff">Valoración general:</strong> {{ data.verdict }}

# MARKET POSITION - precio por m² bar
left: {{ m.pos_pct_precio_m2 }}%   (calculado: (precio_m2_piso - precio_m2_min) / (precio_m2_max - precio_m2_min) * 100)
"Mín. 3.200 €"   →  Mín. {{ m.precio_m2_zona_min | int }} €
"Media 4.580 €"  →  Media {{ m.precio_m2_zona_medio | int }} €
"Máx. 5.900 €"   →  Máx. {{ m.precio_m2_zona_max | int }} €
"Este piso: 4.140 €/m² · Top 38% más barato"  →  Este piso: {{ m.precio_m2_piso | int }} €/m² · Top {{ m.percentil_precio }}% más barato
"Un precio 9,6% inferior"  →  Un precio {{ m.descuento_vs_media }}% inferior a la media del {{ p.barrio }}

# RENTAL ANALYSIS
"1.750 €"  →  {{ m.alquiler_estimado_mes | int }} €
"+12% vs. media barrio"  →  {{ m.alquiler_vs_media_pct }}% vs. media barrio
"5,4%"     →  {{ m.rentabilidad_bruta }}%
"21.000 € / año estimados"  →  {{ (m.alquiler_estimado_mes * 12) | int }} € / año estimados
"Media zona: 4,1%"  →  Media zona: {{ m.rentabilidad_bruta_media_zona }}%
"3,9%"     →  {{ m.rentabilidad_neta }}%
"Media zona: 2,8%"  →  Media zona: {{ m.rentabilidad_neta_media_zona }}%

# RENTAL DEMAND
"Muy alta · Eixample Dret"  →  {{ m.demanda_label }} · {{ p.barrio }}
width demand-fill: 87%   →  {{ m.demanda_pct }}%
"8 días"   →  {{ m.dias_hasta_alquiler }} días
"8 días"   →  {{ m.dias_hasta_alquiler }} días
"57% más rápido"  →  {{ m.velocidad_vs_media_pct }}% más rápido

# BUILDING RISKS
"1972 (54 años)"  →  {{ b.anyo_construccion }} ({{ 2026 - b.anyo_construccion }} años)
"Favorable · 2023"  →  {{ b.ite_resultado | title }} · {{ b.ite_fecha }}
"No detectadas"  →  {{ "No detectadas" if not b.humedades else "Detectadas" }}
"Sí · Revisado 2025"  →  {{ "Sí" if b.ascensor else "No" }}
"Parcialmente renovada"  →  {{ b.electrica }}
"Calificación D"  →  Calificación {{ p.cee if p.cee else "—" }}
"28.400 € · Adecuado"  →  {{ b.fondo_reserva | format_price }} € · {{ b.fondo_reserva_estado }}
alert-box text  →  {{ b.alerta_reformas }}

# AMENITIES
9.2  →  {{ a.transporte }}
8.7  →  {{ a.colegios }}
8.4  →  {{ a.salud }}
9.5  →  {{ a.comercios }}
6.1  →  {{ a.zonas_verdes }}
8.0  →  {{ a.seguridad }}
8.9  →  {{ a.ambiente }}
5.8  →  {{ a.aparcamiento }}
info-box text  →  {{ a.descripcion_cercano }}

# SCORES
"77"  →  {{ s.global }}
"B+"  →  {{ s.global_grade }}
"85"  →  {{ s.precio }}
"A"   →  {{ s.precio_grade }}
"81"  →  {{ s.rentabilidad }}
"A−"  →  {{ s.rentabilidad_grade }}
"63"  →  {{ s.edificio }}
"C+"  →  {{ s.edificio_grade }}
"88"  →  {{ s.vecindario }}
"A"   →  {{ s.vecindario_grade }}
resumen text  →  {{ s.resumen }}

# PERCENTILES en score rings
"Top 15%"  →  Top {{ s.percentil_precio }}%
"Top 22%"  →  Top {{ s.percentil_rentabilidad }}%
"Top 12%"  →  Top {{ s.percentil_vecindario }}%

# FOOTER
"Mayo 2026"  →  {{ fecha_generacion }}
```

Al inicio del archivo `.j2`, añadir el filtro personalizado en un bloque comentado (se aplica en Python, no en el template):
```
{# Filtro format_price: convierte 385000 → "385.000" — registrado en el entorno Jinja2 #}
```

- [ ] **Commit**
```bash
git add api/templates/
git commit -m "feat: add Jinja2 report template ported from HTML"
```

---

## Task 3: Reports service (CRUD + render)

**Files:**
- Create: `api/services/reports_service.py`
- Create: `tests/test_reports.py` (parcial)

- [ ] **Escribir el test primero**

Crear `tests/test_reports.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


def make_report_data():
    return {
        "type": "analysis",
        "title": "Test Eixample",
        "property_id": None,
        "data": {
            "property": {"direccion": "Calle Test 1", "municipio": "Barcelona",
                         "barrio": "Eixample", "precio": 300000, "metros": 80,
                         "habitaciones": 3, "banos": 1, "estado": "buen estado",
                         "url": "https://example.com", "cee": "D"},
            "market": {"precio_m2_zona_min": 3000, "precio_m2_zona_medio": 4000,
                       "precio_m2_zona_max": 5000, "alquiler_estimado_mes": 1500,
                       "rentabilidad_bruta": 6.0, "rentabilidad_neta": 4.2,
                       "rentabilidad_bruta_media_zona": 4.5,
                       "rentabilidad_neta_media_zona": 3.0,
                       "demanda_alquiler": "alta", "dias_hasta_alquiler": 12,
                       "ai_estimated": True},
            "building": {"anyo_construccion": 1980, "ite_resultado": "favorable",
                         "ite_fecha": "2022", "humedades": False, "ascensor": True,
                         "electrica": "renovada", "fondo_reserva": 20000,
                         "fondo_reserva_estado": "Adecuado",
                         "alerta_reformas": "Sin reformas urgentes."},
            "scores": {"global": 80, "global_grade": "A-", "precio": 82,
                       "precio_grade": "A", "rentabilidad": 85,
                       "rentabilidad_grade": "A", "edificio": 70,
                       "edificio_grade": "B+", "vecindario": 78,
                       "vecindario_grade": "B+", "resumen": "Buena oportunidad.",
                       "percentil_precio": 18, "percentil_rentabilidad": 15,
                       "percentil_vecindario": 22},
            "amenities": {"transporte": 8.5, "colegios": 7.0, "salud": 8.0,
                          "comercios": 9.0, "zonas_verdes": 6.5, "seguridad": 7.5,
                          "ambiente": 8.0, "aparcamiento": 5.0,
                          "descripcion_cercano": "Metro a 5 min."},
            "verdict": "Buena oportunidad de inversión."
        }
    }


def test_create_report_returns_id():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "abc-123", **make_report_data()}
    ]
    with patch("api.services.reports_service.get_client", return_value=mock_client):
        from api.services.reports_service import create_report
        result = create_report(make_report_data())
    assert result["id"] == "abc-123"


def test_list_reports_returns_list():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"id": "abc-123", "title": "Test", "type": "analysis", "created_at": "2026-01-01"}
    ]
    with patch("api.services.reports_service.get_client", return_value=mock_client):
        from api.services.reports_service import list_reports
        result = list_reports()
    assert len(result) == 1
    assert result[0]["id"] == "abc-123"


def test_get_report_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    with patch("api.services.reports_service.get_client", return_value=mock_client):
        from api.services.reports_service import get_report
        result = get_report("nonexistent-id")
    assert result is None
```

- [ ] **Ejecutar tests (deben fallar)**
```bash
pytest tests/test_reports.py -v
```
Expected: `ImportError` o `ModuleNotFoundError` (el módulo no existe aún)

- [ ] **Crear `api/services/reports_service.py`**

```python
from __future__ import annotations

import os
from datetime import date
from typing import Optional

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
        "id, type, title, property_id, created_at, data->scores->global"
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

    precio_m2_piso = round(p.get("precio", 0) / p.get("metros", 1))
    pos_pct = 0
    if m.get("precio_m2_zona_max", 0) > m.get("precio_m2_zona_min", 0):
        pos_pct = round(
            (precio_m2_piso - m["precio_m2_zona_min"])
            / (m["precio_m2_zona_max"] - m["precio_m2_zona_min"])
            * 100
        )

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
        report_tag=f"Informe de Análisis · {date.today().strftime('%B %Y')} · Confidencial",
        report_title="Análisis de Mercado<br>&amp; Rentabilidad",
        fecha_generacion=date.today().strftime("%B %Y"),
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
        },
        b=b,
        s=s,
        a=a,
    )


async def render_report_pdf(report: dict) -> bytes:
    from playwright.async_api import async_playwright
    html = render_report_html(report)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf = await page.pdf(format="A4", print_background=True, margin={
            "top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"
        })
        await browser.close()
    return pdf
```

- [ ] **Ejecutar tests**
```bash
pytest tests/test_reports.py -v
```
Expected: 3 tests PASS

- [ ] **Commit**
```bash
git add api/services/reports_service.py tests/test_reports.py
git commit -m "feat: add reports service (CRUD + HTML/PDF render)"
```

---

## Task 4: AI estimate endpoint (Anthropic)

**Files:**
- Modify: `api/services/reports_service.py`
- Modify: `tests/test_reports.py`

- [ ] **Añadir test para AI estimate**

Añadir al final de `tests/test_reports.py`:
```python
def test_ai_estimate_returns_market_data():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"precio_m2_zona_min": 3200, "precio_m2_zona_medio": 4500, "precio_m2_zona_max": 5800, "alquiler_estimado_mes": 1600, "rentabilidad_bruta": 5.5, "rentabilidad_neta": 3.8, "rentabilidad_bruta_media_zona": 4.2, "rentabilidad_neta_media_zona": 2.9, "demanda_alquiler": "alta", "dias_hasta_alquiler": 10, "alquiler_vs_media_pct": 8, "percentil_precio": 25, "percentil_rentabilidad": 20, "percentil_vecindario": 30, "verdict": "Buena oportunidad."}')]

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create.return_value = mock_response

    with patch("api.services.reports_service.anthropic.Anthropic", return_value=mock_anthropic):
        from api.services.reports_service import ai_estimate_market
        result = ai_estimate_market({
            "municipio": "Barcelona", "barrio": "Eixample",
            "precio": 385000, "metros": 93, "habitaciones": 3, "estado": "buen estado"
        })
    assert result["precio_m2_zona_medio"] == 4500
    assert result["demanda_alquiler"] == "alta"
```

- [ ] **Ejecutar test (debe fallar)**
```bash
pytest tests/test_reports.py::test_ai_estimate_returns_market_data -v
```

- [ ] **Añadir `ai_estimate_market` a `api/services/reports_service.py`**

Añadir al inicio del archivo, junto a los otros imports:
```python
import json
import anthropic
```

Añadir la función al final del archivo:
```python
def ai_estimate_market(property_data: dict) -> dict:
    """Llama a Claude para obtener estimados de datos de mercado de un piso."""
    client = anthropic.Anthropic()

    prompt = f"""Eres un experto en mercado inmobiliario español.
Dado este piso, proporciona estimaciones del mercado inmobiliario local en formato JSON.
Datos del piso:
- Municipio: {property_data.get('municipio', '?')}
- Barrio: {property_data.get('barrio', '?')}
- Precio: {property_data.get('precio', '?')} €
- Metros: {property_data.get('metros', '?')} m²
- Habitaciones: {property_data.get('habitaciones', '?')}
- Estado: {property_data.get('estado', '?')}

Devuelve ÚNICAMENTE JSON válido con estos campos (sin markdown, sin explicaciones):
{{
  "precio_m2_zona_min": <int €/m²>,
  "precio_m2_zona_medio": <int €/m²>,
  "precio_m2_zona_max": <int €/m²>,
  "alquiler_estimado_mes": <int €/mes para piso similar>,
  "rentabilidad_bruta": <float %>,
  "rentabilidad_neta": <float %>,
  "rentabilidad_bruta_media_zona": <float %>,
  "rentabilidad_neta_media_zona": <float %>,
  "demanda_alquiler": <"muy_alta"|"alta"|"media"|"baja">,
  "dias_hasta_alquiler": <int días>,
  "alquiler_vs_media_pct": <int % diferencia vs media barrio>,
  "percentil_precio": <int top X% más barato>,
  "percentil_rentabilidad": <int top X%>,
  "percentil_vecindario": <int top X%>,
  "verdict": <string 2 frases evaluando la oportunidad>
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Claude no devolvió JSON válido: {raw[:200]}")
```

- [ ] **Ejecutar tests**
```bash
pytest tests/test_reports.py -v
```
Expected: 4 tests PASS

- [ ] **Commit**
```bash
git add api/services/reports_service.py tests/test_reports.py
git commit -m "feat: add AI market estimate via Claude"
```

---

## Task 5: Reports router

**Files:**
- Create: `api/routers/reports.py`

- [ ] **Crear `api/routers/reports.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from typing import Optional

from api.services.reports_service import (
    create_report, list_reports, get_report,
    render_report_html, render_report_pdf, ai_estimate_market,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


class CreateReportRequest(BaseModel):
    type: str = "analysis"
    title: str
    property_id: Optional[str] = None
    data: dict


class AIEstimateRequest(BaseModel):
    municipio: str
    barrio: str
    precio: int
    metros: int
    habitaciones: int
    estado: str


@router.get("")
def get_reports(type: Optional[str] = None):
    return list_reports(report_type=type)


@router.post("")
def post_report(req: CreateReportRequest):
    return create_report(req.model_dump())


@router.get("/{report_id}")
def get_report_detail(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return report


@router.get("/{report_id}/html", response_class=HTMLResponse)
def get_report_html(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    html = render_report_html(report)
    return HTMLResponse(content=html)


@router.get("/{report_id}/pdf")
async def get_report_pdf(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    pdf_bytes = await render_report_pdf(report)
    slug = report.get("title", "informe").lower().replace(" ", "-")[:40]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
    )


@router.post("/ai-estimate")
def post_ai_estimate(req: AIEstimateRequest):
    try:
        return ai_estimate_market(req.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error llamando a Claude: {exc}")
```

- [ ] **Registrar el router en `api/main.py`**

Modificar el bloque de imports:
```python
from api.routers import listings, scraper, export, zones, monitor, auth, fuentes, telegram, reports
```

Añadir debajo de `app.include_router(telegram.router, **_protected)`:
```python
app.include_router(reports.router, **_protected)
```

- [ ] **Verificar que la API arranca**
```bash
uvicorn api.main:app --reload
```
Abrir http://localhost:8000/docs y verificar que aparece la sección "reports" con todos los endpoints.

- [ ] **Commit**
```bash
git add api/routers/reports.py api/main.py
git commit -m "feat: add reports router with CRUD, HTML, PDF and AI estimate endpoints"
```

---

## Task 6: Telegram — log + publish-report

**Files:**
- Modify: `api/routers/telegram.py`

- [ ] **Añadir endpoints al router de Telegram**

Abrir `api/routers/telegram.py` y añadir al final (después del endpoint `/status` existente):

```python
# ── Nuevos imports al inicio del archivo (añadir a los existentes) ──────────
# from scraper.infrastructure.db import get_client
# import anthropic, json

@router.get("/log")
def get_telegram_log():
    """Historial de mensajes enviados al canal."""
    from scraper.infrastructure.db import get_client
    client = get_client()
    res = client.table("telegram_log").select("*").order("sent_at", desc=True).limit(100).execute()
    return res.data or []


@router.post("/publish-report/{report_id}")
def publish_report_to_telegram(report_id: str):
    """Genera resumen del informe con Claude y lo publica en el canal."""
    import anthropic, json
    from scraper.infrastructure.db import get_client
    from api.services.reports_service import get_report

    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    data = report["data"]
    p = data.get("property", {})
    m = data.get("market", {})
    s = data.get("scores", {})

    ai_client = anthropic.Anthropic()
    prompt = f"""Genera un mensaje corto para el canal de Telegram @inversorinformado sobre este análisis de inversión.
El mensaje debe tener: emoji 📊, barrio y municipio, precio, precio/m², rentabilidad bruta, score global.
Al final añade: "👉 Análisis completo: https://inversorinformado.vercel.app/login"
Máximo 5 líneas. Usa HTML de Telegram (<b>, <i>). Sin JSON, solo el texto del mensaje.

Datos:
- Dirección: {p.get('direccion', '?')}, {p.get('barrio', '?')}, {p.get('municipio', '?')}
- Precio: {p.get('precio', '?')} €
- Precio/m²: {round(p.get('precio', 0) / max(p.get('metros', 1), 1))} € (media zona: {m.get('precio_m2_zona_medio', '?')} €)
- Rentabilidad bruta: {m.get('rentabilidad_bruta', '?')}%
- Score global: {s.get('global', '?')}/100 ({s.get('global_grade', '?')})
"""
    response = ai_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    ok = publish_to_channel(text)
    if not ok:
        raise HTTPException(status_code=502, detail="Error publicando en Telegram")

    db_client = get_client()
    db_client.table("telegram_log").insert({
        "type": "from_report",
        "content": text,
        "report_id": report_id,
        "status": "sent",
    }).execute()

    return {"status": "published", "preview": text[:100]}


@router.post("/generate-weekly")
def generate_weekly_report():
    """Genera y publica el informe semanal automático (también llamado por el scheduler)."""
    from api.services.scheduler_service import run_weekly_publish
    result = run_weekly_publish()
    return result
```

Añadir al inicio de `api/routers/telegram.py` el import que falta:
```python
from scraper.services.alerts import publish_to_channel
```
(ya debería estar, verificar que está importado)

- [ ] **Verificar endpoints en Swagger**
```bash
uvicorn api.main:app --reload
```
Confirmar `/api/telegram/log`, `/api/telegram/publish-report/{id}`, `/api/telegram/generate-weekly` aparecen en http://localhost:8000/docs

- [ ] **Commit**
```bash
git add api/routers/telegram.py
git commit -m "feat: add telegram log, publish-report and generate-weekly endpoints"
```

---

## Task 7: Scheduler service

**Files:**
- Create: `api/services/scheduler_service.py`

- [ ] **Crear `api/services/scheduler_service.py`**

```python
from __future__ import annotations

import json
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
        f"- {p.get('barrio','?')}, {p.get('municipio','?')}: "
        f"{p.get('precio_venta','?')} € · {p.get('metros_cuadrados','?')}m² · "
        f"Score {p.get('score','?')}/100"
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
    log.info("scheduler_started", extra={"jobs": ["weekly_publish mon,thu 10:00"]})

    import atexit
    atexit.register(lambda: scheduler.shutdown(wait=False))
```

- [ ] **Iniciar el scheduler en `api/main.py`**

Añadir al final del archivo, después del último `include_router`:

```python
# Iniciar scheduler (lunes + jueves 10:00 → publicación automática Telegram)
from api.services.scheduler_service import init_scheduler
init_scheduler(app)
```

- [ ] **Verificar que la app arranca sin errores**
```bash
uvicorn api.main:app --reload
```
Confirmar en los logs: `scheduler_started`

- [ ] **Commit**
```bash
git add api/services/scheduler_service.py api/main.py
git commit -m "feat: add APScheduler for weekly Telegram auto-publish (mon+thu 10:00)"
```

---

## Task 8: Frontend — tipos y funciones API

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`

- [ ] **Añadir tipos en `frontend/src/types/index.ts`**

Añadir al final del archivo:
```typescript
export interface ReportProperty {
  direccion: string;
  municipio: string;
  barrio: string;
  precio: number;
  metros: number;
  habitaciones: number;
  banos: number;
  estado: string;
  url: string;
  cee?: string;
}

export interface ReportMarket {
  precio_m2_zona_min: number;
  precio_m2_zona_medio: number;
  precio_m2_zona_max: number;
  alquiler_estimado_mes: number;
  rentabilidad_bruta: number;
  rentabilidad_neta: number;
  rentabilidad_bruta_media_zona: number;
  rentabilidad_neta_media_zona: number;
  demanda_alquiler: "muy_alta" | "alta" | "media" | "baja";
  dias_hasta_alquiler: number;
  ai_estimated?: boolean;
  alquiler_vs_media_pct?: number;
  percentil_precio?: number;
  percentil_rentabilidad?: number;
  percentil_vecindario?: number;
}

export interface ReportBuilding {
  anyo_construccion?: number;
  ite_resultado?: string;
  ite_fecha?: string;
  humedades?: boolean;
  ascensor?: boolean;
  electrica?: string;
  fondo_reserva?: number;
  fondo_reserva_estado?: string;
  alerta_reformas?: string;
}

export interface ReportScores {
  global: number;
  global_grade: string;
  precio: number;
  precio_grade: string;
  rentabilidad: number;
  rentabilidad_grade: string;
  edificio: number;
  edificio_grade: string;
  vecindario: number;
  vecindario_grade: string;
  resumen: string;
  percentil_precio?: number;
  percentil_rentabilidad?: number;
  percentil_vecindario?: number;
}

export interface ReportAmenities {
  transporte?: number;
  colegios?: number;
  salud?: number;
  comercios?: number;
  zonas_verdes?: number;
  seguridad?: number;
  ambiente?: number;
  aparcamiento?: number;
  descripcion_cercano?: string;
}

export interface ReportData {
  property: ReportProperty;
  market: ReportMarket;
  building: ReportBuilding;
  scores: ReportScores;
  amenities: ReportAmenities;
  verdict: string;
}

export interface Report {
  id: string;
  type: string;
  title: string;
  property_id: string | null;
  data: ReportData;
  created_at: string;
}

export interface TelegramLogEntry {
  id: string;
  type: "manual" | "auto" | "from_report";
  content: string;
  report_id: string | null;
  status: "sent" | "failed";
  sent_at: string;
}
```

- [ ] **Añadir funciones en `frontend/src/services/api.ts`**

Añadir al final del archivo:
```typescript
// ── Reports ──────────────────────────────────────────────────────────────────

export interface ReportCreateIn {
  type?: string;
  title: string;
  property_id?: string | null;
  data: import("../types").ReportData;
}

export const fetchReports = async (): Promise<import("../types").Report[]> => {
  const { data } = await api.get<import("../types").Report[]>("/reports");
  return data;
};

export const createReport = async (
  payload: ReportCreateIn
): Promise<import("../types").Report> => {
  const { data } = await api.post<import("../types").Report>("/reports", payload);
  return data;
};

export const fetchReport = async (id: string): Promise<import("../types").Report> => {
  const { data } = await api.get<import("../types").Report>(`/reports/${id}`);
  return data;
};

export const getReportHtmlUrl = (id: string): string => `/api/reports/${id}/html`;
export const getReportPdfUrl = (id: string): string => `/api/reports/${id}/pdf`;

export const fetchReportHtmlBlob = async (id: string): Promise<string> => {
  const resp = await api.get(`/reports/${id}/html`, { responseType: "blob" });
  return URL.createObjectURL(resp.data);
};

export const downloadReportPdf = async (id: string, title: string): Promise<void> => {
  const resp = await api.get(`/reports/${id}/pdf`, { responseType: "blob" });
  const url = URL.createObjectURL(resp.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title.toLowerCase().replace(/\s+/g, "-")}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
};

export interface AIEstimateRequest {
  municipio: string;
  barrio: string;
  precio: number;
  metros: number;
  habitaciones: number;
  estado: string;
}

export const aiEstimateMarket = async (
  req: AIEstimateRequest
): Promise<import("../types").ReportMarket> => {
  const { data } = await api.post<import("../types").ReportMarket>("/reports/ai-estimate", req);
  return data;
};

// ── Telegram ─────────────────────────────────────────────────────────────────

export const fetchTelegramLog = async (): Promise<import("../types").TelegramLogEntry[]> => {
  const { data } = await api.get<import("../types").TelegramLogEntry[]>("/telegram/log");
  return data;
};

export const publishReportToTelegram = async (
  reportId: string
): Promise<{ status: string; preview: string }> => {
  const { data } = await api.post(`/telegram/publish-report/${reportId}`);
  return data;
};

export const generateWeeklyReport = async (): Promise<{
  status: string;
  properties_featured?: number;
  preview?: string;
}> => {
  const { data } = await api.post("/telegram/generate-weekly");
  return data;
};

export const publishTelegram = async (req: {
  type: string;
  title: string;
  body: string;
  zone?: string;
}): Promise<{ status: string; channel_id: string }> => {
  const { data } = await api.post("/telegram/publish", req);
  return data;
};
```

- [ ] **Verificar compilación**
```bash
cd frontend && npx tsc --noEmit
```
Expected: sin errores de tipos

- [ ] **Commit**
```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat: add Report and TelegramLogEntry types + API service functions"
```

---

## Task 9: Frontend — página Informes (listado)

**Files:**
- Create: `frontend/src/pages/Informes.tsx`

- [ ] **Crear `frontend/src/pages/Informes.tsx`**

```tsx
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchReports } from "../services/api";
import type { Report } from "../types";

function ScoreBadge({ score }: { score?: number }) {
  if (score === undefined || score === null) return null;
  const color =
    score >= 80 ? "bg-green-100 text-green-700" :
    score >= 60 ? "bg-yellow-100 text-yellow-700" :
    "bg-red-100 text-red-700";
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {score}/100
    </span>
  );
}

export default function Informes() {
  const navigate = useNavigate();
  const { data: reports = [], isLoading } = useQuery<Report[]>({
    queryKey: ["reports"],
    queryFn: fetchReports,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Informes de análisis</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Análisis de inversión generados para propiedades concretas
          </p>
        </div>
        <button
          onClick={() => navigate("/informes/nuevo")}
          className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Nuevo análisis
        </button>
      </div>

      {isLoading && (
        <p className="text-sm text-gray-400">Cargando informes...</p>
      )}

      {!isLoading && reports.length === 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center shadow-sm">
          <p className="text-gray-400 text-sm">Aún no hay informes generados.</p>
          <button
            onClick={() => navigate("/informes/nuevo")}
            className="mt-4 bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Crear el primero
          </button>
        </div>
      )}

      {reports.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Propiedad</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Ubicación</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Score</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports.map((r) => (
                <tr
                  key={r.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/informes/${r.id}`)}
                >
                  <td className="px-4 py-3 font-medium text-gray-900">{r.title}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {r.data?.property?.barrio}, {r.data?.property?.municipio}
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBadge score={r.data?.scores?.global} />
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(r.created_at).toLocaleDateString("es-ES")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Commit**
```bash
git add frontend/src/pages/Informes.tsx
git commit -m "feat: add Informes list page"
```

---

## Task 10: Frontend — página InformeNuevo

**Files:**
- Create: `frontend/src/pages/InformeNuevo.tsx`

- [ ] **Crear `frontend/src/pages/InformeNuevo.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchListings, createReport, aiEstimateMarket } from "../services/api";
import type { Listing } from "../types";
import type { ReportData, ReportMarket, ReportBuilding, ReportAmenities, ReportScores } from "../types";

const EMPTY_MARKET: ReportMarket = {
  precio_m2_zona_min: 0, precio_m2_zona_medio: 0, precio_m2_zona_max: 0,
  alquiler_estimado_mes: 0, rentabilidad_bruta: 0, rentabilidad_neta: 0,
  rentabilidad_bruta_media_zona: 0, rentabilidad_neta_media_zona: 0,
  demanda_alquiler: "media", dias_hasta_alquiler: 0, ai_estimated: false,
};

const EMPTY_SCORES: ReportScores = {
  global: 0, global_grade: "", precio: 0, precio_grade: "",
  rentabilidad: 0, rentabilidad_grade: "", edificio: 0, edificio_grade: "",
  vecindario: 0, vecindario_grade: "", resumen: "",
};

export default function InformeNuevo() {
  const navigate = useNavigate();
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [search, setSearch] = useState("");
  const [market, setMarket] = useState<ReportMarket>(EMPTY_MARKET);
  const [building, setBuilding] = useState<ReportBuilding>({});
  const [amenities, setAmenities] = useState<ReportAmenities>({});
  const [scores, setScores] = useState<ReportScores>(EMPTY_SCORES);
  const [verdict, setVerdict] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiEstimated, setAiEstimated] = useState(false);

  const { data: listings = [] } = useQuery<Listing[]>({
    queryKey: ["listings-search", search],
    queryFn: () => fetchListings({ limit: 20, ...(search ? { municipio: search } : {}) }),
    staleTime: 30_000,
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!selectedListing) throw new Error("Selecciona un piso");
      const data: ReportData = {
        property: {
          direccion: selectedListing.titulo ?? selectedListing.url,
          municipio: selectedListing.municipio ?? "",
          barrio: selectedListing.barrio ?? "",
          precio: selectedListing.precio_venta ?? 0,
          metros: selectedListing.metros_cuadrados ?? 0,
          habitaciones: selectedListing.habitaciones ?? 0,
          banos: selectedListing.banos ?? 0,
          estado: selectedListing.estado ?? "",
          url: selectedListing.url,
          cee: selectedListing.cee ?? undefined,
        },
        market,
        building,
        amenities,
        scores,
        verdict,
      };
      const title = `${data.property.barrio || data.property.municipio} · ${new Date().toLocaleDateString("es-ES")}`;
      return createReport({ title, property_id: selectedListing.id, data });
    },
    onSuccess: (report) => navigate(`/informes/${report.id}`),
  });

  const handleAiEstimate = async () => {
    if (!selectedListing) return;
    setAiLoading(true);
    try {
      const est = await aiEstimateMarket({
        municipio: selectedListing.municipio ?? "",
        barrio: selectedListing.barrio ?? "",
        precio: selectedListing.precio_venta ?? 0,
        metros: selectedListing.metros_cuadrados ?? 0,
        habitaciones: selectedListing.habitaciones ?? 0,
        estado: selectedListing.estado ?? "",
      });
      setMarket({ ...est, ai_estimated: true });
      if (est.verdict && !verdict) setVerdict(est.verdict as unknown as string);
      setAiEstimated(true);
    } catch {
      alert("Error al contactar con Claude. Verifica que ANTHROPIC_API_KEY está configurada.");
    } finally {
      setAiLoading(false);
    }
  };

  const setM = (k: keyof ReportMarket, v: unknown) =>
    setMarket((m) => ({ ...m, [k]: v }));

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Nuevo análisis</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Selecciona un piso del scraper y completa los datos de mercado
        </p>
      </div>

      {/* Paso 1: selección de piso */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
        <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
          1 · Seleccionar piso
        </p>
        <input
          placeholder="Buscar por municipio..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {listings.length > 0 && !selectedListing && (
          <div className="border border-gray-200 rounded-lg overflow-hidden max-h-52 overflow-y-auto">
            {listings.map((l) => (
              <button
                key={l.id}
                onClick={() => { setSelectedListing(l); setSearch(""); }}
                className="w-full text-left px-3 py-2.5 text-sm hover:bg-blue-50 border-b border-gray-100 last:border-0"
              >
                <span className="font-medium text-gray-900">{l.titulo ?? l.url}</span>
                <span className="text-gray-400 ml-2">
                  {l.barrio}, {l.municipio} · {l.precio_venta?.toLocaleString("es-ES")} €
                </span>
              </button>
            ))}
          </div>
        )}
        {selectedListing && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm flex justify-between items-center">
            <span className="font-medium text-blue-900">
              {selectedListing.titulo ?? selectedListing.url} —{" "}
              {selectedListing.precio_venta?.toLocaleString("es-ES")} €
            </span>
            <button
              onClick={() => setSelectedListing(null)}
              className="text-blue-400 hover:text-blue-700 ml-4"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Paso 2: datos de mercado */}
      {selectedListing && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
              2 · Datos de mercado
            </p>
            <button
              onClick={handleAiEstimate}
              disabled={aiLoading}
              className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              {aiLoading ? "Estimando..." : "✨ Estimar con IA"}
            </button>
          </div>
          {aiEstimated && (
            <p className="text-xs text-purple-600 bg-purple-50 px-3 py-1.5 rounded-lg">
              Datos pre-rellenados por Claude — revisa y ajusta si es necesario
            </p>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {([
              ["precio_m2_zona_min", "€/m² zona min"],
              ["precio_m2_zona_medio", "€/m² zona medio"],
              ["precio_m2_zona_max", "€/m² zona max"],
              ["alquiler_estimado_mes", "Alquiler estimado (€/mes)"],
              ["rentabilidad_bruta", "Rentabilidad bruta (%)"],
              ["rentabilidad_neta", "Rentabilidad neta (%)"],
              ["rentabilidad_bruta_media_zona", "Rent. bruta media zona (%)"],
              ["rentabilidad_neta_media_zona", "Rent. neta media zona (%)"],
              ["dias_hasta_alquiler", "Días hasta alquiler"],
            ] as [keyof ReportMarket, string][]).map(([k, label]) => (
              <div key={k} className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-gray-600">{label}</label>
                <input
                  type="number"
                  value={(market[k] as number) || ""}
                  onChange={(e) => setM(k, e.target.value ? Number(e.target.value) : 0)}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-gray-600">Demanda alquiler</label>
              <select
                value={market.demanda_alquiler}
                onChange={(e) => setM("demanda_alquiler", e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="muy_alta">Muy alta</option>
                <option value="alta">Alta</option>
                <option value="media">Media</option>
                <option value="baja">Baja</option>
              </select>
            </div>
          </div>

          {/* Veredicto */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-gray-600">Veredicto (2 frases)</label>
            <textarea
              rows={3}
              value={verdict}
              onChange={(e) => setVerdict(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Descripción general de la oportunidad..."
            />
          </div>

          {/* Scores */}
          <p className="font-semibold text-gray-700 text-xs uppercase tracking-wide mt-2">
            Puntuaciones (0–100)
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {([
              ["global", "Global"], ["precio", "Precio"],
              ["rentabilidad", "Rentab."], ["edificio", "Edificio"],
              ["vecindario", "Vecindario"],
            ] as [keyof ReportScores, string][]).map(([k, label]) => (
              <div key={k} className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">{label}</label>
                <input
                  type="number" min={0} max={100}
                  value={(scores[k] as number) || ""}
                  onChange={(e) =>
                    setScores((s) => ({ ...s, [k]: e.target.value ? Number(e.target.value) : 0 }))
                  }
                  className="border border-gray-300 rounded-lg px-2 py-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedListing && (
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="self-start bg-blue-600 text-white font-medium text-sm px-6 py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saveMutation.isPending ? "Guardando..." : "Guardar informe"}
        </button>
      )}

      {saveMutation.isError && (
        <p className="text-sm text-red-600">
          Error al guardar: {(saveMutation.error as Error).message}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Commit**
```bash
git add frontend/src/pages/InformeNuevo.tsx
git commit -m "feat: add InformeNuevo page with property selector and AI estimate"
```

---

## Task 11: Frontend — página InformeDetalle

**Files:**
- Create: `frontend/src/pages/InformeDetalle.tsx`

- [ ] **Crear `frontend/src/pages/InformeDetalle.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  fetchReport, fetchReportHtmlBlob, downloadReportPdf, publishReportToTelegram
} from "../services/api";
import type { Report } from "../types";

export default function InformeDetalle() {
  const { id } = useParams<{ id: string }>();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [published, setPublished] = useState(false);

  const { data: report, isLoading } = useQuery<Report>({
    queryKey: ["report", id],
    queryFn: () => fetchReport(id!),
    enabled: !!id,
  });

  useEffect(() => {
    if (!id) return;
    fetchReportHtmlBlob(id).then(setBlobUrl);
    return () => { if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [id]);

  const pdfMutation = useMutation({
    mutationFn: () => downloadReportPdf(id!, report?.title ?? "informe"),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishReportToTelegram(id!),
    onSuccess: () => setPublished(true),
  });

  if (isLoading || !report) {
    return <p className="text-sm text-gray-400">Cargando informe...</p>;
  }

  const { property, market, scores } = report.data;

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex-1">
          <h1 className="text-lg font-bold text-gray-900">{report.title}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {property.barrio}, {property.municipio} ·{" "}
            {property.precio?.toLocaleString("es-ES")} € ·{" "}
            {property.metros} m²
          </p>
          {market.ai_estimated && (
            <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded mt-1 inline-block">
              Datos de mercado estimados por IA
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {scores?.global > 0 && (
            <span className={`text-sm font-bold px-3 py-1 rounded-full ${
              scores.global >= 80 ? "bg-green-100 text-green-700" :
              scores.global >= 60 ? "bg-yellow-100 text-yellow-700" :
              "bg-red-100 text-red-700"
            }`}>
              {scores.global}/100 · {scores.global_grade}
            </span>
          )}
          <button
            onClick={() => pdfMutation.mutate()}
            disabled={pdfMutation.isPending}
            className="text-sm border border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {pdfMutation.isPending ? "Generando..." : "↓ PDF"}
          </button>
          <button
            onClick={() => {
              if (window.confirm("¿Publicar este informe en el canal de Telegram?")) {
                publishMutation.mutate();
              }
            }}
            disabled={publishMutation.isPending || published}
            className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {published ? "✓ Publicado" : publishMutation.isPending ? "Publicando..." : "Publicar en Telegram"}
          </button>
        </div>
      </div>

      {publishMutation.isSuccess && (
        <p className="text-sm text-green-600 bg-green-50 px-4 py-2 rounded-lg">
          Publicado en @inversorinformado. Preview: {publishMutation.data?.preview}
        </p>
      )}

      {/* HTML Preview */}
      {blobUrl ? (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <iframe
            src={blobUrl}
            title="Informe de análisis"
            className="w-full"
            style={{ height: "calc(297mm * 2 + 40px)", border: "none" }}
          />
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-xl h-96 flex items-center justify-center">
          <p className="text-sm text-gray-400">Cargando preview...</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Commit**
```bash
git add frontend/src/pages/InformeDetalle.tsx
git commit -m "feat: add InformeDetalle page with HTML preview, PDF download and Telegram publish"
```

---

## Task 12: Frontend — página Comunicaciones

**Files:**
- Create: `frontend/src/pages/Comunicaciones.tsx`

- [ ] **Crear `frontend/src/pages/Comunicaciones.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchTelegramLog, publishTelegram, generateWeeklyReport } from "../services/api";
import type { TelegramLogEntry } from "../types";

const TYPE_LABEL: Record<string, string> = {
  manual: "Manual",
  auto: "Auto",
  from_report: "Informe",
};

const TYPE_COLOR: Record<string, string> = {
  manual: "bg-blue-100 text-blue-700",
  auto: "bg-purple-100 text-purple-700",
  from_report: "bg-green-100 text-green-700",
};

export default function Comunicaciones() {
  const [form, setForm] = useState({ type: "oportunidades", title: "", body: "", zone: "" });
  const [preview, setPreview] = useState(false);

  const { data: log = [], refetch: refetchLog } = useQuery<TelegramLogEntry[]>({
    queryKey: ["telegram-log"],
    queryFn: fetchTelegramLog,
    refetchInterval: 30_000,
  });

  const publishMutation = useMutation({
    mutationFn: () =>
      publishTelegram({ type: form.type, title: form.title, body: form.body, zone: form.zone || undefined }),
    onSuccess: () => {
      setForm({ type: "oportunidades", title: "", body: "", zone: "" });
      setPreview(false);
      refetchLog();
    },
  });

  const weeklyMutation = useMutation({
    mutationFn: generateWeeklyReport,
    onSuccess: () => refetchLog(),
  });

  const previewText = `🏆 INFORME DE OPORTUNIDADES\n${"─".repeat(32)}\n${form.zone ? `🗺 Zona: ${form.zone}\n` : ""}<b>${form.title}</b>\n\n${form.body}`;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-gray-900">Comunicaciones</h1>

      {/* Auto-publicación */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col gap-3">
        <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
          Auto-publicación semanal
        </p>
        <p className="text-sm text-gray-500">
          Publica automáticamente los lunes y jueves a las 10:00h con los 5 mejores pisos
          no publicados en los últimos 14 días. Generado por Claude.
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={() => weeklyMutation.mutate()}
            disabled={weeklyMutation.isPending}
            className="text-sm bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {weeklyMutation.isPending ? "Generando..." : "▶ Ejecutar ahora"}
          </button>
          {weeklyMutation.isSuccess && (
            <span className="text-sm text-green-600">
              {weeklyMutation.data?.status === "sent"
                ? `✓ Publicado (${weeklyMutation.data.properties_featured} propiedades)`
                : weeklyMutation.data?.reason ?? "Completado"}
            </span>
          )}
          {weeklyMutation.isError && (
            <span className="text-sm text-red-600">Error al generar</span>
          )}
        </div>
      </div>

      {/* Nueva publicación manual */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col gap-4">
        <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
          Nueva publicación manual
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">Tipo</label>
            <select
              value={form.type}
              onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="oportunidades">Oportunidades</option>
              <option value="mercado">Mercado</option>
              <option value="zonas">Zonas</option>
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">Zona (opcional)</label>
            <input
              value={form.zone}
              onChange={(e) => setForm((f) => ({ ...f, zone: e.target.value }))}
              placeholder="Ej: Eixample, Gràcia..."
              className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Título</label>
          <input
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Resumen semanal · Mayo 2026"
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Cuerpo del mensaje</label>
          <textarea
            rows={6}
            value={form.body}
            onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            placeholder="Contenido del informe..."
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {preview && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap text-gray-700">
            {previewText}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => setPreview((p) => !p)}
            className="text-sm border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {preview ? "Ocultar preview" : "Ver preview"}
          </button>
          <button
            onClick={() => publishMutation.mutate()}
            disabled={publishMutation.isPending || !form.title || !form.body}
            className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {publishMutation.isPending ? "Publicando..." : "Publicar en Telegram"}
          </button>
        </div>
        {publishMutation.isSuccess && (
          <p className="text-sm text-green-600">✓ Publicado en @inversorinformado</p>
        )}
      </div>

      {/* Historial */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
            Historial de envíos
          </p>
        </div>
        {log.length === 0 ? (
          <p className="text-sm text-gray-400 px-5 py-6">Aún no hay mensajes enviados.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Fecha</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Tipo</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Mensaje</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {log.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                    {new Date(entry.sent_at).toLocaleString("es-ES")}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TYPE_COLOR[entry.type] ?? "bg-gray-100 text-gray-600"}`}>
                      {TYPE_LABEL[entry.type] ?? entry.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-md truncate">
                    {entry.content}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${entry.status === "sent" ? "text-green-600" : "text-red-600"}`}>
                      {entry.status === "sent" ? "✓ Enviado" : "✗ Fallido"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Commit**
```bash
git add frontend/src/pages/Comunicaciones.tsx
git commit -m "feat: add Comunicaciones page with Telegram log, manual publish and auto-publish"
```

---

## Task 13: Frontend — rutas y navegación

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Actualizar `frontend/src/App.tsx`**

Añadir los imports nuevos junto a los existentes:
```tsx
import Informes from "./pages/Informes";
import InformeNuevo from "./pages/InformeNuevo";
import InformeDetalle from "./pages/InformeDetalle";
import Comunicaciones from "./pages/Comunicaciones";
```

En el bloque `<nav>`, añadir después del NavLink de Monitor:
```tsx
<NavLink
  to="/informes"
  className={({ isActive }) =>
    isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
  }
>
  Informes
</NavLink>
<NavLink
  to="/comunicaciones"
  className={({ isActive }) =>
    isActive ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-800"
  }
>
  Comunicaciones
</NavLink>
```

En el bloque `<Routes>`, añadir junto a las rutas existentes:
```tsx
<Route path="/informes" element={<Informes />} />
<Route path="/informes/nuevo" element={<InformeNuevo />} />
<Route path="/informes/:id" element={<InformeDetalle />} />
<Route path="/comunicaciones" element={<Comunicaciones />} />
```

- [ ] **Verificar compilación TypeScript**
```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Arrancar dev server y probar**
```bash
cd frontend && npm run dev
```
Verificar:
- Nav muestra "Informes" y "Comunicaciones"
- `/informes` muestra listado vacío con botón "Nuevo análisis"
- `/informes/nuevo` muestra el selector de piso
- `/comunicaciones` muestra las tres secciones

- [ ] **Commit final**
```bash
git add frontend/src/App.tsx
git commit -m "feat: wire up Informes and Comunicaciones routes and nav links"
```

---

## Verificación final

- [ ] Crear un informe completo end-to-end: seleccionar piso → usar "Estimar con IA" → guardar → ver HTML preview → descargar PDF
- [ ] Publicar el informe en Telegram desde la vista de detalle
- [ ] En Comunicaciones: hacer una publicación manual y verificar que aparece en el historial
- [ ] Ejecutar la auto-publicación manualmente y verificar que el historial se actualiza
- [ ] Verificar que los pisos publicados tienen `last_featured_at` actualizado en Supabase

---

## Notas para Railway (producción)

1. Añadir `ANTHROPIC_API_KEY` en las variables de entorno de Railway (ver instrucciones en `.env.example`)
2. El scheduler APScheduler se inicia automáticamente con el servidor — no requiere configuración adicional
3. Playwright ya está disponible vía `scrapling[all]` — no se necesitan dependencias extra para PDF

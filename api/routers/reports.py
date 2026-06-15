from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

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
    condition: Optional[str] = None


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

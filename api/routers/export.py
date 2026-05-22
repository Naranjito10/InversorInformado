from __future__ import annotations
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/excel")
def export_excel(
    municipio: Optional[str] = Query(None),
    score_min: Optional[int] = Query(None),
    score_label: Optional[str] = Query(None),
    precio_min: Optional[int] = Query(None),
    precio_max: Optional[int] = Query(None),
):
    from api.services.export_service import generate_excel

    filters = {}
    if municipio:
        filters["municipio"] = municipio
    if score_min is not None:
        filters["score_min"] = score_min
    if score_label:
        filters["score_label"] = score_label
    if precio_min is not None:
        filters["precio_min"] = precio_min
    if precio_max is not None:
        filters["precio_max"] = precio_max

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    generate_excel(Path(tmp.name), filters=filters)

    return FileResponse(
        path=tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="oportunidades.xlsx",
    )
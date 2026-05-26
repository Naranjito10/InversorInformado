from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from api.services import fuentes_service

router = APIRouter(prefix="/api/fuentes", tags=["fuentes"])


class FuenteCreate(BaseModel):
    id: str
    nombre: str
    test_url: str | None = None


class FuenteToggle(BaseModel):
    activo: bool


class FuenteUpdate(BaseModel):
    nombre: str
    test_url: str | None = None


@router.get("")
def get_fuentes(solo_activos: bool = False):
    return fuentes_service.get_fuentes(solo_activos=solo_activos)


@router.post("")
def create_fuente(body: FuenteCreate):
    return fuentes_service.create_fuente(body.id, body.nombre, body.test_url)


@router.patch("/{fuente_id}/toggle")
def toggle_fuente(fuente_id: str, body: FuenteToggle):
    return fuentes_service.toggle_fuente(fuente_id, body.activo)


@router.put("/{fuente_id}")
def update_fuente(fuente_id: str, body: FuenteUpdate):
    return fuentes_service.update_fuente(fuente_id, body.nombre, body.test_url)


@router.delete("/{fuente_id}")
def delete_fuente(fuente_id: str):
    return fuentes_service.delete_fuente(fuente_id)

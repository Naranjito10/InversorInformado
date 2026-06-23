from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services import config_service

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    value: str


@router.get("")
def get_config():
    return config_service.get_all_config()


@router.put("/{key}")
def update_config(key: str, body: ConfigUpdate):
    result = config_service.set_config(key, body.value)
    if not result:
        raise HTTPException(status_code=404, detail=f"Clave '{key}' no encontrada")
    return result

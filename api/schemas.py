from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class ListingOut(BaseModel):
    id: Optional[str] = None
    url: str
    fuente: str
    titulo: Optional[str] = None
    precio_venta: Optional[int] = None
    metros_cuadrados: Optional[float] = None
    habitaciones: Optional[int] = None
    banos: Optional[int] = None
    barrio: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    ascensor: Optional[bool] = None
    terraza: Optional[bool] = None
    garaje: Optional[bool] = None
    precio_m2: Optional[int] = None
    rentabilidad_bruta: Optional[float] = None
    score: Optional[int] = None
    score_label: Optional[str] = None
    bajada_precio: Optional[bool] = None
    dias_en_mercado: Optional[int] = None
    activo: Optional[bool] = None
    primera_deteccion: Optional[str] = None
    ultima_actualizacion: Optional[str] = None

    class Config:
        extra = "allow"


class StatsOut(BaseModel):
    total_activos: int
    nuevos_esta_semana: int
    score_medio: float
    bajadas_precio: int
    por_fuente: dict[str, int]
    por_label: dict[str, int]


class SearchRequest(BaseModel):
    zona: str
    precio_min: Optional[int] = None
    precio_max: Optional[int] = None
    portales: list[str]
    max_pages: int = 10


class SearchResponse(BaseModel):
    status: str
    zona: str
    portales: list[str]
    targets: int
    search_urls: list[str]


class ZoneOut(BaseModel):
    key: str
    label: str
    portales_disponibles: list[str]
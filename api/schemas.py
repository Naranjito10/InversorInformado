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
    status: Optional[str] = None
    condition: Optional[str] = None
    ocupacion: Optional[str] = None
    situacion_legal: Optional[str] = None
    ascensor: Optional[bool] = None
    terraza: Optional[bool] = None
    garaje: Optional[bool] = None
    precio_m2: Optional[int] = None
    rentabilidad_bruta: Optional[float] = None
    score: Optional[int] = None
    score_label: Optional[str] = None
    bajada_precio: Optional[bool] = None
    dias_en_mercado: Optional[int] = None
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


class ManualListingIn(BaseModel):
    url: str
    fuente: str
    titulo: Optional[str] = None
    precio_venta: Optional[int] = None
    metros_cuadrados: Optional[int] = None
    habitaciones: Optional[int] = None
    banos: Optional[int] = None
    municipio: Optional[str] = None
    barrio: Optional[str] = None
    provincia: Optional[str] = None
    planta: Optional[str] = None
    condition: Optional[str] = None
    ocupacion: Optional[str] = None
    situacion_legal: Optional[str] = None
    ascensor: Optional[bool] = None
    terraza: Optional[bool] = None
    garaje: Optional[bool] = None
    certificado_energetico: Optional[str] = None
    alquiler_estimado: Optional[int] = None
    precio_zona_m2: Optional[int] = None
    balcon: Optional[bool] = None
    trastero: Optional[bool] = None
    armarios_empotrados: Optional[bool] = None
    aire_acondicionado: Optional[bool] = None
    calefaccion: Optional[bool] = None
    calefaccion_tipo: Optional[str] = None
    cocina_equipada: Optional[bool] = None
    amueblado: Optional[bool] = None
    exterior: Optional[bool] = None
    orientacion: Optional[str] = None
    portero: Optional[bool] = None
    puerta_blindada: Optional[bool] = None
    doble_acristalamiento: Optional[bool] = None
    adaptado_movilidad: Optional[bool] = None
    jardin: Optional[bool] = None
    piscina: Optional[bool] = None
    piscina_comunitaria: Optional[bool] = None
    zonas_verdes_comunitarias: Optional[bool] = None
    vigilancia: Optional[bool] = None
    garaje_incluido: Optional[bool] = None
    num_plazas_garaje: Optional[int] = None
    referencia_catastral: Optional[str] = None


class CheckUrlsRequest(BaseModel):
    urls: list[str]


class BulkImportRequest(BaseModel):
    listings: list[ManualListingIn]


class BulkImportResult(BaseModel):
    inserted: int
    updated: int
    errors: int
    error_details: list[dict]
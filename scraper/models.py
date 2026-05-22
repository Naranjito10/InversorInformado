"""Modelos de dominio (Pydantic) para viviendas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


VALID_ESTADOS = {"nuevo", "buen estado", "a reformar", None}


class Listing(BaseModel):
    """Estructura unificada de vivienda. Coincide con la tabla `listings`."""

    # Identificacion
    url: str
    fuente: str
    titulo: Optional[str] = None

    # Precios
    precio_venta: Optional[int] = None
    ibi: Optional[int] = None
    comunidad: Optional[int] = None
    derramas_pendientes: Optional[int] = None
    precio_m2: Optional[int] = None

    # Caracteristicas fisicas
    metros_cuadrados: Optional[int] = None
    habitaciones: Optional[int] = None
    banos: Optional[int] = None
    planta: Optional[str] = None
    ascensor: Optional[bool] = None
    terraza: Optional[bool] = None
    garaje: Optional[bool] = None
    estado: Optional[str] = None
    certificado_energetico: Optional[str] = None

    # Localizacion
    barrio: Optional[str] = None
    municipio: Optional[str] = None
    provincia: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    # Mercado / inversion
    alquiler_estimado: Optional[int] = None
    rentabilidad_alquiler: Optional[int] = None
    rentabilidad_bruta: Optional[float] = None
    precio_zona_m2: Optional[int] = None
    descuento_zona_pct: Optional[float] = None

    # Seguimiento
    dias_en_mercado: Optional[int] = None
    veces_visto: int = 1
    score: Optional[int] = None
    score_label: Optional[str] = None
    bajada_precio: bool = False
    campos_vacios: Optional[int] = None
    primera_deteccion: Optional[datetime] = None
    ultima_actualizacion: Optional[datetime] = None
    activo: bool = True

    # Deduplicación
    pending_review: bool = False
    duplicate_candidate_of: Optional[str] = None

    # Datos crudos para reparsear si hace falta
    raw_data: Optional[dict[str, Any]] = None

    @field_validator("estado")
    @classmethod
    def _normalize_estado(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_norm = v.lower().strip()
        # mapeo flexible
        if "reform" in v_norm or "rehab" in v_norm:
            return "a reformar"
        if "obra nueva" in v_norm or "nuevo" in v_norm or "estren" in v_norm:
            return "nuevo"
        if "buen" in v_norm or "segunda mano" in v_norm:
            return "buen estado"
        return None

    @field_validator("certificado_energetico")
    @classmethod
    def _normalize_cee(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_up = v.upper().strip()
        if v_up and v_up[0] in "ABCDEFG":
            return v_up[0]
        return None

    def to_db_dict(self) -> dict[str, Any]:
        """Serializa para insertar en Supabase. Excluye None salvo el flag `activo`."""
        data = self.model_dump(mode="json", exclude_none=False)
        # Mantener `activo` y `bajada_precio` aunque sean False/None
        # Quitar None (Postgres acepta omision)
        cleaned = {
            k: v for k, v in data.items()
            if v is not None or k in {"activo", "veces_visto", "bajada_precio", "pending_review"}
        }
        return cleaned

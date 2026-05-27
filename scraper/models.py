"""Modelos de dominio (Pydantic) para viviendas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator


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
    tipo_propiedad: Optional[str] = None

    # Extras — base
    ascensor: Optional[bool] = None
    terraza: Optional[bool] = None
    garaje: Optional[bool] = None
    garaje_incluido: Optional[bool] = None
    num_plazas_garaje: Optional[int] = None
    certificado_energetico: Optional[str] = None

    # Extras — interiores
    balcon: Optional[bool] = None
    trastero: Optional[bool] = None
    armarios_empotrados: Optional[bool] = None
    aire_acondicionado: Optional[bool] = None
    calefaccion: Optional[bool] = None
    calefaccion_tipo: Optional[str] = None
    cocina_equipada: Optional[bool] = None
    amueblado: Optional[bool] = None

    # Extras — edificio
    exterior: Optional[bool] = None
    orientacion: Optional[str] = None
    portero: Optional[bool] = None
    puerta_blindada: Optional[bool] = None
    doble_acristalamiento: Optional[bool] = None
    adaptado_movilidad: Optional[bool] = None

    # Extras — zonas exteriores / comunidad
    jardin: Optional[bool] = None
    piscina: Optional[bool] = None
    piscina_comunitaria: Optional[bool] = None
    zonas_verdes_comunitarias: Optional[bool] = None
    vigilancia: Optional[bool] = None

    # Clasificacion del inmueble
    # condition: obra_nueva | listo_para_usar | buen_estado | reforma_leve | reforma_integral | reforma_estructural
    condition: Optional[str] = None
    # ocupacion: libre | ocupado | alquilado | nuda_propiedad
    ocupacion: Optional[str] = None
    # situacion_legal: libre_cargas | con_hipoteca | en_construccion | renta_antigua | vpo | subasta | litigio | herencia
    situacion_legal: Optional[str] = None

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

    # Estado del registro en BD
    # status: activo | pendiente_revision | reservado | en_pausa | inactivo | descartado
    status: str = "activo"
    # disabled_reason: duplicado_nuevo_elegido | duplicado_antiguo_elegido | no_visto_scraper | revision_manual
    disabled_reason: Optional[str] = None

    # Deduplicacion
    duplicate_candidate_of: Optional[str] = None

    # Datos crudos para reparsear si hace falta
    raw_data: Optional[dict[str, Any]] = None

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
        """Serializa para insertar en Supabase. Excluye None; preserva False y status."""
        data = self.model_dump(mode="json", exclude_none=False)
        return {
            k: v for k, v in data.items()
            if v is not None or k in {"status", "veces_visto", "bajada_precio"}
        }

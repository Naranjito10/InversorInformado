"""
Calculo de score y label en Python.

Espejo de la funcion SQL `calcular_score` del fichero 003_scoring_function.sql.
Util para:
- Testear localmente sin necesidad de Supabase.
- Mostrar el score en alertas antes de que el trigger SQL lo escriba.
"""
from __future__ import annotations

from typing import Tuple, Union

from .models import Listing


def calcular_score(v: Union[Listing, dict]) -> Tuple[int, str]:
    """
    Calcula (score, label) segun los pesos definidos en el prompt maestro.
    """
    if isinstance(v, Listing):
        d = v.model_dump()
    else:
        d = v

    score = 0

    # RENTABILIDAD (0-40)
    rb = d.get("rentabilidad_bruta")
    if rb is not None:
        if rb >= 7:
            score += 40
        elif rb >= 5:
            score += 25
        elif rb >= 4:
            score += 10

    # DESCUENTO ZONA (0-25)
    dz = d.get("descuento_zona_pct")
    if dz is not None:
        if dz <= -10:
            score += 25
        elif dz <= -5:
            score += 15
        elif dz <= 0:
            score += 8

    # ESTADO Y EXTRAS (0-20)
    if d.get("estado") == "buen estado":
        score += 8
    if d.get("ascensor") is True:
        score += 4
    if d.get("terraza") is True:
        score += 4
    if d.get("garaje") is True:
        score += 4

    # SEÑALES DE URGENCIA (0-15)
    if d.get("bajada_precio") is True:
        score += 10
    if (d.get("dias_en_mercado") or 0) > 60:
        score += 5

    # PENALIZACIONES
    if (d.get("campos_vacios") or 0) > 5:
        score = min(score, 40)
    if d.get("estado") == "a reformar":
        score -= 5

    # Acotar
    score = max(0, min(100, score))

    # Label
    if score >= 80:
        label = "alto"
    elif score >= 50:
        label = "medio"
    else:
        label = "normal"
    if (d.get("campos_vacios") or 0) > 3:
        label = "incompleto"

    return score, label


def contar_campos_vacios(v: Union[Listing, dict]) -> int:
    """Cuenta campos clave nulos (espejo de la funcion SQL)."""
    if isinstance(v, Listing):
        d = v.model_dump()
    else:
        d = v
    claves = [
        "precio_venta", "metros_cuadrados", "habitaciones", "banos",
        "estado", "barrio", "municipio", "precio_m2",
        "certificado_energetico", "planta",
    ]
    return sum(1 for k in claves if d.get(k) is None)

"""Tests del calculador de score (espejo Python del SQL)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.services.scorer import calcular_score, contar_campos_vacios


def test_score_alto_rentabilidad_y_descuento():
    v = {
        "rentabilidad_bruta": 7.5,        # 40
        "descuento_zona_pct": -12,        # 25
        "estado": "buen estado",          # 8
        "ascensor": True,                 # 4
        "terraza": True,                  # 4
        "garaje": True,                   # 4
        "bajada_precio": False,
        "dias_en_mercado": 10,
        "campos_vacios": 0,
    }
    score, label = calcular_score(v)
    assert score == 40 + 25 + 8 + 4 + 4 + 4 == 85
    assert label == "alto"


def test_score_medio():
    v = {
        "rentabilidad_bruta": 5.5,        # 25
        "descuento_zona_pct": -3,         # 8
        "estado": "buen estado",          # 8
        "ascensor": True,                 # 4
        "terraza": False,
        "garaje": False,
        "bajada_precio": False,
        "dias_en_mercado": 0,
        "campos_vacios": 1,
    }
    score, label = calcular_score(v)
    assert score == 25 + 8 + 8 + 4 == 45
    assert label == "normal"  # < 50 -> normal


def test_score_con_bajada_y_dias_largos():
    v = {
        "rentabilidad_bruta": 4.5,        # 10
        "descuento_zona_pct": -6,         # 15
        "estado": "buen estado",          # 8
        "ascensor": True,                 # 4
        "bajada_precio": True,            # 10
        "dias_en_mercado": 90,            # 5
        "campos_vacios": 0,
    }
    score, label = calcular_score(v)
    assert score == 10 + 15 + 8 + 4 + 10 + 5 == 52
    assert label == "medio"


def test_score_penalizacion_campos_vacios():
    v = {
        "rentabilidad_bruta": 8,          # 40 (sin cap)
        "descuento_zona_pct": -15,        # 25
        "estado": "buen estado",
        "campos_vacios": 6,               # cap a 40
    }
    score, label = calcular_score(v)
    assert score == 40              # caped
    assert label == "incompleto"    # campos_vacios > 3


def test_score_penalizacion_a_reformar():
    v = {
        "rentabilidad_bruta": 7,          # 40
        "descuento_zona_pct": -5,         # 15
        "estado": "a reformar",           # -5
        "campos_vacios": 0,
    }
    score, label = calcular_score(v)
    assert score == 40 + 15 - 5 == 50
    assert label == "medio"


def test_score_label_incompleto_overrides():
    v = {
        "rentabilidad_bruta": 8,
        "descuento_zona_pct": -15,
        "estado": "buen estado",
        "campos_vacios": 4,               # > 3 -> incompleto
    }
    score, label = calcular_score(v)
    assert label == "incompleto"


def test_score_minimo_0():
    v = {
        "rentabilidad_bruta": None,
        "descuento_zona_pct": None,
        "estado": "a reformar",
        "campos_vacios": 0,
    }
    score, label = calcular_score(v)
    assert score == 0                   # acotado a 0
    assert label == "normal"


def test_contar_campos_vacios():
    v = {"precio_venta": 100000, "metros_cuadrados": 80}
    assert contar_campos_vacios(v) == 8  # 10 claves - 2 rellenas


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
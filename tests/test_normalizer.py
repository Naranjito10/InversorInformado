"""Tests del normalizer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.services.normalizer import (
    canonical_url, clean_float, clean_int, clean_str,
    detect_cee, detect_estado, detect_features, normalize,
)


def test_clean_int_spanish_format():
    assert clean_int("1.250.000 €") == 1250000
    assert clean_int("85 m²") == 85
    assert clean_int("3 hab.") == 3
    assert clean_int(None) is None
    assert clean_int("sin datos") is None


def test_clean_float_european_format():
    assert clean_float("6,5%") == 6.5
    assert clean_float("-12,3") == -12.3
    assert clean_float(None) is None


def test_canonical_url_strips_query_and_trailing_slash():
    u = "https://www.idealista.com/inmueble/12345/?utm_source=email#foo"
    assert canonical_url(u) == "https://www.idealista.com/inmueble/12345"


def test_detect_features_from_description():
    desc = "Piso reformado con ascensor, terraza grande y sin garaje"
    f = detect_features(desc)
    assert f["ascensor"] is True
    assert f["terraza"] is True
    # 'sin garaje' debe detectarse como negacion
    assert f["garaje"] is False


def test_detect_estado():
    assert detect_estado("Vivienda a reformar en el centro") == "a reformar"
    assert detect_estado("Obra nueva con piscina") == "nuevo"
    assert detect_estado("Buen estado, segunda mano") == "buen estado"
    assert detect_estado("Texto sin pistas") is None


def test_detect_cee():
    assert detect_cee("Certificado energético: C consumo 120 kWh") == "C"
    assert detect_cee("Etiqueta energetica E") == "E"
    assert detect_cee("Sin info") is None


def test_normalize_minimal():
    raw = {
        "url": "https://www.idealista.com/inmueble/12345?utm=x",
        "titulo": "Piso en Eixample",
        "precio_venta": "350.000 €",
        "metros_cuadrados": "80 m²",
        "habitaciones": "3 hab",
        "description": "Piso con ascensor y terraza",
        "municipio": "Barcelona",
        "barrio": "Eixample",
    }
    l = normalize("idealista", raw)
    assert l.url == "https://www.idealista.com/inmueble/12345"
    assert l.fuente == "idealista"
    assert l.precio_venta == 350000
    assert l.metros_cuadrados == 80
    assert l.habitaciones == 3
    assert l.precio_m2 == round(350000 / 80)
    assert l.ascensor is True
    assert l.terraza is True
    assert l.municipio == "Barcelona"
    assert l.barrio == "Eixample"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

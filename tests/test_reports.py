import pytest
from unittest.mock import patch, MagicMock


def make_report_data():
    return {
        "type": "analysis",
        "title": "Test Eixample",
        "property_id": None,
        "data": {
            "property": {"direccion": "Calle Test 1", "municipio": "Barcelona",
                         "barrio": "Eixample", "precio": 300000, "metros": 80,
                         "habitaciones": 3, "banos": 1, "estado": "buen estado",
                         "url": "https://example.com", "cee": "D"},
            "market": {"precio_m2_zona_min": 3000, "precio_m2_zona_medio": 4000,
                       "precio_m2_zona_max": 5000, "alquiler_estimado_mes": 1500,
                       "rentabilidad_bruta": 6.0, "rentabilidad_neta": 4.2,
                       "rentabilidad_bruta_media_zona": 4.5,
                       "rentabilidad_neta_media_zona": 3.0,
                       "demanda_alquiler": "alta", "dias_hasta_alquiler": 12,
                       "ai_estimated": True},
            "building": {"anyo_construccion": 1980, "ite_resultado": "favorable",
                         "ite_fecha": "2022", "humedades": False, "ascensor": True,
                         "electrica": "renovada", "fondo_reserva": 20000,
                         "fondo_reserva_estado": "Adecuado",
                         "alerta_reformas": "Sin reformas urgentes."},
            "scores": {"global": 80, "global_grade": "A-", "precio": 82,
                       "precio_grade": "A", "rentabilidad": 85,
                       "rentabilidad_grade": "A", "edificio": 70,
                       "edificio_grade": "B+", "vecindario": 78,
                       "vecindario_grade": "B+", "resumen": "Buena oportunidad.",
                       "percentil_precio": 18, "percentil_rentabilidad": 15,
                       "percentil_vecindario": 22},
            "amenities": {"transporte": 8.5, "colegios": 7.0, "salud": 8.0,
                          "comercios": 9.0, "zonas_verdes": 6.5, "seguridad": 7.5,
                          "ambiente": 8.0, "aparcamiento": 5.0,
                          "descripcion_cercano": "Metro a 5 min."},
            "verdict": "Buena oportunidad de inversión."
        }
    }


def test_create_report_returns_id():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "abc-123", **make_report_data()}
    ]
    with patch("api.services.reports_service.get_client", return_value=mock_client):
        from api.services.reports_service import create_report
        result = create_report(make_report_data())
    assert result["id"] == "abc-123"


def test_list_reports_returns_list():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"id": "abc-123", "title": "Test", "type": "analysis", "created_at": "2026-01-01"}
    ]
    with patch("api.services.reports_service.get_client", return_value=mock_client):
        from api.services.reports_service import list_reports
        result = list_reports()
    assert len(result) == 1
    assert result[0]["id"] == "abc-123"


def test_get_report_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    with patch("api.services.reports_service.get_client", return_value=mock_client):
        from api.services.reports_service import get_report
        result = get_report("nonexistent-id")
    assert result is None

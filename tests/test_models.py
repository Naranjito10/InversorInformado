"""Unit tests for Listing model serialization."""
import pytest
from scraper.models import Listing


def test_status_default_activo():
    l = Listing(url="http://x.com/1", fuente="test")
    assert l.status == "activo"


def test_condition_accepts_valid_value():
    l = Listing(url="http://x.com/1", fuente="test", condition="obra_nueva")
    assert l.condition == "obra_nueva"


def test_condition_default_none():
    l = Listing(url="http://x.com/1", fuente="test")
    assert l.condition is None


def test_to_db_dict_always_includes_status():
    l = Listing(url="http://x.com/1", fuente="test")
    d = l.to_db_dict()
    assert "status" in d
    assert d["status"] == "activo"


def test_to_db_dict_no_old_fields():
    l = Listing(url="http://x.com/1", fuente="test")
    d = l.to_db_dict()
    assert "activo" not in d
    assert "pending_review" not in d
    assert "estado" not in d


def test_to_db_dict_includes_true_amenity():
    l = Listing(url="http://x.com/1", fuente="test", balcon=True)
    d = l.to_db_dict()
    assert d["balcon"] is True


def test_to_db_dict_includes_false_amenity():
    # False means "explicitly absent" — different from None (unknown)
    l = Listing(url="http://x.com/1", fuente="test", trastero=False)
    d = l.to_db_dict()
    assert d["trastero"] is False


def test_to_db_dict_excludes_none_amenity():
    l = Listing(url="http://x.com/1", fuente="test")
    d = l.to_db_dict()
    assert "balcon" not in d


def test_to_db_dict_preserves_bajada_precio_false():
    l = Listing(url="http://x.com/1", fuente="test", bajada_precio=False)
    d = l.to_db_dict()
    assert "bajada_precio" in d


def test_certificado_energetico_normalizes():
    l = Listing(url="http://x.com/1", fuente="test", certificado_energetico="b+")
    assert l.certificado_energetico == "B"

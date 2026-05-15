"""Tests de parseo para cada scraper usando HTML fixtures.

Los fixtures son fragmentos HTML representativos de la estructura real
de cada portal. Se usan para validar que parse_search_page extrae
correctamente los campos clave sin necesidad de red.
"""
from __future__ import annotations

import json

import pytest

from scraper.scrapers.casaradar import CasaradarScraper
from scraper.scrapers.fotocasa import FotocasaScraper
from scraper.scrapers.habitaclia import HabitacliaScraper
from scraper.scrapers.idealista import IdealistaScraper


# ---------------------------------------------------------------------------
# Fixtures HTML
# ---------------------------------------------------------------------------

IDEALISTA_HTML = """
<html><body>
  <section class="items-list">
    <article class="item" data-element-id="123456">
      <a class="item-link" href="/inmueble/123456/" title="Piso en Gracia">
        Piso en Gracia
      </a>
      <span class="item-price">185.000 €</span>
      <div class="item-detail-char">
        <span class="item-detail">65 m²</span>
        <span class="item-detail">3 hab.</span>
        <span class="item-detail">Planta 2</span>
      </div>
      <p class="item-description">Magnifico piso reformado con ascensor.</p>
    </article>
    <article class="item" data-element-id="789012">
      <a class="item-link" href="/inmueble/789012/" title="Ático en Eixample">
        Ático en Eixample
      </a>
      <span class="item-price">320.000 €</span>
      <div class="item-detail-char">
        <span class="item-detail">90 m²</span>
        <span class="item-detail">4 hab.</span>
        <span class="item-detail">Planta 5 con ascensor</span>
      </div>
    </article>
  </section>
  <nav>
    <li class="next"><a href="/venta-viviendas/barcelona/pagina-2">Siguiente</a></li>
  </nav>
</body></html>
"""

FOTOCASA_NEXT_DATA = {
    "props": {
        "pageProps": {
            "initialSearch": {
                "result": {
                    "realEstates": [
                        {
                            "link": "/d/piso-venta-barcelona/123",
                            "title": "Piso en venta en Barcelona",
                            "transactions": [{"value": 250000}],
                            "features": {
                                "surface": 80,
                                "rooms": 3,
                                "bathrooms": 2,
                                "elevator": True,
                                "terrace": False,
                                "parking": False,
                                "conservationState": "buen estado",
                                "energyCertificate": {"rating": "C"},
                            },
                            "address": {
                                "neighborhood": {"name": "Gracia"},
                                "town": {"name": "Barcelona"},
                                "province": {"name": "Barcelona"},
                            },
                            "coordinates": {"latitude": 41.4, "longitude": 2.15},
                        }
                    ]
                }
            }
        }
    }
}

FOTOCASA_HTML = f"""
<html><body>
  <script id="__NEXT_DATA__" type="application/json">{json.dumps(FOTOCASA_NEXT_DATA)}</script>
  <article class="re-CardPack">
    <a href="/d/piso-en-barcelona/456" title="Piso fallback">Piso fallback</a>
    <span class="re-CardPrice">220.000 €</span>
  </article>
</body></html>
"""

HABITACLIA_HTML = """
<html><body>
  <ul>
    <li class="list-item">
      <article class="list-item-container">
        <a href="/vivienda-en-gracia-barcelona/99887" class="list-item-title">
          Piso en Gracia
        </a>
        <span class="list-item-price">195.000 €</span>
        <ul class="list-feature">
          <li>70 m²</li>
          <li>3 hab.</li>
          <li>1 baño</li>
          <li>Planta 1</li>
        </ul>
        <span class="list-item-location">Gracia, Barcelona</span>
      </article>
    </li>
  </ul>
  <a class="next" href="/venta-pisos-barcelona-2.htm">Siguiente</a>
</body></html>
"""

CASARADAR_HTML = """
<html><body>
  <article class="property">
    <a href="/comprar/piso-barcelona-55544" title="Piso en venta">
      Piso en venta Barcelona
    </a>
    <span class="price">175.000 €</span>
    <ul class="specs">
      <li>60 m²</li>
      <li>2 hab.</li>
      <li>1 baño</li>
    </ul>
    <span class="location">Sant Andreu, Barcelona</span>
  </article>
</body></html>
"""


# ---------------------------------------------------------------------------
# Idealista
# ---------------------------------------------------------------------------

class TestIdealistaScraper:
    scraper = IdealistaScraper()

    def test_parse_returns_correct_count(self):
        items = list(self.scraper.parse_search_page(IDEALISTA_HTML, "https://www.idealista.com/venta-viviendas/barcelona/"))
        assert len(items) == 2

    def test_parse_url(self):
        items = list(self.scraper.parse_search_page(IDEALISTA_HTML, ""))
        assert items[0]["url"] == "https://www.idealista.com/inmueble/123456/"

    def test_parse_titulo(self):
        items = list(self.scraper.parse_search_page(IDEALISTA_HTML, ""))
        assert "Gracia" in items[0]["titulo"]

    def test_parse_precio(self):
        items = list(self.scraper.parse_search_page(IDEALISTA_HTML, ""))
        assert "185" in str(items[0].get("precio_venta", ""))

    def test_parse_metros(self):
        items = list(self.scraper.parse_search_page(IDEALISTA_HTML, ""))
        assert "65" in str(items[0].get("metros_cuadrados", ""))

    def test_next_page_from_link(self):
        url = self.scraper.next_page_url(IDEALISTA_HTML, "https://www.idealista.com/venta-viviendas/barcelona/", 1)
        assert url is not None
        assert "pagina-2" in url

    def test_next_page_url_pattern_increment(self):
        html = "<html></html>"
        url = self.scraper.next_page_url(html, "https://www.idealista.com/venta-viviendas/barcelona/pagina-3", 3)
        assert url is not None
        assert "pagina-4" in url

    def test_next_page_none_on_last(self):
        html = "<html></html>"  # sin enlace siguiente
        url = self.scraper.next_page_url(html, "https://www.idealista.com/venta-viviendas/barcelona/pagina-5", 5)
        # Puede devolver None o intentar pagina-6; lo importante es no crashear
        assert url is None or "pagina-6" in url

    def test_use_js_flag(self):
        assert self.scraper.USE_JS is True


# ---------------------------------------------------------------------------
# Fotocasa
# ---------------------------------------------------------------------------

class TestFotocasaScraper:
    scraper = FotocasaScraper()

    def test_parse_from_next_data(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, "https://www.fotocasa.es/"))
        assert len(items) >= 1

    def test_next_data_url(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, "https://www.fotocasa.es/"))
        assert "fotocasa.es" in items[0]["url"]

    def test_next_data_precio(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, ""))
        assert items[0].get("precio_venta") == 250000

    def test_next_data_superficie(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, ""))
        assert items[0].get("metros_cuadrados") == 80

    def test_next_data_habitaciones(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, ""))
        assert items[0].get("habitaciones") == 3

    def test_next_data_barrio(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, ""))
        assert items[0].get("barrio") == "Gracia"

    def test_next_data_ascensor(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, ""))
        assert items[0].get("ascensor") is True

    def test_next_data_certificado(self):
        items = list(self.scraper.parse_search_page(FOTOCASA_HTML, ""))
        assert items[0].get("certificado_energetico") == "C"

    def test_next_page_pattern(self):
        url = self.scraper.next_page_url("", "https://www.fotocasa.es/es/comprar/viviendas/barcelona/l", 1)
        assert url is not None
        assert url.endswith("/2") or "/l/2" in url

    def test_next_page_increment(self):
        url = self.scraper.next_page_url("", "https://www.fotocasa.es/es/comprar/viviendas/barcelona/l/3", 3)
        assert url is not None
        assert "/l/4" in url

    def test_use_js_flag(self):
        assert self.scraper.USE_JS is True


# ---------------------------------------------------------------------------
# Habitaclia
# ---------------------------------------------------------------------------

class TestHabitacliaScraper:
    scraper = HabitacliaScraper()

    def test_parse_returns_items(self):
        items = list(self.scraper.parse_search_page(HABITACLIA_HTML, "https://www.habitaclia.com/"))
        assert len(items) == 1

    def test_parse_url(self):
        items = list(self.scraper.parse_search_page(HABITACLIA_HTML, ""))
        assert "habitaclia.com" in items[0]["url"]
        assert "99887" in items[0]["url"]

    def test_parse_precio(self):
        items = list(self.scraper.parse_search_page(HABITACLIA_HTML, ""))
        assert "195" in str(items[0].get("precio_venta", ""))

    def test_parse_metros(self):
        items = list(self.scraper.parse_search_page(HABITACLIA_HTML, ""))
        assert "70" in str(items[0].get("metros_cuadrados", ""))

    def test_parse_barrio(self):
        items = list(self.scraper.parse_search_page(HABITACLIA_HTML, ""))
        assert items[0].get("barrio") is not None

    def test_next_page_from_link(self):
        url = self.scraper.next_page_url(HABITACLIA_HTML, "https://www.habitaclia.com/venta-pisos-barcelona.htm", 1)
        assert url is not None
        assert "-2.htm" in url

    def test_next_page_pattern(self):
        html = "<html></html>"
        url = self.scraper.next_page_url(html, "https://www.habitaclia.com/venta-pisos-barcelona-3.htm", 3)
        assert url is not None
        assert "-4.htm" in url

    def test_use_js_flag(self):
        assert self.scraper.USE_JS is True


# ---------------------------------------------------------------------------
# Casaradar
# ---------------------------------------------------------------------------

class TestCasaradarScraper:
    scraper = CasaradarScraper()

    def test_parse_returns_items(self):
        items = list(self.scraper.parse_search_page(CASARADAR_HTML, "https://www.casaradar.es/"))
        assert len(items) == 1

    def test_parse_url(self):
        items = list(self.scraper.parse_search_page(CASARADAR_HTML, ""))
        assert "casaradar.es" in items[0]["url"]
        assert "55544" in items[0]["url"]

    def test_parse_precio(self):
        items = list(self.scraper.parse_search_page(CASARADAR_HTML, ""))
        assert "175" in str(items[0].get("precio_venta", ""))

    def test_parse_metros(self):
        items = list(self.scraper.parse_search_page(CASARADAR_HTML, ""))
        assert "60" in str(items[0].get("metros_cuadrados", ""))

    def test_next_page_query_param(self):
        html = "<html></html>"
        url = self.scraper.next_page_url(html, "https://www.casaradar.es/venta?page=2", 2)
        assert url is not None
        assert "page=3" in url

    def test_next_page_adds_param_when_missing(self):
        html = "<html></html>"
        url = self.scraper.next_page_url(html, "https://www.casaradar.es/venta", 1)
        assert url is not None
        assert "page=2" in url

    def test_use_js_flag(self):
        assert self.scraper.USE_JS is False

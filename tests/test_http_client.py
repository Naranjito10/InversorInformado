"""Tests para scraper/http_client.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scraper.http_client import FetchError, _is_blocked, fetch_html, fetch_with_delay


# ---------------------------------------------------------------------------
# _is_blocked
# ---------------------------------------------------------------------------

class TestIsBlocked:
    def test_datadome(self):
        assert _is_blocked("<html>datadome challenge</html>")

    def test_captcha(self):
        assert _is_blocked("<html>captcha required</html>")

    def test_acceso_restringido(self):
        assert _is_blocked("<html>acceso restringido</html>")

    def test_challenge_short_page(self):
        assert _is_blocked("<html>challenge</html>")

    def test_challenge_long_page_not_blocked(self):
        # Una pagina real puede contener 'challenge' en el contenido sin ser un bloqueo
        large_html = "<html>" + "challenge " * 2000 + "contenido real</html>"
        assert not _is_blocked(large_html)

    def test_normal_page_not_blocked(self):
        assert not _is_blocked("<html><body><article class='item'>Piso en Madrid</article></body></html>")


# ---------------------------------------------------------------------------
# fetch_html via Scrapling Fetcher (HTTP)
# ---------------------------------------------------------------------------

class TestFetchHtmlHttp:
    def test_success_via_fetcher(self):
        mock_page = MagicMock()
        mock_page.html_content = "<html>contenido ok</html>"

        with patch("scraper.http_client._HAS_SCRAPLING", True), \
             patch("scraper.http_client.Fetcher") as mock_fetcher:
            mock_fetcher.get.return_value = mock_page
            result = fetch_html("https://example.com", use_js=False)

        assert result == "<html>contenido ok</html>"
        mock_fetcher.get.assert_called_once()

    def test_fetcher_blocked_falls_back_to_js(self):
        mock_http_page = MagicMock()
        mock_http_page.html_content = "<html>datadome</html>"

        with patch("scraper.http_client._HAS_SCRAPLING", True), \
             patch("scraper.http_client.Fetcher") as mock_fetcher, \
             patch("scraper.http_client._fetch_js", return_value="<html>contenido real</html>") as mock_js:
            mock_fetcher.get.return_value = mock_http_page
            result = fetch_html("https://example.com", use_js=False)

        assert result == "<html>contenido real</html>"
        mock_js.assert_called_once()

    def test_fetcher_exception_falls_back_to_js_on_403(self):
        with patch("scraper.http_client._HAS_SCRAPLING", True), \
             patch("scraper.http_client.Fetcher") as mock_fetcher, \
             patch("scraper.http_client._fetch_js", return_value="<html>ok via js</html>") as mock_js:
            mock_fetcher.get.side_effect = Exception("403 Forbidden")
            result = fetch_html("https://example.com", use_js=False)

        assert result == "<html>ok via js</html>"
        mock_js.assert_called_once()

    def test_fetcher_non_block_exception_raises_fetch_error(self):
        with patch("scraper.http_client._HAS_SCRAPLING", True), \
             patch("scraper.http_client.Fetcher") as mock_fetcher:
            mock_fetcher.get.side_effect = Exception("Connection timeout")
            with pytest.raises(FetchError, match="Connection timeout"):
                fetch_html("https://example.com", use_js=False)

    def test_no_scrapling_no_httpx_raises(self):
        with patch("scraper.http_client._HAS_SCRAPLING", False), \
             patch("scraper.http_client._HAS_HTTPX", False):
            with pytest.raises(FetchError, match="Ni scrapling ni httpx"):
                fetch_html("https://example.com", use_js=False)


# ---------------------------------------------------------------------------
# fetch_html via StealthySession (JS)
# ---------------------------------------------------------------------------

class TestFetchHtmlJs:
    def test_success_via_stealth_session(self):
        mock_page = MagicMock()
        mock_page.html_content = "<html>js rendered</html>"
        mock_session = MagicMock()
        mock_session.fetch.return_value = mock_page

        with patch("scraper.http_client._HAS_SCRAPLING", True), \
             patch("scraper.http_client._get_stealth_session", return_value=mock_session):
            result = fetch_html("https://idealista.com/...", use_js=True)

        assert result == "<html>js rendered</html>"
        mock_session.fetch.assert_called_once_with("https://idealista.com/...")

    def test_stealth_none_response_raises(self):
        mock_session = MagicMock()
        mock_session.fetch.return_value = None

        with patch("scraper.http_client._HAS_SCRAPLING", True), \
             patch("scraper.http_client._get_stealth_session", return_value=mock_session):
            with pytest.raises(FetchError, match="vacia"):
                fetch_html("https://example.com", use_js=True)

    def test_no_scrapling_raises(self):
        with patch("scraper.http_client._HAS_SCRAPLING", False):
            with pytest.raises(FetchError, match="scrapling no instalado"):
                fetch_html("https://example.com", use_js=True)


# ---------------------------------------------------------------------------
# fetch_with_delay
# ---------------------------------------------------------------------------

class TestFetchWithDelay:
    def test_returns_html_on_success(self):
        with patch("scraper.http_client.fetch_html", return_value="<html/>"), \
             patch("scraper.http_client.random_delay"):
            result = fetch_with_delay("https://example.com")
        assert result == "<html/>"

    def test_returns_none_on_fetch_error(self):
        with patch("scraper.http_client.fetch_html", side_effect=FetchError("fail")), \
             patch("scraper.http_client.random_delay"):
            result = fetch_with_delay("https://example.com")
        assert result is None

    def test_delay_called_on_success(self):
        with patch("scraper.http_client.fetch_html", return_value="<html/>"), \
             patch("scraper.http_client.random_delay") as mock_delay:
            fetch_with_delay("https://example.com")
        mock_delay.assert_called_once()

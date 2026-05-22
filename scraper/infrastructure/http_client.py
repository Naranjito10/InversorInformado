"""Cliente HTTP anti-ban usando Scrapling (Fetcher + StealthyFetcher)."""
from __future__ import annotations

import atexit
import random
import time
from typing import Optional

from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_exponential,
)

from .config import config
from .logger import get_logger

log = get_logger("http")

# ---------------------------------------------------------------------------
# Imports opcionales con degradacion graceful
# ---------------------------------------------------------------------------

try:
    from scrapling.fetchers import Fetcher, StealthyFetcher, StealthySession
    _HAS_SCRAPLING = True
except ImportError:
    _HAS_SCRAPLING = False
    Fetcher = None  # type: ignore
    StealthyFetcher = None  # type: ignore
    StealthySession = None  # type: ignore
    log.warning("scrapling_not_installed", extra={"detail": "pip install 'scrapling[all]'"})

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    httpx = None  # type: ignore

# ---------------------------------------------------------------------------
# Sesion persistente de navegador (reutiliza Chromium entre peticiones JS)
# ---------------------------------------------------------------------------

_stealth_session: Optional["StealthySession"] = None


def _get_stealth_session() -> "StealthySession":
    """Abre el navegador la primera vez y lo reutiliza en el resto del ciclo."""
    global _stealth_session
    if _stealth_session is None:
        log.info("browser_session_start")
        _stealth_session = StealthySession(headless=True)
        _stealth_session.__enter__()
        atexit.register(_close_stealth_session)
    return _stealth_session


def _close_stealth_session() -> None:
    global _stealth_session
    if _stealth_session is not None:
        try:
            _stealth_session.__exit__(None, None, None)
            log.info("browser_session_closed")
        except Exception:
            pass
        _stealth_session = None


# ---------------------------------------------------------------------------
# User-agent y proxy
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def get_user_agent() -> str:
    try:
        from fake_useragent import UserAgent
        return UserAgent().random
    except Exception:
        return random.choice(DEFAULT_USER_AGENTS)


def get_proxy() -> Optional[str]:
    if not config.scraper.proxies:
        return None
    return random.choice(config.scraper.proxies)


def random_delay() -> None:
    time.sleep(random.uniform(config.scraper.delay_min, config.scraper.delay_max))


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class FetchError(Exception):
    """Error recuperable al descargar una URL."""


# ---------------------------------------------------------------------------
# Fetch principal
# ---------------------------------------------------------------------------

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type(FetchError),
)
def fetch_html(url: str, use_js: bool = False, timeout: int = 30) -> str:
    """
    Descarga HTML de una URL.

    - use_js=False → Fetcher (HTTP rápido con fingerprinting de Chrome)
    - use_js=True  → StealthySession (Chromium headless, bypassea DataDome/Cloudflare)

    Raises:
        FetchError: si todos los reintentos fallan.
    """
    proxy = get_proxy()
    log.debug("fetch_start", extra={"url": url, "use_js": use_js, "proxy": bool(proxy)})

    if use_js:
        return _fetch_js(url, proxy=proxy, timeout=timeout)
    return _fetch_http(url, proxy=proxy, timeout=timeout)


def _fetch_js(url: str, proxy: Optional[str], timeout: int) -> str:
    """Chromium headless via StealthySession (sesion persistente)."""
    if not _HAS_SCRAPLING:
        raise FetchError("scrapling no instalado: pip install 'scrapling[all]'")
    try:
        log.info("stealth_fetch", extra={"url": url})
        session = _get_stealth_session()
        kwargs: dict = {}
        if proxy:
            kwargs["proxy"] = proxy
        page = session.fetch(url, **kwargs)
        if page is None:
            raise FetchError(f"StealthySession devolvio respuesta vacia: {url}")
        return page.html_content
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"StealthySession error [{url}]: {exc}") from exc


def _fetch_http(url: str, proxy: Optional[str], timeout: int) -> str:
    """HTTP rapido via Scrapling Fetcher (fingerprint Chrome, sin JS)."""
    if _HAS_SCRAPLING:
        try:
            kwargs: dict = {"stealthy_headers": True, "timeout": timeout}
            if proxy:
                kwargs["proxy"] = proxy
            page = Fetcher.get(url, **kwargs)
            if page is None:
                raise FetchError(f"Fetcher devolvio respuesta vacia: {url}")
            html = page.html_content
            # Detectar bloqueo suave (pagina de desafio sin error HTTP)
            if _is_blocked(html):
                log.warning("soft_block_detected_fallback_js", extra={"url": url})
                return _fetch_js(url, proxy=proxy, timeout=timeout)
            return html
        except FetchError:
            raise
        except Exception as exc:
            exc_str = str(exc)
            if any(code in exc_str for code in ("403", "429", "forbidden", "blocked")):
                log.warning("http_blocked_fallback_js", extra={"url": url, "error": exc_str})
                return _fetch_js(url, proxy=proxy, timeout=timeout)
            raise FetchError(f"Fetcher error [{url}]: {exc}") from exc

    # Fallback final: httpx (sin fingerprinting, ultimo recurso)
    if not _HAS_HTTPX:
        raise FetchError("Ni scrapling ni httpx disponibles. Instala scrapling[all].")
    return _fetch_httpx(url, proxy=proxy, timeout=timeout)


def _fetch_httpx(url: str, proxy: Optional[str], timeout: int) -> str:
    headers = {
        "User-Agent": get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
    }
    proxies = {"http://": proxy, "https://": proxy} if proxy else None
    try:
        with httpx.Client(
            headers=headers, timeout=timeout, proxies=proxies,
            follow_redirects=True, http2=True,
        ) as client:
            r = client.get(url)
            if r.status_code in (403, 429):
                raise FetchError(f"Bloqueado {r.status_code}: {url}")
            if r.status_code >= 400:
                raise FetchError(f"HTTP {r.status_code}: {url}")
            return r.text
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(str(exc)) from exc


def _is_blocked(html: str) -> bool:
    """Detecta paginas de desafio sin error HTTP (DataDome, Cloudflare, Imperva, etc.)."""
    lower = html.lower()
    return (
        "datadome" in lower
        or "check.datadome.co" in lower
        or ("challenge" in lower and len(html) < 10_000)
        or "captcha" in lower
        or "ddg-captcha" in lower          # DataDome challenge page class
        or "validate your request" in lower  # DataDome message
        or "acceso restringido" in lower
        or "verificar que no eres un robot" in lower
        or "pardon our interruption" in lower  # Imperva/Incapsula
        or ("sorry, you have been blocked" in lower and len(html) < 15_000)
        or ("access denied" in lower and len(html) < 10_000)
        or "robot_check" in lower
    )


# ---------------------------------------------------------------------------
# Funcion publica con delay (interfaz usada por BaseScraper)
# ---------------------------------------------------------------------------

def fetch_with_delay(url: str, use_js: bool = False) -> Optional[str]:
    """Fetch + delay aleatorio. Devuelve None si falla tras todos los reintentos."""
    try:
        html = fetch_html(url, use_js=use_js)
        random_delay()
        return html
    except FetchError as e:
        log.error("fetch_failed", extra={"url": url, "error": str(e)})
        return None
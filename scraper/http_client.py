"""Cliente HTTP con anti-ban: rotacion de UA, delays aleatorios, proxies."""
from __future__ import annotations

import random
import time
from typing import Optional

from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_exponential
)

from .config import config
from .logger import get_logger

log = get_logger("http")

# Lazy imports para evitar fallar si Scrapling no esta instalado
try:
    from scrapling.fetchers import StealthyFetcher, Fetcher  # type: ignore
    _HAS_SCRAPLING = True
except ImportError:
    _HAS_SCRAPLING = False
    StealthyFetcher = None  # type: ignore
    Fetcher = None  # type: ignore

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    httpx = None  # type: ignore

try:
    from fake_useragent import UserAgent
    _UA = UserAgent()
    _HAS_UA = True
except Exception:
    _HAS_UA = False
    _UA = None


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
    if config.scraper.user_agent_rotate and _HAS_UA:
        try:
            return _UA.random
        except Exception:
            pass
    return random.choice(DEFAULT_USER_AGENTS)


def get_proxy() -> Optional[str]:
    if not config.scraper.proxies:
        return None
    return random.choice(config.scraper.proxies)


def random_delay() -> None:
    """Pausa aleatoria entre peticiones para no levantar sospechas."""
    delay = random.uniform(config.scraper.delay_min, config.scraper.delay_max)
    time.sleep(delay)


class FetchError(Exception):
    """Error recuperable al descargar una URL."""


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type(FetchError),
)
def fetch_html(url: str, use_js: bool = False, timeout: int = 30) -> str:
    """
    Descarga HTML de una URL.

    Args:
        url: URL absoluta.
        use_js: True para usar Scrapling/StealthyFetcher (paginas con JS pesado).
        timeout: segundos.

    Returns:
        HTML como str.

    Raises:
        FetchError: si todos los reintentos fallan.
    """
    ua = get_user_agent()
    proxy = get_proxy()

    log.debug("fetch_start", extra={"url": url, "use_js": use_js, "proxy": bool(proxy)})

    try:
        if use_js and _HAS_SCRAPLING:
            # StealthyFetcher es bueno contra Cloudflare/JS challenges
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                network_idle=True,
                timeout=timeout * 1000,
                google_search=False,
            )
            if page is None or page.status not in (200, 304):
                raise FetchError(f"Status {getattr(page, 'status', '?')}: {url}")
            return page.html_content

        # Fallback: httpx (rapido, sin JS)
        if not _HAS_HTTPX:
            raise FetchError("httpx no instalado y scrapling no disponible para esta URL")

        headers = {
            "User-Agent": ua,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        proxies = {"http://": proxy, "https://": proxy} if proxy else None

        with httpx.Client(
            headers=headers,
            timeout=timeout,
            proxies=proxies,
            follow_redirects=True,
            http2=True,
        ) as client:
            r = client.get(url)
            if r.status_code == 403 or r.status_code == 429:
                # Probablemente bloqueado -> reintentar con JS
                if not use_js and _HAS_SCRAPLING:
                    log.warning(
                        "blocked_fallback_to_js",
                        extra={"url": url, "status": r.status_code},
                    )
                    return fetch_html(url, use_js=True, timeout=timeout)
                raise FetchError(f"Bloqueado {r.status_code}: {url}")
            if r.status_code >= 400:
                raise FetchError(f"Status {r.status_code}: {url}")
            return r.text

    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("fetch_exception", extra={"url": url, "error": str(exc)})
        raise FetchError(str(exc)) from exc


def fetch_with_delay(url: str, use_js: bool = False) -> Optional[str]:
    """Fetch + delay aleatorio. Devuelve None si falla tras los reintentos."""
    try:
        html = fetch_html(url, use_js=use_js)
        random_delay()
        return html
    except FetchError as e:
        log.error("fetch_failed", extra={"url": url, "error": str(e)})
        return None

"""
PhotoEnricher — descarga fotos del portal y las sube a Supabase Storage.

Flujo:
  1. Lee foto_urls del listing (URLs del portal, extraídas por el scraper).
  2. Descarga cada foto vía httpx.
  3. Sube al bucket "listing-photos" en Supabase Storage.
  4. Escribe las URLs públicas en enrichment_meta["fotos"]["urls"].

Solo corre sobre pisos con score >= enrichment_threshold_cheap (configurable).
Registra fallos en enrichment_meta["photos_failed_at"] para no reintentar 7 días.

Prerequisito: bucket "listing-photos" creado en Supabase Storage (público).
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, timezone

import httpx

from scraper.infrastructure import db
from scraper.infrastructure.config import config
from .base import BaseEnricher

log = logging.getLogger(__name__)

_BUCKET = "listing-photos"
_MAX_PHOTOS = 10
_DOWNLOAD_SLEEP = 0.5
_PHOTO_RETRY_DAYS = 7


def _guess_ext(url: str, content_type: str) -> str:
    for ext in (".png", ".webp", ".jpeg", ".jpg"):
        if ext in url.lower():
            return ext
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    return ".jpg"


class PhotoEnricher(BaseEnricher):
    name = "photos"

    def needs_enrichment(self, listing_row: dict) -> bool:
        if not listing_row.get("foto_urls"):
            return False
        meta = listing_row.get("enrichment_meta") or {}
        if "fotos" in meta:
            return False
        failed_at_str = meta.get("photos_failed_at")
        if failed_at_str:
            try:
                failed_at = datetime.fromisoformat(failed_at_str)
                if (datetime.now(timezone.utc) - failed_at).days < _PHOTO_RETRY_DAYS:
                    return False
            except (ValueError, TypeError):
                pass
        return True

    def enrich(self, listing_row: dict) -> dict:
        listing_id = listing_row.get("id")
        foto_urls = listing_row.get("foto_urls") or []
        if not foto_urls:
            return {}

        client = db.get_client()
        if client is None:
            return {}

        base_url = (config.supabase.url or "").rstrip("/")
        stored_urls: list[str] = []

        for i, url in enumerate(foto_urls[:_MAX_PHOTOS]):
            try:
                resp = httpx.get(url, timeout=15, follow_redirects=True)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "image/jpeg")
                ext = _guess_ext(url, content_type)
                path = f"{listing_id}/{i}{ext}"
                client.storage.from_(_BUCKET).upload(
                    path=path,
                    file=resp.content,
                    file_options={"content-type": content_type, "upsert": "true"},
                )
                public_url = f"{base_url}/storage/v1/object/public/{_BUCKET}/{path}"
                stored_urls.append(public_url)
                time.sleep(_DOWNLOAD_SLEEP)
            except Exception as exc:  # noqa: BLE001
                log.warning("photo_download_failed", extra={"url": url, "id": listing_id, "error": str(exc)})

        if stored_urls:
            db.merge_enrichment_meta(listing_id, {
                "fotos": {
                    "urls": stored_urls,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "count": len(stored_urls),
                }
            })
            log.info("photos_stored", extra={"id": listing_id, "count": len(stored_urls)})
        else:
            db.merge_enrichment_meta(listing_id, {
                "photos_failed_at": datetime.now(timezone.utc).isoformat()
            })
            log.warning("photos_all_failed", extra={"id": listing_id})

        return {}

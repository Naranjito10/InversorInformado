"""Runner principal: ejecuta un ciclo completo de scraping."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .alerts import notify_opportunity, should_alert
from .config import config
from .db import get_existing, mark_inactive, upsert_listing
from .logger import get_logger
from .models import Listing
from .scorer import calcular_score, contar_campos_vacios
from .scrapers import get_scraper

log = get_logger("runner")


@dataclass
class RunStats:
    total_targets: int = 0
    total_scraped: int = 0
    total_new: int = 0
    total_updated: int = 0
    total_alerts: int = 0
    total_errors: int = 0
    errors: list[dict] = field(default_factory=list)


def _enrich_local_score(listing: Listing) -> Listing:
    """Aplica scoring en Python (espejo del SQL) por si la BD no es Supabase."""
    listing.campos_vacios = contar_campos_vacios(listing)
    # precio_m2
    if (listing.precio_m2 is None and listing.precio_venta
            and listing.metros_cuadrados and listing.metros_cuadrados > 0):
        listing.precio_m2 = round(listing.precio_venta / listing.metros_cuadrados)
    # rentabilidad bruta
    if (listing.rentabilidad_bruta is None and listing.alquiler_estimado
            and listing.precio_venta and listing.precio_venta > 0):
        listing.rentabilidad_bruta = round(
            (listing.alquiler_estimado * 12 / listing.precio_venta) * 100, 2
        )
    # descuento zona
    if (listing.descuento_zona_pct is None and listing.precio_m2
            and listing.precio_zona_m2 and listing.precio_zona_m2 > 0):
        listing.descuento_zona_pct = round(
            ((listing.precio_m2 - listing.precio_zona_m2) / listing.precio_zona_m2) * 100, 2
        )
    score, label = calcular_score(listing)
    listing.score = score
    listing.score_label = label
    return listing


def run_target(target: dict, stats: RunStats) -> None:
    """Procesa un target (un searchUrl de una fuente concreta)."""
    source = target["source"]
    url = target["url"]
    max_pages = target.get("max_pages", config.scraper.max_pages_per_search)

    log.info("target_start", extra={"source": source, "url": url, "max_pages": max_pages})

    try:
        scraper = get_scraper(source)
    except ValueError as e:
        log.error("scraper_not_found", extra={"source": source, "error": str(e)})
        stats.errors.append({"source": source, "error": str(e)})
        stats.total_errors += 1
        return

    try:
        result = scraper.scrape_search(url, max_pages=max_pages)
    except Exception as exc:  # noqa: BLE001
        log.error(
            "scrape_failed",
            extra={"source": source, "url": url, "error": str(exc)},
            exc_info=True,
        )
        stats.errors.append({"source": source, "url": url, "error": str(exc)})
        stats.total_errors += 1
        return

    stats.total_scraped += result.count
    stats.total_errors += len(result.errors)
    stats.errors.extend(result.errors)

    seen_urls: set[str] = set()
    for listing in result.listings:
        seen_urls.add(listing.url)
        try:
            existed_before = get_existing(listing.url) is not None
            _enrich_local_score(listing)

            saved = upsert_listing(listing)
            if saved is None:
                continue

            if existed_before:
                stats.total_updated += 1
            else:
                stats.total_new += 1

            # Alertar segun reglas
            if should_alert(saved, was_new=not existed_before):
                notify_opportunity(saved)
                stats.total_alerts += 1
                log.info(
                    "alert_sent",
                    extra={
                        "url": listing.url,
                        "score": saved.get("score"),
                        "new": not existed_before,
                    },
                )

        except Exception as exc:  # noqa: BLE001
            log.error(
                "process_listing_failed",
                extra={"url": listing.url, "error": str(exc)},
            )
            stats.errors.append({"url": listing.url, "error": str(exc)})
            stats.total_errors += 1

    # Marcar como inactivos los que ya no aparecen.
    # Solo si SCRAPER_MARK_INACTIVE=true Y el scraper cubrió todas las páginas del target.
    if config.scraper.mark_inactive and seen_urls and result.pages_fetched > 0:
        mark_inactive(seen_urls, source)


def run_cycle() -> RunStats:
    """Ejecuta un ciclo completo: itera por todos los targets configurados."""
    config.validate()
    log.info("cycle_start")
    targets = config.load_search_targets()
    stats = RunStats(total_targets=len(targets))

    if not targets:
        log.warning("no_targets_configured")
        return stats

    for target in targets:
        try:
            run_target(target, stats)
        except Exception as exc:  # noqa: BLE001
            log.error("target_unhandled_error", extra={"target": target, "error": str(exc)})
            stats.errors.append({"target": target.get("name"), "error": str(exc)})
            stats.total_errors += 1

    log.info(
        "cycle_done",
        extra={
            "targets": stats.total_targets,
            "scraped": stats.total_scraped,
            "new": stats.total_new,
            "updated": stats.total_updated,
            "alerts": stats.total_alerts,
            "errors": stats.total_errors,
        },
    )
    return stats


if __name__ == "__main__":
    run_cycle()

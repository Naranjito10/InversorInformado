"""Runner principal: ejecuta un ciclo completo de scraping."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .services.alerts import notify_opportunity, should_alert
from .infrastructure.config import config
from .infrastructure.db import find_near_duplicate, get_existing, mark_inactive, upsert_listing
from .infrastructure.logger import get_logger
from .models import Listing
from .services.scorer import calcular_score, contar_campos_vacios
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


def _price_in_range(
    listing: Listing, price_min: Optional[int], price_max: Optional[int]
) -> bool:
    """Listings sin precio conocido se conservan; resto se filtran por rango."""
    if listing.precio_venta is None:
        return True
    if price_min is not None and listing.precio_venta < price_min:
        return False
    if price_max is not None and listing.precio_venta > price_max:
        return False
    return True


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


def run_target(target: dict, stats: RunStats) -> Optional[set[str]]:
    """Procesa un target (un searchUrl de una fuente concreta)."""
    source = target["source"]
    url = target["url"]
    max_pages = target.get("max_pages", config.scraper.max_pages_per_search)
    max_results = target.get("max_results", 100)

    log.info("target_start", extra={"source": source, "url": url,
                                    "max_pages": max_pages, "max_results": max_results})

    try:
        scraper = get_scraper(source)
    except ValueError as e:
        log.error("scraper_not_found", extra={"source": source, "error": str(e)})
        stats.errors.append({"source": source, "error": str(e)})
        stats.total_errors += 1
        return

    try:
        result = scraper.scrape_search(url, max_pages=max_pages, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        log.error(
            "scrape_failed",
            extra={"source": source, "url": url, "error": str(exc)},
            exc_info=True,
        )
        stats.errors.append({"source": source, "url": url, "error": str(exc)})
        stats.total_errors += 1
        return

    # Aplicar filtro de precio (post-scraping universal: funciona en todos los portales)
    filters = target.get("filters", {})
    price_min: Optional[int] = filters.get("price_min")
    price_max: Optional[int] = filters.get("price_max")
    if price_min is not None or price_max is not None:
        before = len(result.listings)
        result.listings = [l for l in result.listings if _price_in_range(l, price_min, price_max)]
        removed = before - len(result.listings)
        if removed:
            log.info("price_filter", extra={"removed": removed, "kept": len(result.listings),
                                            "min": price_min, "max": price_max})

    stats.total_scraped += result.count
    stats.total_errors += len(result.errors)
    stats.errors.extend(result.errors)

    seen_urls: set[str] = set()
    for listing in result.listings:
        seen_urls.add(listing.url)
        try:
            existed_before = get_existing(listing.url) is not None
            _enrich_local_score(listing)

            if not existed_before:
                near_dup = find_near_duplicate(listing)
                if near_dup:
                    listing.status = "pendiente_revision"
                    listing.duplicate_candidate_of = near_dup["url"]
                    log.info(
                        "duplicate_candidate_detected",
                        extra={"url": listing.url, "similar_to": near_dup["url"]},
                    )

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

    # Devolver URLs vistas para que run_cycle las acumule por fuente.
    return seen_urls if (config.scraper.mark_inactive and result.pages_fetched > 0) else None


def run_targets(targets: list[dict]) -> RunStats:
    """Ejecuta un ciclo con los targets proporcionados (e.g. desde webhook)."""
    stats = RunStats(total_targets=len(targets))
    if not targets:
        log.warning("no_targets_provided")
        return stats

    disabled = {s.lower() for s in (config.scraper.disabled_sources or [])}
    seen_urls_by_source: dict[str, set[str]] = {}
    for target in targets:
        if target.get("source", "").lower() in disabled:
            log.info("target_skipped_disabled", extra={"source": target.get("source")})
            continue
        try:
            seen = run_target(target, stats)
            if seen is not None:
                source = target["source"]
                seen_urls_by_source.setdefault(source, set()).update(seen)
        except Exception as exc:  # noqa: BLE001
            log.error("target_unhandled_error", extra={"target": target, "error": str(exc)})
            stats.errors.append({"target": target.get("name"), "error": str(exc)})
            stats.total_errors += 1

    for source, seen_urls in seen_urls_by_source.items():
        mark_inactive(seen_urls, source)

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


def run_cycle() -> RunStats:
    """Ejecuta un ciclo completo: itera por todos los targets configurados."""
    config.validate()
    log.info("cycle_start")
    targets = config.load_search_targets()
    stats = RunStats(total_targets=len(targets))

    if not targets:
        log.warning("no_targets_configured")
        return stats

    disabled = {s.lower() for s in (config.scraper.disabled_sources or [])}
    seen_urls_by_source: dict[str, set[str]] = {}
    for target in targets:
        if target.get("source", "").lower() in disabled:
            log.info("target_skipped_disabled", extra={"source": target.get("source")})
            continue
        try:
            seen = run_target(target, stats)
            if seen is not None:
                source = target["source"]
                seen_urls_by_source.setdefault(source, set()).update(seen)
        except Exception as exc:  # noqa: BLE001
            log.error("target_unhandled_error", extra={"target": target, "error": str(exc)})
            stats.errors.append({"target": target.get("name"), "error": str(exc)})
            stats.total_errors += 1

    # mark_inactive una vez por fuente con todas sus URLs vistas en el ciclo
    for source, seen_urls in seen_urls_by_source.items():
        mark_inactive(seen_urls, source)

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

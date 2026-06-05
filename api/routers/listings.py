from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Query
from api.schemas import (
    BulkImportRequest, BulkImportResult, CheckUrlsRequest,
    ListingOut, ManualListingIn, StatsOut,
)
from api.services import listings_service

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=list[ListingOut])
def get_listings(
    municipio: Optional[str] = Query(None),
    barrio: Optional[str] = Query(None),
    fuente: Optional[str] = Query(None),
    score_label: Optional[str] = Query(None),
    score_min: Optional[int] = Query(None),
    precio_min: Optional[int] = Query(None),
    precio_max: Optional[int] = Query(None),
    solo_activos: bool = Query(True),
    limit: int = Query(200, le=500),
    q: Optional[str] = Query(None),
):
    filters: dict = {"activo": solo_activos}
    if q:
        filters["q"] = q
    elif municipio:
        filters["municipio"] = municipio
    if barrio and not q:
        filters["barrio"] = barrio
    if fuente:
        filters["fuente"] = fuente
    if score_label:
        filters["score_label"] = score_label
    if score_min is not None:
        filters["score_min"] = score_min
    if precio_min is not None:
        filters["precio_min"] = precio_min
    if precio_max is not None:
        filters["precio_max"] = precio_max

    return listings_service.get_listings(filters=filters, limit=limit)


@router.post("/manual")
def create_manual(body: ManualListingIn):
    return listings_service.create_manual_listing(body.model_dump(exclude_none=True))


@router.post("/check-urls")
def check_urls(body: CheckUrlsRequest):
    return listings_service.check_urls_exist(body.urls)


@router.post("/bulk", response_model=BulkImportResult)
def bulk_import(body: BulkImportRequest):
    return listings_service.bulk_import_listings(
        [item.model_dump(exclude_none=True) for item in body.listings]
    )


@router.get("/pending-review")
def get_pending_review(limit: int = Query(100, le=200)):
    return listings_service.get_pending_review(limit=limit)


@router.post("/{listing_id}/approve")
def approve_listing(listing_id: str):
    ok = listings_service.approve_listing(listing_id)
    return {"ok": ok}


@router.post("/{listing_id}/reject")
def reject_listing(listing_id: str):
    ok = listings_service.reject_listing(listing_id)
    return {"ok": ok}


@router.post("/{listing_id}/keep-new")
def keep_new_listing(listing_id: str):
    ok = listings_service.keep_new_listing(listing_id)
    return {"ok": ok}


@router.get("/stats", response_model=StatsOut)
def get_stats():
    return listings_service.get_stats()


@router.get("/zonas")
def get_zonas():
    return listings_service.get_zonas()
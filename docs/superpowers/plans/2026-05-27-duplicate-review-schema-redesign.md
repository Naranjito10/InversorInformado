# Duplicate Review UI + Schema Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `activo`/`pending_review` booleans with a rich `status` enum, add `condition`/`ocupacion`/`situacion_legal`/`disabled_reason` classification fields plus ~20 amenity fields, and redesign the duplicate review card to show both listings' details with three action buttons.

**Architecture:** Additive DB migration first (new columns, data backfill), then code changes that use the new schema, then a second migration to drop old columns. The review card is enriched at fetch time via a secondary query on `duplicate_candidate_of` URL.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Supabase (PostgreSQL via supabase-py), React 18, TypeScript, TanStack Query v5, Tailwind CSS.

---

## File Map

| File | Change |
|---|---|
| Supabase SQL editor | Add columns + backfill; later drop old columns |
| `scraper/models.py` | Replace `activo`/`pending_review`/`estado`; add ~24 new fields |
| `scraper/infrastructure/db.py` | Update all filter logic; add `keep_new_listing()` |
| `api/services/listings_service.py` | Add `keep_new_listing()` wrapper; update `get_stats` |
| `api/routers/listings.py` | Add `POST /{id}/keep-new` endpoint |
| `frontend/src/services/api.ts` | Update `PendingListing` type; add `keepNewListing()` |
| `frontend/src/pages/Review.tsx` | Redesign card: show original info, 3-button layout |
| `tests/test_models.py` | New: unit tests for model serialization |

---

## Task 1: DB Migration Step 1+2 — Add columns and backfill

**Files:**
- Run SQL via: Supabase Dashboard → SQL Editor

Additive — safe to run before any code changes. Old columns stay until Task 8.

- [ ] **Step 1: Open Supabase SQL Editor**

Navigate to your Supabase project → SQL Editor → New query.

- [ ] **Step 2: Run the additive migration**

```sql
-- Add new columns (safe while old code is still live)
ALTER TABLE listings
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'activo',
  ADD COLUMN IF NOT EXISTS condition TEXT,
  ADD COLUMN IF NOT EXISTS ocupacion TEXT,
  ADD COLUMN IF NOT EXISTS situacion_legal TEXT,
  ADD COLUMN IF NOT EXISTS disabled_reason TEXT,
  ADD COLUMN IF NOT EXISTS balcon BOOLEAN,
  ADD COLUMN IF NOT EXISTS trastero BOOLEAN,
  ADD COLUMN IF NOT EXISTS armarios_empotrados BOOLEAN,
  ADD COLUMN IF NOT EXISTS aire_acondicionado BOOLEAN,
  ADD COLUMN IF NOT EXISTS calefaccion BOOLEAN,
  ADD COLUMN IF NOT EXISTS calefaccion_tipo TEXT,
  ADD COLUMN IF NOT EXISTS cocina_equipada BOOLEAN,
  ADD COLUMN IF NOT EXISTS amueblado BOOLEAN,
  ADD COLUMN IF NOT EXISTS exterior BOOLEAN,
  ADD COLUMN IF NOT EXISTS orientacion TEXT,
  ADD COLUMN IF NOT EXISTS portero BOOLEAN,
  ADD COLUMN IF NOT EXISTS puerta_blindada BOOLEAN,
  ADD COLUMN IF NOT EXISTS doble_acristalamiento BOOLEAN,
  ADD COLUMN IF NOT EXISTS adaptado_movilidad BOOLEAN,
  ADD COLUMN IF NOT EXISTS jardin BOOLEAN,
  ADD COLUMN IF NOT EXISTS piscina BOOLEAN,
  ADD COLUMN IF NOT EXISTS piscina_comunitaria BOOLEAN,
  ADD COLUMN IF NOT EXISTS zonas_verdes_comunitarias BOOLEAN,
  ADD COLUMN IF NOT EXISTS vigilancia BOOLEAN,
  ADD COLUMN IF NOT EXISTS garaje_incluido BOOLEAN,
  ADD COLUMN IF NOT EXISTS num_plazas_garaje INTEGER;

-- Backfill status from existing boolean fields
UPDATE listings SET status = 'pendiente_revision' WHERE pending_review = TRUE;
UPDATE listings SET status = 'inactivo'           WHERE activo = FALSE AND pending_review = FALSE;
-- Rows with activo=TRUE, pending_review=FALSE already have status='activo' from DEFAULT

-- Backfill condition from existing estado field
UPDATE listings SET condition = 'obra_nueva'       WHERE estado = 'nuevo';
UPDATE listings SET condition = 'buen_estado'      WHERE estado = 'buen estado';
UPDATE listings SET condition = 'reforma_integral' WHERE estado = 'a reformar';
```

- [ ] **Step 3: Verify migration**

```sql
-- Counts per status — should see 'activo', possibly 'inactivo', 'pendiente_revision'
SELECT status, COUNT(*) FROM listings GROUP BY status;

-- Cross-check: active rows must match
SELECT COUNT(*) FROM listings WHERE status = 'activo';
SELECT COUNT(*) FROM listings WHERE activo = TRUE AND pending_review = FALSE;
-- Both queries must return the same number
```

- [ ] **Step 4: Record migration with empty commit**

```bash
git commit --allow-empty -m "chore: ran DB migration step 1+2 (additive — columns + backfill)"
```

---

## Task 2: Update `scraper/models.py`

**Files:**
- Modify: `scraper/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Create `tests/__init__.py` (empty) if it doesn't exist, then create `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd c:/Users/kein-/Desktop/Antigravity/RealStateAnalyse
python -m pytest tests/test_models.py -v
```

Expected: `ImportError` or `ValidationError` — `Listing` has no `status`/`condition` yet.

- [ ] **Step 3: Replace `scraper/models.py`**

```python
"""Modelos de dominio (Pydantic) para viviendas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator


class Listing(BaseModel):
    """Estructura unificada de vivienda. Coincide con la tabla `listings`."""

    # Identificacion
    url: str
    fuente: str
    titulo: Optional[str] = None

    # Precios
    precio_venta: Optional[int] = None
    ibi: Optional[int] = None
    comunidad: Optional[int] = None
    derramas_pendientes: Optional[int] = None
    precio_m2: Optional[int] = None

    # Caracteristicas fisicas
    metros_cuadrados: Optional[int] = None
    habitaciones: Optional[int] = None
    banos: Optional[int] = None
    planta: Optional[str] = None
    tipo_propiedad: Optional[str] = None

    # Extras — base
    ascensor: Optional[bool] = None
    terraza: Optional[bool] = None
    garaje: Optional[bool] = None
    garaje_incluido: Optional[bool] = None
    num_plazas_garaje: Optional[int] = None
    certificado_energetico: Optional[str] = None

    # Extras — interiores
    balcon: Optional[bool] = None
    trastero: Optional[bool] = None
    armarios_empotrados: Optional[bool] = None
    aire_acondicionado: Optional[bool] = None
    calefaccion: Optional[bool] = None
    calefaccion_tipo: Optional[str] = None
    cocina_equipada: Optional[bool] = None
    amueblado: Optional[bool] = None

    # Extras — edificio
    exterior: Optional[bool] = None
    orientacion: Optional[str] = None
    portero: Optional[bool] = None
    puerta_blindada: Optional[bool] = None
    doble_acristalamiento: Optional[bool] = None
    adaptado_movilidad: Optional[bool] = None

    # Extras — zonas exteriores / comunidad
    jardin: Optional[bool] = None
    piscina: Optional[bool] = None
    piscina_comunitaria: Optional[bool] = None
    zonas_verdes_comunitarias: Optional[bool] = None
    vigilancia: Optional[bool] = None

    # Clasificacion del inmueble
    # condition: obra_nueva | listo_para_usar | buen_estado | reforma_leve | reforma_integral | reforma_estructural
    condition: Optional[str] = None
    # ocupacion: libre | ocupado | alquilado | nuda_propiedad
    ocupacion: Optional[str] = None
    # situacion_legal: libre_cargas | con_hipoteca | en_construccion | renta_antigua | vpo | subasta | litigio | herencia
    situacion_legal: Optional[str] = None

    # Localizacion
    barrio: Optional[str] = None
    municipio: Optional[str] = None
    provincia: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    # Mercado / inversion
    alquiler_estimado: Optional[int] = None
    rentabilidad_alquiler: Optional[int] = None
    rentabilidad_bruta: Optional[float] = None
    precio_zona_m2: Optional[int] = None
    descuento_zona_pct: Optional[float] = None

    # Seguimiento
    dias_en_mercado: Optional[int] = None
    veces_visto: int = 1
    score: Optional[int] = None
    score_label: Optional[str] = None
    bajada_precio: bool = False
    campos_vacios: Optional[int] = None
    primera_deteccion: Optional[datetime] = None
    ultima_actualizacion: Optional[datetime] = None

    # Estado del registro en BD
    # status: activo | pendiente_revision | reservado | en_pausa | inactivo | descartado
    status: str = "activo"
    # disabled_reason: duplicado_nuevo_elegido | duplicado_antiguo_elegido | no_visto_scraper | revision_manual
    disabled_reason: Optional[str] = None

    # Deduplicacion
    duplicate_candidate_of: Optional[str] = None

    # Datos crudos para reparsear si hace falta
    raw_data: Optional[dict[str, Any]] = None

    @field_validator("certificado_energetico")
    @classmethod
    def _normalize_cee(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_up = v.upper().strip()
        if v_up and v_up[0] in "ABCDEFG":
            return v_up[0]
        return None

    def to_db_dict(self) -> dict[str, Any]:
        """Serializa para insertar en Supabase. Excluye None; preserva False y status."""
        data = self.model_dump(mode="json", exclude_none=False)
        return {
            k: v for k, v in data.items()
            if v is not None or k in {"status", "veces_visto", "bajada_precio"}
        }
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python -m pytest tests/test_models.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scraper/models.py tests/test_models.py tests/__init__.py
git commit -m "feat: replace activo/pending_review/estado with status/condition; add amenity fields"
```

---

## Task 3: Update `scraper/infrastructure/db.py` — filter and upsert logic

**Files:**
- Modify: `scraper/infrastructure/db.py`

- [ ] **Step 1: Update the INSERT branch of `upsert_listing` (lines ~79-90)**

Remove `payload["activo"] = True` — `status="activo"` is already in payload from `to_db_dict()`. The insert block becomes:

```python
        if existing is None:
            payload["primera_deteccion"] = now
            payload["ultima_actualizacion"] = now
            payload["veces_visto"] = 1
            res = client.table("listings").insert(payload).execute()
            log.info(
                "listing_inserted",
                extra={"url": listing.url, "fuente": listing.fuente,
                       "precio": listing.precio_venta},
            )
            return res.data[0] if res.data else None
```

- [ ] **Step 2: Update the UPDATE branch of `upsert_listing` (lines ~93-125)**

Replace the update branch:

```python
        # Actualizacion
        update_payload = {**payload}
        update_payload["veces_visto"] = (existing.get("veces_visto") or 1) + 1
        update_payload["ultima_actualizacion"] = now

        # Never overwrite these on re-scrape — preserve manually-set state
        update_payload.pop("status", None)
        update_payload.pop("disabled_reason", None)
        update_payload.pop("duplicate_candidate_of", None)
        update_payload.pop("primera_deteccion", None)

        old_price = existing.get("precio_venta")
        new_price = listing.precio_venta
        if old_price and new_price and new_price < old_price:
            update_payload["bajada_precio"] = True

        res = (
            client.table("listings")
            .update(update_payload)
            .eq("url", listing.url)
            .execute()
        )
        log.info(
            "listing_updated",
            extra={
                "url": listing.url,
                "fuente": listing.fuente,
                "old_price": old_price,
                "new_price": new_price,
            },
        )
        return res.data[0] if res.data else None
```

- [ ] **Step 3: Update `find_near_duplicate`**

Replace the two filter lines:
```python
            .eq("activo", True)
            .eq("pending_review", False)
```
With:
```python
            .eq("status", "activo")
```

- [ ] **Step 4: Update `mark_inactive`**

Replace the query and update inside `mark_inactive`:

```python
        existing = (
            client.table("listings")
            .select("id,url")
            .eq("fuente", source)
            .eq("status", "activo")
            .execute()
        )
        to_deactivate = [
            row["id"] for row in (existing.data or [])
            if row["url"] not in urls_seen
        ]
        if not to_deactivate:
            return 0
        client.table("listings").update({
            "status": "inactivo",
            "disabled_reason": "no_visto_scraper",
        }).in_("id", to_deactivate).execute()
        log.info("listings_deactivated", extra={"fuente": source, "count": len(to_deactivate)})
        return len(to_deactivate)
```

- [ ] **Step 5: Replace `get_pending_review_listings`**

```python
def get_pending_review_listings(limit: int = 100) -> list[dict]:
    """Devuelve anuncios pendientes de revisión, enriquecidos con datos del original."""
    client = get_client()
    if client is None:
        return []
    try:
        res = (
            client.table("listings")
            .select("*")
            .eq("status", "pendiente_revision")
            .order("primera_deteccion", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        for row in rows:
            original_url = row.get("duplicate_candidate_of")
            row["original_info"] = None
            if original_url:
                try:
                    orig = (
                        client.table("listings")
                        .select("titulo,precio_venta,metros_cuadrados,habitaciones,barrio,municipio,primera_deteccion,url")
                        .eq("url", original_url)
                        .limit(1)
                        .execute()
                    )
                    row["original_info"] = orig.data[0] if orig.data else None
                except Exception:
                    pass
        return rows
    except Exception as exc:
        log.error("db_query_failed", extra={"error": str(exc)})
        return []
```

- [ ] **Step 6: Update `approve_pending`**

Replace the update payload:

```python
        client.table("listings").update({
            "status": "activo",
            "duplicate_candidate_of": None,
        }).eq("id", listing_id).execute()
        log.info("listing_approved", extra={"id": listing_id})
        return True
```

- [ ] **Step 7: Update `reject_pending`**

Replace the update payload:

```python
        client.table("listings").update({
            "status": "descartado",
            "disabled_reason": "duplicado_antiguo_elegido",
        }).eq("id", listing_id).execute()
        log.info("listing_rejected", extra={"id": listing_id})
        return True
```

- [ ] **Step 8: Update `get_high_score_listings`**

Replace `.eq("activo", True)` with `.eq("status", "activo")`.

- [ ] **Step 9: Update `query_listings`**

Replace the `activo` filter block:

```python
        if "activo" in filters:
            if filters["activo"]:
                q = q.eq("status", "activo")
```

- [ ] **Step 10: Run unit tests to confirm no regressions**

```bash
python -m pytest tests/test_models.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 11: Commit**

```bash
git add scraper/infrastructure/db.py
git commit -m "feat: update db layer — status filters, upsert safety, enriched pending-review"
```

---

## Task 4: Add `keep_new_listing` — DB, service, and router

**Files:**
- Modify: `scraper/infrastructure/db.py`
- Modify: `api/services/listings_service.py`
- Modify: `api/routers/listings.py`

- [ ] **Step 1: Add `keep_new_listing` to `scraper/infrastructure/db.py`**

Add this function after `reject_pending`:

```python
def keep_new_listing(listing_id: str) -> bool:
    """
    'Dejar el nuevo': activa el candidato nuevo y descarta el original.
    El nuevo listing apunta al original via duplicate_candidate_of.
    """
    client = get_client()
    if client is None:
        return False
    try:
        res = (
            client.table("listings")
            .select("id,duplicate_candidate_of")
            .eq("id", listing_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            log.error("keep_new_not_found", extra={"id": listing_id})
            return False

        original_url = res.data[0].get("duplicate_candidate_of")
        if original_url:
            client.table("listings").update({
                "status": "descartado",
                "disabled_reason": "duplicado_nuevo_elegido",
            }).eq("url", original_url).execute()

        client.table("listings").update({
            "status": "activo",
            "duplicate_candidate_of": None,
        }).eq("id", listing_id).execute()

        log.info("keep_new_listing", extra={"id": listing_id, "original_url": original_url})
        return True
    except Exception as exc:
        log.error("db_keep_new_failed", extra={"id": listing_id, "error": str(exc)})
        return False
```

- [ ] **Step 2: Update `api/services/listings_service.py`**

Update the import at the top:

```python
from scraper.infrastructure.db import (
    approve_pending, get_pending_review_listings, query_listings,
    reject_pending, keep_new_listing as db_keep_new,
)
```

Add after `reject_listing`:

```python
def keep_new_listing(listing_id: str) -> bool:
    return db_keep_new(listing_id)
```

- [ ] **Step 3: Add endpoint to `api/routers/listings.py`**

Add after the `reject_listing` endpoint:

```python
@router.post("/{listing_id}/keep-new")
def keep_new_listing(listing_id: str):
    ok = listings_service.keep_new_listing(listing_id)
    return {"ok": ok}
```

- [ ] **Step 4: Verify server starts**

```bash
cd c:/Users/kein-/Desktop/Antigravity/RealStateAnalyse
uvicorn api.main:app --reload --port 8000
```

Expected: starts without import errors. Press Ctrl+C to stop.

- [ ] **Step 5: Commit**

```bash
git add scraper/infrastructure/db.py api/services/listings_service.py api/routers/listings.py
git commit -m "feat: add keep-new duplicate action — discard original, activate new listing"
```

---

## Task 5: Update frontend API types and service

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Replace `PendingListing` interface and add `keepNewListing`**

In `frontend/src/services/api.ts`, replace lines 105–131 (the `PendingListing` interface through `rejectListing`):

```typescript
export interface OriginalListingInfo {
  titulo?: string;
  precio_venta?: number;
  metros_cuadrados?: number;
  habitaciones?: number;
  barrio?: string;
  municipio?: string;
  primera_deteccion?: string;
  url: string;
}

export interface PendingListing {
  id: string;
  url: string;
  fuente: string;
  titulo?: string;
  precio_venta?: number;
  metros_cuadrados?: number;
  habitaciones?: number;
  barrio?: string;
  municipio?: string;
  status: string;
  duplicate_candidate_of?: string;
  primera_deteccion?: string;
  original_info?: OriginalListingInfo;
}

export const fetchPendingReview = async (): Promise<PendingListing[]> => {
  const { data } = await api.get<PendingListing[]>("/listings/pending-review");
  return data;
};

export const approveListing = async (id: string): Promise<void> => {
  await api.post(`/listings/${id}/approve`);
};

export const rejectListing = async (id: string): Promise<void> => {
  await api.post(`/listings/${id}/reject`);
};

export const keepNewListing = async (id: string): Promise<void> => {
  await api.post(`/listings/${id}/keep-new`);
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd c:/Users/kein-/Desktop/Antigravity/RealStateAnalyse/frontend
npm run build 2>&1 | head -40
```

Expected: TypeScript errors only in `Review.tsx` (references `pending_review` which no longer exists) — fixed in Task 6. No errors in `api.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: update PendingListing type with status + original_info; add keepNewListing"
```

---

## Task 6: Redesign `Review.tsx` card

**Files:**
- Modify: `frontend/src/pages/Review.tsx`

- [ ] **Step 1: Replace `Review.tsx`**

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveListing,
  fetchPendingReview,
  keepNewListing,
  rejectListing,
} from "../services/api";
import type { OriginalListingInfo, PendingListing } from "../services/api";

function formatDate(ts?: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return ts;
  }
}

type ListingSnippet = Pick<PendingListing, "titulo" | "precio_venta" | "metros_cuadrados" | "habitaciones" | "municipio" | "barrio" | "primera_deteccion" | "url">;

function ListingDetails({ listing }: { listing: ListingSnippet }) {
  return (
    <div className="flex flex-col gap-1.5">
      {listing.titulo && (
        <p className="text-sm font-medium text-gray-800 truncate">{listing.titulo}</p>
      )}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
        {listing.precio_venta != null && (
          <span className="font-semibold text-gray-700">
            {listing.precio_venta.toLocaleString("es-ES")} €
          </span>
        )}
        {listing.metros_cuadrados != null && <span>{listing.metros_cuadrados} m²</span>}
        {listing.habitaciones != null && <span>{listing.habitaciones} hab.</span>}
        {listing.municipio && (
          <span>
            {listing.municipio}
            {listing.barrio ? ` · ${listing.barrio}` : ""}
          </span>
        )}
        <span className="text-gray-300">Detectado: {formatDate(listing.primera_deteccion)}</span>
      </div>
      {listing.url && (
        <a
          href={listing.url}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-blue-500 hover:underline truncate"
        >
          Ver anuncio →
        </a>
      )}
    </div>
  );
}

function ReviewCard({ listing }: { listing: PendingListing }) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["pending-review"] });

  const approveMutation = useMutation({
    mutationFn: () => approveListing(listing.id),
    onSuccess: invalidate,
  });
  const rejectMutation = useMutation({
    mutationFn: () => rejectListing(listing.id),
    onSuccess: invalidate,
  });
  const keepNewMutation = useMutation({
    mutationFn: () => keepNewListing(listing.id),
    onSuccess: invalidate,
  });

  const isPending =
    approveMutation.isPending || rejectMutation.isPending || keepNewMutation.isPending;

  return (
    <div className="bg-white border border-yellow-200 rounded-xl p-5 shadow-sm flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-yellow-700 bg-yellow-100 px-2 py-0.5 rounded-full">
          ⚠️ Posible duplicado
        </span>
        <span className="text-xs text-gray-400 capitalize">{listing.fuente}</span>
      </div>

      {/* Anuncio nuevo */}
      <div className="flex flex-col gap-1.5">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Anuncio nuevo</p>
        <ListingDetails listing={listing} />
      </div>

      <div className="border-t border-dashed border-gray-200" />

      {/* Original en BD */}
      <div className="flex flex-col gap-1.5">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Original en BD</p>
        {listing.original_info ? (
          <ListingDetails listing={listing.original_info} />
        ) : (
          <p className="text-xs text-gray-300 italic">No se encontró el original</p>
        )}
      </div>

      {/* Botones */}
      <div className="flex flex-col gap-2 mt-auto">
        <button
          onClick={() => approveMutation.mutate()}
          disabled={isPending}
          className="w-full py-2 text-sm border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {approveMutation.isPending ? "…" : "↔ Dejar los dos"}
        </button>
        <div className="flex gap-2">
          <button
            onClick={() => rejectMutation.mutate()}
            disabled={isPending}
            className="flex-1 py-2 text-sm border border-gray-200 text-gray-500 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {rejectMutation.isPending ? "…" : "← Dejar el antiguo"}
          </button>
          <button
            onClick={() => keepNewMutation.mutate()}
            disabled={isPending}
            className="flex-1 py-2 text-sm bg-blue-700 text-white rounded-lg hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {keepNewMutation.isPending ? "…" : "→ Dejar el nuevo"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Review() {
  const query = useQuery({
    queryKey: ["pending-review"],
    queryFn: fetchPendingReview,
    refetchInterval: 60_000,
  });

  const items = query.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Revisión de duplicados</h1>
        <p className="text-sm text-gray-400 mt-1">
          Anuncios detectados como posibles duplicados que requieren aprobación manual
        </p>
      </div>

      {query.isLoading ? (
        <p className="text-sm text-gray-400">Cargando…</p>
      ) : query.isError ? (
        <p className="text-sm text-red-500">Error al cargar los anuncios pendientes.</p>
      ) : items.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <p className="text-gray-400 text-sm">Sin anuncios pendientes de revisión</p>
          <p className="text-gray-300 text-xs mt-1">
            Los posibles duplicados aparecerán aquí durante el scraping
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-500">
            {items.length} anuncio{items.length !== 1 ? "s" : ""} pendiente
            {items.length !== 1 ? "s" : ""}
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {items.map((item) => (
              <ReviewCard key={item.id} listing={item} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build with no errors**

```bash
cd c:/Users/kein-/Desktop/Antigravity/RealStateAnalyse/frontend
npm run build 2>&1 | head -40
```

Expected: build succeeds, zero TypeScript errors.

- [ ] **Step 3: Start dev server and smoke test the UI**

```bash
npm run dev
```

Open `http://localhost:5173` → navigate to Revisión de duplicados.

Verify:
- Both "Anuncio nuevo" and "Original en BD" blocks are visible (or "No se encontró el original" if no match)
- Three buttons: "↔ Dejar los dos" / "← Dejar el antiguo" / "→ Dejar el nuevo"
- All three buttons disable while any mutation is loading
- After clicking any action, the card disappears from the list

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Review.tsx
git commit -m "feat: redesign duplicate review card — original info + 3-action buttons"
```

---

## Task 7: Final verification

**Files:** None — verification only.

- [ ] **Step 1: Run all unit tests**

```bash
cd c:/Users/kein-/Desktop/Antigravity/RealStateAnalyse
python -m pytest tests/ -v
```

Expected: 10 tests PASS.

- [ ] **Step 2: Confirm no stale references to old fields**

```bash
grep -rn "\"activo\"" api/ scraper/ --include="*.py" | grep -v "fuentes"
grep -rn "pending_review" api/ scraper/ --include="*.py"
grep -rn "\"estado\"" api/ scraper/ --include="*.py"
```

Expected: zero hits. (The `fuentes` table has its own `activo` field — exclude it.)

- [ ] **Step 3: Deploy to Railway**

Push the branch and merge to main to trigger Railway deployment.

---

## Task 8: DB Migration Step 3 — Drop old columns

**Files:**
- Run SQL via: Supabase Dashboard → SQL Editor

**Only run this after Tasks 1–7 are deployed to production and at least one scraper cycle has run without errors.**

- [ ] **Step 1: Confirm new code is live in production**

Check Railway deployment logs — new code must be live.

- [ ] **Step 2: Re-run the stale reference check on production code**

```bash
grep -rn "\.eq(\"activo\"" scraper/ api/ --include="*.py"
grep -rn "pending_review" scraper/ api/ --include="*.py"
```

Expected: zero hits.

- [ ] **Step 3: Drop old columns in Supabase SQL Editor**

```sql
ALTER TABLE listings
  DROP COLUMN IF EXISTS activo,
  DROP COLUMN IF EXISTS pending_review,
  DROP COLUMN IF EXISTS estado;
```

- [ ] **Step 4: Verify table structure**

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'listings'
ORDER BY ordinal_position;
```

Expected: `activo`, `pending_review`, `estado` absent. `status`, `condition`, `ocupacion`, `situacion_legal`, `disabled_reason`, and all amenity columns present.

- [ ] **Step 5: Record migration**

```bash
git commit --allow-empty -m "chore: ran DB migration step 3 (drop activo, pending_review, estado)"
```

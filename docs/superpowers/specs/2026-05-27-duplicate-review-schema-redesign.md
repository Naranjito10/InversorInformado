# Spec: Duplicate Review UI + Schema Redesign

**Date:** 2026-05-27
**Branch target:** main
**Status:** Approved for implementation

---

## Overview

Two interleaved goals:

1. **Duplicate Review UI** — redesign the Review page card to show both listings side-by-side and replace the binary Approve/Reject with three explicit actions.
2. **Schema Redesign** — replace the `activo` boolean and `pending_review` boolean with a rich `status` enum; rename `estado` to `condition` with expanded values; add `ocupacion`, `situacion_legal`, `disabled_reason`, and ~20 amenity fields.

### Out of scope
- `ventas` and `alquileres` tables (future milestone)
- Scraper parser changes to populate new amenity fields (separate task — fields are added to schema now, populated later)

---

## 1. Data Model

### 1.1 Fields removed (replaced)

| Field | Type | Replaced by |
|---|---|---|
| `activo` | bool | `status` |
| `pending_review` | bool | `status = 'pendiente_revision'` |
| `estado` | str | `condition` |

### 1.2 New classification fields

#### `status` (enum, NOT NULL, default `'activo'`)
Lifecycle of the listing record in the database.

| Value | Set by | Meaning |
|---|---|---|
| `activo` | Scraper / approve action | Visible in all searches and analytics |
| `pendiente_revision` | Scraper duplicate detector | Flagged as possible duplicate, awaiting manual review |
| `reservado` | Future / manual | Under offer or negotiation |
| `en_pausa` | Future / manual | Temporarily withdrawn by seller |
| `inactivo` | `mark_inactive()` | Scraper stopped seeing it — off market |
| `descartado` | Reject action / keep-new action | Manually discarded |

All existing queries filtering `activo = TRUE` migrate to `status = 'activo'`.
`find_near_duplicate` migrates from `pending_review = FALSE` to `status != 'pendiente_revision'` (or equivalently `status = 'activo'`).

#### `condition` (enum, nullable)
Physical conservation state of the property.

| Value | Display label |
|---|---|
| `obra_nueva` | Nuevo |
| `listo_para_usar` | Listo para usar |
| `buen_estado` | Usado pero bien |
| `reforma_leve` | Reforma leve necesaria |
| `reforma_integral` | Reforma Integral / A reformar |
| `reforma_estructural` | Reforma estructural necesaria |

Migration from `estado`: `'nuevo'` → `obra_nueva`, `'buen estado'` → `buen_estado`, `'a reformar'` → `reforma_integral`.

#### `ocupacion` (enum, nullable)
Who is physically present in the property.

| Value | Display label |
|---|---|
| `libre` | Libre / Desocupado |
| `ocupado` | Ocupado |
| `alquilado` | Alquilado |
| `nuda_propiedad` | Nuda propiedad |

#### `situacion_legal` (enum, nullable)
Legal or encumbrance status of the title.

| Value | Display label |
|---|---|
| `libre_cargas` | Libre de cargas |
| `con_hipoteca` | Con hipoteca |
| `en_construccion` | En construcción |
| `renta_antigua` | Renta antigua |
| `vpo` | VPO / Protección oficial |
| `subasta` | En subasta |
| `litigio` | En litigio |
| `herencia` | Herencia / En trámite |

#### `disabled_reason` (text, nullable)
Audit field. Only set when `status` transitions away from `activo`/`pendiente_revision`.

| Value | When set |
|---|---|
| `duplicado_nuevo_elegido` | "Dejar el nuevo" — this was the old listing |
| `duplicado_antiguo_elegido` | "Dejar el antiguo" — this was the new candidate |
| `no_visto_scraper` | `mark_inactive()` at end of scraper cycle |
| `revision_manual` | Future: manual discard outside duplicate flow |

### 1.3 New amenity fields (all nullable)

#### Interiores
| Field | Type |
|---|---|
| `balcon` | bool |
| `trastero` | bool |
| `armarios_empotrados` | bool |
| `aire_acondicionado` | bool |
| `calefaccion` | bool |
| `calefaccion_tipo` | str (`central\|individual_gas\|bomba_calor\|electrica\|suelo_radiante`) |
| `cocina_equipada` | bool |
| `amueblado` | bool |

#### Edificio
| Field | Type |
|---|---|
| `exterior` | bool |
| `orientacion` | str (`N\|S\|E\|O\|NE\|NO\|SE\|SO`) |
| `portero` | bool |
| `puerta_blindada` | bool |
| `doble_acristalamiento` | bool |
| `adaptado_movilidad` | bool |

#### Zonas exteriores / comunidad
| Field | Type |
|---|---|
| `jardin` | bool |
| `piscina` | bool |
| `piscina_comunitaria` | bool |
| `zonas_verdes_comunitarias` | bool |
| `vigilancia` | bool |

#### Garaje (ampliar existing)
| Field | Type | Notes |
|---|---|---|
| `garaje_incluido` | bool | Garage price included vs. separate |
| `num_plazas_garaje` | int | Number of spaces |

---

## 2. Database Migration

One-time SQL to run against Supabase before deploying new code:

```sql
-- Step 1: Add new columns
ALTER TABLE listings
  ADD COLUMN status TEXT NOT NULL DEFAULT 'activo',
  ADD COLUMN condition TEXT,
  ADD COLUMN ocupacion TEXT,
  ADD COLUMN situacion_legal TEXT,
  ADD COLUMN disabled_reason TEXT,
  ADD COLUMN balcon BOOLEAN,
  ADD COLUMN trastero BOOLEAN,
  ADD COLUMN armarios_empotrados BOOLEAN,
  ADD COLUMN aire_acondicionado BOOLEAN,
  ADD COLUMN calefaccion BOOLEAN,
  ADD COLUMN calefaccion_tipo TEXT,
  ADD COLUMN cocina_equipada BOOLEAN,
  ADD COLUMN amueblado BOOLEAN,
  ADD COLUMN exterior BOOLEAN,
  ADD COLUMN orientacion TEXT,
  ADD COLUMN portero BOOLEAN,
  ADD COLUMN puerta_blindada BOOLEAN,
  ADD COLUMN doble_acristalamiento BOOLEAN,
  ADD COLUMN adaptado_movilidad BOOLEAN,
  ADD COLUMN jardin BOOLEAN,
  ADD COLUMN piscina BOOLEAN,
  ADD COLUMN piscina_comunitaria BOOLEAN,
  ADD COLUMN zonas_verdes_comunitarias BOOLEAN,
  ADD COLUMN vigilancia BOOLEAN,
  ADD COLUMN garaje_incluido BOOLEAN,
  ADD COLUMN num_plazas_garaje INTEGER;

-- Step 2: Migrate existing data
UPDATE listings SET status = 'pendiente_revision' WHERE pending_review = TRUE;
UPDATE listings SET status = 'inactivo'           WHERE activo = FALSE AND pending_review = FALSE;
-- status = 'activo' already set by DEFAULT for all other rows

UPDATE listings SET condition = 'obra_nueva'       WHERE estado = 'nuevo';
UPDATE listings SET condition = 'buen_estado'      WHERE estado = 'buen estado';
UPDATE listings SET condition = 'reforma_integral' WHERE estado = 'a reformar';

-- Step 3: Drop old columns (after verifying migration is correct)
ALTER TABLE listings
  DROP COLUMN activo,
  DROP COLUMN pending_review,
  DROP COLUMN estado;
```

**Migration order:** Run Step 1+2 first, deploy new code, then run Step 3 once confirmed stable.

---

## 3. Backend Changes

### 3.1 `scraper/models.py`

- Remove: `activo: bool`, `pending_review: bool`, `estado: Optional[str]`
- Remove: `VALID_ESTADOS` set and `_normalize_estado` validator
- Add: `status: str = 'activo'`, `condition`, `ocupacion`, `situacion_legal`, `disabled_reason` (all Optional[str])
- Add: all 20 new amenity fields (all `Optional[bool/int/str]`)
- Update `to_db_dict` to keep `status` always (instead of `activo`)

### 3.2 `scraper/infrastructure/db.py`

| Function | Change |
|---|---|
| `upsert_listing` | Replace `activo=True` / `pending_review` assignments with `status=` equivalents; on update, pop `status`, `disabled_reason`, and `duplicate_candidate_of` from `update_payload` (same pattern as current `pop("pending_review")`) so a re-scrape never overwrites a manually-set status |
| `find_near_duplicate` | `.eq("activo", True).eq("pending_review", False)` → `.eq("status", "activo")` |
| `mark_inactive` | `.eq("activo", True)` → `.eq("status", "activo")`; update sets `status='inactivo', disabled_reason='no_visto_scraper'` |
| `get_pending_review_listings` | `.eq("pending_review", True)` → `.eq("status", "pendiente_revision")`; **enrich** each result with original listing details (secondary query by `duplicate_candidate_of` URL, adds `original_info` key) |
| `approve_pending` | Sets `status='activo', duplicate_candidate_of=null` |
| `reject_pending` | Sets `status='descartado', disabled_reason='duplicado_antiguo_elegido'` |
| `get_price_drops_last_24h` | No filter change needed (no `activo` filter) |
| `get_high_score_listings` | `.eq("activo", True)` → `.eq("status", "activo")` |
| `query_listings` | `"activo" in filters` → `"status" in filters`; default filter becomes `status='activo'` |
| **NEW** `keep_new_listing` | Fetch new listing → get `duplicate_candidate_of` URL → find original → set original `status='descartado', disabled_reason='duplicado_nuevo_elegido'` → set new listing `status='activo', duplicate_candidate_of=null` |

### 3.3 `api/services/listings_service.py`

- `approve_listing`: no change (delegates to `approve_pending`)
- `reject_listing`: no change (delegates to `reject_pending`)
- Add `keep_new_listing(listing_id)` → delegates to `keep_new_listing` in db
- `get_stats`: update filters from `activo=True` to `status='activo'`

### 3.4 `api/routers/listings.py`

- Add `POST /{listing_id}/keep-new` endpoint
- `get_listings`: update `solo_activos` filter to use `status='activo'`

### 3.5 Backend schema note

`get_pending_review_listings` returns `list[dict]` — no typed Pydantic schema for this endpoint. The `original_info` key is injected directly into each dict in that function. No `api/schemas.py` change needed.

---

## 4. Frontend Changes

### 4.1 `frontend/src/services/api.ts`

- Update `PendingListing` type:
  - Add `original_info?: { titulo, precio_venta, metros_cuadrados, habitaciones, barrio, municipio, primera_deteccion }`
- Add `keepNewListing(id: string)` function → `POST /api/listings/{id}/keep-new`

### 4.2 `frontend/src/pages/Review.tsx`

**Card redesign:**
- Split into two labelled blocks: "Anuncio nuevo" and "Original en BD"
- Original block shows: título, precio, m², hab., municipio·barrio, fecha detectado, link
- Replace 2-button row with 3-button layout:
  - Row 1 (full width): `↔ Dejar los dos` (neutral/grey border) → calls `approveMutation`
  - Row 2 (split): `← Dejar el antiguo` (grey) + `→ Dejar el nuevo` (blue filled) → calls `rejectMutation` / `keepNewMutation`
- All 3 buttons disabled while any mutation is pending
- Add `keepNewMutation` using `keepNewListing`

---

## 5. Enrichment Logic for `get_pending_review_listings`

When fetching pending listings, for each row where `duplicate_candidate_of` is set:

```python
original = client.table("listings")
    .select("titulo,precio_venta,metros_cuadrados,habitaciones,barrio,municipio,primera_deteccion,url")
    .eq("url", row["duplicate_candidate_of"])
    .limit(1)
    .execute()
row["original_info"] = original.data[0] if original.data else None
```

This adds one extra DB query per pending listing. Acceptable at the expected volume (tens of listings at most).

---

## 6. Impact on Other Features

| Feature | Impact |
|---|---|
| Dashboard / ListingsTable | `solo_activos` filter already uses `status='activo'` after migration |
| Excel Export | `query_listings(activo=True)` → `status='activo'` — no UI change |
| Telegram publish | No filter change needed |
| Reports | No filter change needed |
| Scraper cycle | `mark_inactive` updated to set `status='inactivo'` |
| Duplicate detection | `find_near_duplicate` updated |

---

## 7. Sequence of Implementation

1. Run DB migration Step 1+2 (additive — safe to deploy before code change)
2. Backend: update models, db, service, router
3. Frontend: update types, api service, Review card
4. Smoke test: create a test duplicate, go through all 3 actions
5. Run DB migration Step 3 (drop old columns) once stable

-- =========================================================================
-- 004_add_tipo_propiedad.sql
-- Añade el tipo de propiedad (Piso / Casa / etc.) a la tabla listings
-- =========================================================================

alter table public.listings
    add column if not exists tipo_propiedad text;

create index if not exists idx_listings_tipo_propiedad
    on public.listings (tipo_propiedad);

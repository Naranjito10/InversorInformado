-- =========================================================================
-- 001_create_listings.sql
-- Tabla principal de viviendas detectadas por el scraper
-- =========================================================================

create extension if not exists "uuid-ossp";

create table if not exists public.listings (
    id                        uuid primary key default uuid_generate_v4(),

    -- Identificacion
    url                       text not null unique,
    fuente                    text not null,             -- idealista / fotocasa / habitaclia / pisos
    titulo                    text,

    -- Precios
    precio_venta              integer,
    ibi                       integer,                   -- Precio anual del IBI en EUR
    comunidad                 integer,                   -- Cuota anual de comunidad EUR
    derramas_pendientes       integer,                   -- Estimacion derramas pendientes EUR
    precio_m2                 integer,                   -- Calculado: precio_venta / m2

    -- Caracteristicas fisicas
    metros_cuadrados          integer,
    habitaciones              integer,
    banos                     integer,
    planta                    text,
    ascensor                  boolean,
    terraza                   boolean,
    garaje                    boolean,
    condition                 text,                      -- obra_nueva / listo_para_usar / buen_estado / reforma_leve / reforma_integral / reforma_estructural
    certificado_energetico    text,                      -- A..G

    -- Localizacion
    barrio                    text,
    municipio                 text,
    provincia                 text,
    lat                       double precision,
    lon                       double precision,

    -- Mercado / inversion
    alquiler_estimado         integer,                   -- mensual EUR
    rentabilidad_alquiler     integer,                   -- (alquiler*12) - gastos
    rentabilidad_bruta        numeric(5,2),              -- pct
    precio_zona_m2            integer,                   -- precio medio zona EUR/m2
    descuento_zona_pct        numeric(6,2),              -- (+/-) % vs zona

    -- Estado del seguimiento
    dias_en_mercado           integer default 0,
    veces_visto               integer default 1,
    score                     integer default 0,
    score_label               text default 'normal',     -- alto / medio / normal / incompleto
    bajada_precio             boolean default false,
    campos_vacios             integer default 0,
    primera_deteccion         timestamptz default now(),
    ultima_actualizacion      timestamptz default now(),
    activo                    boolean default true,

    -- Auditoria
    raw_data                  jsonb                      -- payload original por si hace falta reparsear
);

-- Indices para queries habituales
create index if not exists idx_listings_score          on public.listings (score desc);
create index if not exists idx_listings_score_label    on public.listings (score_label);
create index if not exists idx_listings_municipio      on public.listings (municipio);
create index if not exists idx_listings_barrio         on public.listings (barrio);
create index if not exists idx_listings_fuente         on public.listings (fuente);
create index if not exists idx_listings_activo         on public.listings (activo);
create index if not exists idx_listings_rentabilidad   on public.listings (rentabilidad_bruta desc);
create index if not exists idx_listings_precio_m2      on public.listings (precio_m2);
create index if not exists idx_listings_primera_det    on public.listings (primera_deteccion desc);

-- Trigger para mantener ultima_actualizacion
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.ultima_actualizacion = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_listings_updated_at on public.listings;
create trigger trg_listings_updated_at
    before update on public.listings
    for each row
    execute function public.set_updated_at();

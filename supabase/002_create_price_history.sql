-- =========================================================================
-- 002_create_price_history.sql
-- Historico de precios por anuncio para deteccion de bajadas
-- =========================================================================

create table if not exists public.price_history (
    id          uuid primary key default uuid_generate_v4(),
    listing_id  uuid not null references public.listings(id) on delete cascade,
    precio      integer not null,
    fecha       timestamptz not null default now()
);

create index if not exists idx_price_history_listing on public.price_history (listing_id, fecha desc);

-- Funcion para registrar cambios de precio
create or replace function public.log_price_change()
returns trigger as $$
begin
    -- Solo registrar cuando el precio cambia
    if (tg_op = 'INSERT') then
        if new.precio_venta is not null then
            insert into public.price_history (listing_id, precio, fecha)
            values (new.id, new.precio_venta, now());
        end if;
        return new;
    end if;

    if (tg_op = 'UPDATE') then
        if new.precio_venta is distinct from old.precio_venta and new.precio_venta is not null then
            insert into public.price_history (listing_id, precio, fecha)
            values (new.id, new.precio_venta, now());

            -- Marcar bajada de precio si es relevante
            if old.precio_venta is not null and new.precio_venta < old.precio_venta then
                new.bajada_precio = true;
            end if;
        end if;
        return new;
    end if;

    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_price_change on public.listings;
create trigger trg_price_change
    before insert or update on public.listings
    for each row
    execute function public.log_price_change();

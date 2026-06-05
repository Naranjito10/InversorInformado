-- =========================================================================
-- 005_fix_scoring_trigger.sql
-- Corrige el trigger de scoring para usar la columna "condition" (no "estado")
-- y los valores del enum Python: buen_estado, reforma_integral, etc.
-- Ejecutar en Supabase SQL Editor.
-- =========================================================================

create or replace function public.calcular_score(l public.listings)
returns table(score int, score_label text) as $$
declare
    s int := 0;
    lbl text := 'normal';
begin
    -- ----- RENTABILIDAD (0-40) -----
    if l.rentabilidad_bruta is not null then
        if l.rentabilidad_bruta >= 7 then
            s := s + 40;
        elsif l.rentabilidad_bruta >= 5 then
            s := s + 25;
        elsif l.rentabilidad_bruta >= 4 then
            s := s + 10;
        end if;
    end if;

    -- ----- DESCUENTO vs ZONA (0-25) -----
    if l.descuento_zona_pct is not null then
        if l.descuento_zona_pct <= -10 then
            s := s + 25;
        elsif l.descuento_zona_pct <= -5 then
            s := s + 15;
        elsif l.descuento_zona_pct <= 0 then
            s := s + 8;
        end if;
    end if;

    -- ----- ESTADO Y EXTRAS (0-20) -----
    if l.condition in ('buen_estado', 'listo_para_usar') then s := s + 8; end if;
    if l.ascensor is true then s := s + 4; end if;
    if l.terraza  is true then s := s + 4; end if;
    if l.garaje   is true then s := s + 4; end if;

    -- ----- SEÑALES DE URGENCIA (0-15) -----
    if l.bajada_precio is true             then s := s + 10; end if;
    if coalesce(l.dias_en_mercado, 0) > 60 then s := s + 5;  end if;

    -- ----- PENALIZACIONES -----
    if coalesce(l.campos_vacios, 0) > 5 then
        s := least(s, 40);
    end if;
    if l.condition in ('reforma_leve', 'reforma_integral', 'reforma_estructural') then
        s := s - 5;
    end if;

    -- Acotar [0, 100]
    s := greatest(0, least(s, 100));

    -- ----- CLASIFICACION -----
    if s >= 80 then
        lbl := 'alto';
    elsif s >= 50 then
        lbl := 'medio';
    else
        lbl := 'normal';
    end if;
    if coalesce(l.campos_vacios, 0) > 3 then
        lbl := 'incompleto';
    end if;

    score := s;
    score_label := lbl;
    return next;
end;
$$ language plpgsql immutable;


create or replace function public.aplicar_score()
returns trigger as $$
declare
    r record;
    null_count int := 0;
begin
    -- Contar campos clave nulos para campos_vacios
    if new.precio_venta           is null then null_count := null_count + 1; end if;
    if new.metros_cuadrados       is null then null_count := null_count + 1; end if;
    if new.habitaciones           is null then null_count := null_count + 1; end if;
    if new.banos                  is null then null_count := null_count + 1; end if;
    if new.condition              is null then null_count := null_count + 1; end if;
    if new.barrio                 is null then null_count := null_count + 1; end if;
    if new.municipio              is null then null_count := null_count + 1; end if;
    if new.precio_m2              is null then null_count := null_count + 1; end if;
    if new.certificado_energetico is null then null_count := null_count + 1; end if;
    if new.planta                 is null then null_count := null_count + 1; end if;
    new.campos_vacios := null_count;

    -- precio_m2 si falta y tenemos datos
    if new.precio_m2 is null
       and new.precio_venta is not null
       and new.metros_cuadrados is not null
       and new.metros_cuadrados > 0 then
        new.precio_m2 := round(new.precio_venta::numeric / new.metros_cuadrados);
    end if;

    -- rentabilidad_bruta si falta y tenemos datos
    if new.rentabilidad_bruta is null
       and new.alquiler_estimado is not null
       and new.precio_venta is not null
       and new.precio_venta > 0 then
        new.rentabilidad_bruta := round(
            ((new.alquiler_estimado * 12.0) / new.precio_venta) * 100, 2
        );
    end if;

    -- descuento_zona_pct si falta y tenemos datos
    if new.descuento_zona_pct is null
       and new.precio_m2 is not null
       and new.precio_zona_m2 is not null
       and new.precio_zona_m2 > 0 then
        new.descuento_zona_pct := round(
            ((new.precio_m2 - new.precio_zona_m2)::numeric / new.precio_zona_m2) * 100, 2
        );
    end if;

    -- rentabilidad_alquiler (neto aproximado, EUR/año)
    if new.rentabilidad_alquiler is null
       and new.alquiler_estimado is not null then
        new.rentabilidad_alquiler :=
            (coalesce(new.alquiler_estimado, 0) * 12)
            - coalesce(new.ibi, 0)
            - coalesce(new.comunidad, 0)
            - coalesce(new.derramas_pendientes, 0);
    end if;

    -- dias_en_mercado
    if new.primera_deteccion is not null then
        new.dias_en_mercado := greatest(
            extract(day from (now() - new.primera_deteccion))::int, 0
        );
    end if;

    -- Calcular score
    select * into r from public.calcular_score(new);
    new.score := r.score;
    new.score_label := r.score_label;

    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_aplicar_score on public.listings;
drop trigger if exists trg_z_aplicar_score on public.listings;
create trigger trg_z_aplicar_score
    before insert or update on public.listings
    for each row
    execute function public.aplicar_score();

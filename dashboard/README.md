# Dashboard — Metabase o Grafana sobre Supabase

Supabase expone PostgreSQL directamente, así que cualquier BI tool compatible
con Postgres vale. Aquí van las dos opciones más prácticas para perfil
intermedio (gratis o casi).

---

## 1. Obtener credenciales de Supabase

En el dashboard de tu proyecto: **Settings → Database → Connection string**.

Tendrás algo así:

```
host:     db.YOURPROJECT.supabase.co
port:     5432
database: postgres
user:     postgres
password: <tu_password>
```

> ⚠️ Crea un usuario **read-only** para el dashboard (no uses el `service_role`).
>
> En el **SQL Editor** de Supabase:
>
> ```sql
> create user bi_reader with password 'una-clave-fuerte';
> grant connect on database postgres to bi_reader;
> grant usage on schema public to bi_reader;
> grant select on all tables in schema public to bi_reader;
> alter default privileges in schema public grant select on tables to bi_reader;
> ```

---

## 2. Opción A — Metabase (recomendado para empezar)

### Local (Docker)

```bash
docker run -d -p 3000:3000 --name metabase metabase/metabase
```

Abre <http://localhost:3000>, crea cuenta admin y añade la base de datos
PostgreSQL con los datos del paso 1.

### Hosteado gratis

* [Metabase Cloud](https://www.metabase.com/start/) — 14 días gratis.
* [Render.com](https://render.com) o [Railway](https://railway.app) — free tier para Metabase en Docker.

### Consultas de partida (cópialas en *Questions → SQL*)

**Top 10 viviendas por rentabilidad bruta esta semana**
```sql
select titulo, barrio, municipio, precio_venta, precio_m2,
       rentabilidad_bruta, score, url
from listings
where activo = true
  and primera_deteccion >= now() - interval '7 days'
order by rentabilidad_bruta desc nulls last
limit 10;
```

**Bajadas de precio últimos 7 días**
```sql
select l.titulo, l.barrio, l.municipio,
       l.precio_venta as precio_actual,
       ph.precio as precio_anterior,
       round(((l.precio_venta - ph.precio)::numeric / ph.precio) * 100, 2) as variacion_pct,
       l.url
from listings l
join lateral (
    select precio from price_history
    where listing_id = l.id and fecha < now() - interval '1 day'
    order by fecha desc limit 1
) ph on true
where l.bajada_precio = true
  and l.ultima_actualizacion >= now() - interval '7 days'
order by variacion_pct asc;
```

**Precio medio €/m² por barrio (evolución 30 días)**
```sql
select barrio, municipio,
       count(*) as muestras,
       round(avg(precio_m2)) as precio_medio_actual
from listings
where activo = true and barrio is not null
group by barrio, municipio
order by precio_medio_actual desc;
```

**Anuncios con más de 90 días sin venderse**
```sql
select titulo, barrio, municipio, precio_venta, precio_m2,
       dias_en_mercado, score, url
from listings
where activo = true and dias_en_mercado > 90
order by dias_en_mercado desc;
```

**Comparativa Idealista vs Fotocasa por barrio**
```sql
select barrio, fuente,
       count(*) as anuncios,
       round(avg(precio_m2)) as precio_m2_medio,
       round(avg(rentabilidad_bruta)::numeric, 2) as rentabilidad_media
from listings
where activo = true and barrio is not null
  and fuente in ('idealista', 'fotocasa')
group by barrio, fuente
order by barrio, fuente;
```

---

## 3. Opción B — Grafana

Grafana sirve para dashboards más operativos (alertas, métricas en tiempo
real). Instala Grafana → añade datasource **PostgreSQL** apuntando al host de
Supabase con las credenciales `bi_reader`.

Panel sugerido: usa las vistas SQL que ya crea la migración
`003_scoring_function.sql`:

* `v_top_rentabilidad`
* `v_bajadas_recientes`
* `v_oportunidades_alto`
* `v_precio_medio_barrio`

Ejemplo de query Grafana (Time series — bajadas por día):

```sql
select date_trunc('day', fecha) as time,
       count(*) as bajadas
from price_history
where fecha >= $__timeFrom() and fecha >= now() - interval '90 days'
group by 1
order by 1;
```

---

## 4. Opción C — Lo más simple: Supabase Studio

Supabase tiene editor SQL integrado. Para empezar sin instalar nada:

1. Entra a tu proyecto en supabase.com → **SQL Editor**.
2. Pega las queries de arriba.
3. Guarda como *snippets* para reutilizar.

No es un dashboard visual, pero para revisar oportunidades semanalmente sobra.

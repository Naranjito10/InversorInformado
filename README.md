# 🏠 Real Estate Scraper — Vigilancia del mercado para inversores

Sistema automatizado que vigila Idealista, Fotocasa, Habitaclia y Casaradar
cada hora, almacena los anuncios en Supabase, calcula un **score 0–100** por
vivienda y envía alertas por **email** y **Telegram** cuando aparece una
oportunidad.

Pensado para tres perfiles de inversión:
* Compra para alquilar (rentabilidad)
* Reforma y venta
* Alquiler vacacional

---

## 📐 Arquitectura

```
┌──────────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  Cron / GH Action │──▶│  Scraper (Python) │──▶│ Supabase (Postgres)│
└──────────────────┘    └───────────────────┘    └──────────────────┘
                                │                          │
                                ▼                          │
                        ┌───────────────┐                  │
                        │   Scorer      │                  │
                        │ (Python+SQL)  │                  │
                        └───────────────┘                  │
                                │                          │
                                ▼                          ▼
                        ┌───────────────┐         ┌──────────────────┐
                        │ Alerts        │         │  Excel / Metabase│
                        │ Email+Telegram│         │  (consultas)     │
                        └───────────────┘         └──────────────────┘
```

---

## 🚀 Instalación rápida (15–20 min)

### 1. Clonar el repositorio

```bash
git clone <tu-repo>
cd real_estate_scraper
python -m venv .venv
source .venv/bin/activate            # macOS / Linux
# .venv\Scripts\activate              # Windows
pip install -r requirements.txt
```

Si vas a scrapear Idealista o Fotocasa instala también el navegador headless
para Scrapling:

```bash
python -m playwright install chromium
```

### 2. Crear el proyecto en Supabase

1. Crea cuenta gratis en <https://supabase.com>.
2. **New project** → anota la **URL** y la **service_role key**.
3. En **SQL Editor**, ejecuta en orden:
   * `supabase/001_create_listings.sql`
   * `supabase/002_create_price_history.sql`
   * `supabase/003_scoring_function.sql`

### 3. Configurar `.env`

```bash
cp .env.example .env
```

Edita `.env` con:

* `SUPABASE_URL` y `SUPABASE_KEY` del paso 2.
* `SMTP_*` con tu cuenta de email (Gmail: usa una *App Password*).
* `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (opcional — abajo cómo crearlos).

### 4. Definir qué buscar

Edita `config/search_targets.json` y pon las URLs de búsqueda que ya tienes en
los portales (ej. *“Pisos en venta en Eixample, Barcelona, precio max 400.000”*).
Copia la URL del portal tal cual aparece en el navegador después de aplicar
filtros — el sistema iterará las paginaciones por ti.

### 5. Probar un ciclo manual

```bash
python -m scraper.scheduler once
```

Debería:
* Recorrer las URLs configuradas.
* Guardar resultados en Supabase.
* Imprimir un resumen y dejar los logs en `logs/scraper.jsonl`.

Confirma desde la web de Supabase: **Table editor → listings**.

### 6. Programar la ejecución horaria

#### Opción A — GitHub Actions (gratis, recomendada)

1. Sube el repo a GitHub (privado).
2. En **Settings → Secrets and variables → Actions**, añade los secrets que
   coincidan con tu `.env` (`SUPABASE_URL`, `SUPABASE_KEY`, `SMTP_*`,
   `TELEGRAM_*`, etc.).
3. El workflow `.github/workflows/scrape.yml` ya está listo: se ejecutará
   cada hora.
4. Para forzar una ejecución: **Actions → Scrape viviendas → Run workflow**.

#### Opción B — cron local

```bash
crontab -e
# Añadir (cada hora, en el minuto 0):
0 * * * * cd /ruta/al/proyecto && /ruta/.venv/bin/python -m scraper.scheduler once >> logs/cron.log 2>&1
```

#### Opción C — APScheduler en primer plano

```bash
python -m scraper.scheduler
# Bloquea el proceso. Útil con systemd / supervisord / pm2.
```

---

## 📊 Sistema de score

El score (0–100) se recalcula automáticamente en cada upsert (trigger SQL) y
está espejado en `scraper/scorer.py` por si quieres testearlo offline.

| Componente              | Puntos máx | Detalle |
|-------------------------|-----------|---------|
| Rentabilidad bruta      | 40        | ≥7%=40 · ≥5%=25 · ≥4%=10 |
| Descuento vs zona       | 25        | ≤-10%=25 · ≤-5%=15 · ≤0%=8 |
| Estado y extras         | 20        | Buen estado 8 · Ascensor/Terraza/Garaje 4 c/u |
| Señales de urgencia     | 15        | Bajada precio 10 · >60 días en mercado 5 |
| Penalizaciones          | —         | Campos vacíos>5 → cap 40 · A reformar -5 |

Etiquetas:

| Label        | Rango  | Color   |
|--------------|--------|---------|
| `alto`       | ≥ 80   | 🟢 verde `#22c55e` |
| `medio`      | 50–79  | 🟡 amarillo `#f59e0b` |
| `normal`     | 0–49   | sin resaltar |
| `incompleto` | (>3 campos NULL) | 🔴 rojo `#ef4444` |
| `bajada_precio`| bool sobre cualquier label | 🟣 morado `#a855f7` |

---

## 🔔 Configurar Telegram (opcional)

1. Abre Telegram → habla con [@BotFather](https://t.me/BotFather) → `/newbot`.
2. Anota el **token** que te da.
3. Para descubrir tu `chat_id`: envía cualquier mensaje a tu bot, luego visita:
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
   y busca `"chat":{"id":<numero>...}`.
4. Pega ambos en `.env`.

---

## 📤 Exportar a Excel con colores

```bash
# Todo el stock activo
python -m export.export_excel --out export/todo.xlsx

# Solo Barcelona, score >= 60, precio entre 100k y 400k
python -m export.export_excel \
  --municipio "Barcelona" \
  --precio-min 100000 --precio-max 400000 \
  --score-min 60 \
  --out export/barcelona_60.xlsx

# Solo oportunidades de alto score
python -m export.export_excel --score-label alto --out export/alto.xlsx
```

El fichero generado lleva colores aplicados según `score_label`, hipervínculos
en la columna URL y filtros automáticos.

---

## 📈 Dashboard (Metabase / Grafana / Supabase Studio)

Ver `dashboard/README.md` para instrucciones detalladas y consultas listas
para copiar.

---

## ❓ Preguntas que el sistema responde

Todas estas se pueden ejecutar como **SQL directo en Supabase** o desde
Metabase. Hay vistas pre-creadas en `003_scoring_function.sql`:

| Pregunta | Consulta |
|----------|----------|
| Top 10 rentabilidad esta semana | `select * from v_top_rentabilidad where primera_deteccion >= now()-interval '7 days' limit 10;` |
| Bajadas de precio últimos 7 días | `select * from v_bajadas_recientes;` |
| Precio medio €/m² por barrio | `select * from v_precio_medio_barrio;` |
| Anuncios > 90 días | `select * from listings where dias_en_mercado > 90 and activo;` |
| Comparativa fuentes | Ver `dashboard/README.md` |

---

## 🛠 Estructura del proyecto

```
real_estate_scraper/
├── config/
│   └── search_targets.json       # URLs de búsqueda a vigilar
├── scraper/
│   ├── config.py                 # Carga .env
│   ├── logger.py                 # Logs JSONL
│   ├── models.py                 # Pydantic models
│   ├── normalizer.py             # Datos crudos → esquema único
│   ├── http_client.py            # Anti-ban (UA rotation, delays, Scrapling)
│   ├── db.py                     # Capa Supabase con upsert
│   ├── scorer.py                 # Score 0-100 (espejo Python del SQL)
│   ├── alerts.py                 # Email + Telegram
│   ├── runner.py                 # Orquestador de un ciclo
│   ├── scheduler.py              # APScheduler cada N min
│   └── scrapers/
│       ├── base.py
│       ├── idealista.py
│       ├── fotocasa.py
│       ├── habitaclia.py
│       └── casaradar.py
├── supabase/
│   ├── 001_create_listings.sql
│   ├── 002_create_price_history.sql
│   └── 003_scoring_function.sql
├── export/
│   └── export_excel.py           # Excel con colores (openpyxl)
├── dashboard/
│   └── README.md                 # Metabase / Grafana
├── tests/
│   ├── test_scorer.py
│   └── test_normalizer.py
├── .github/workflows/scrape.yml  # Cron horario en GitHub
├── requirements.txt
├── .env.example
└── README.md                     # (este fichero)
```

---

## ⚖️ Consideraciones legales y técnicas

* **Respeta `robots.txt`** de cada portal. El scraper introduce *delays*
  aleatorios entre 2 y 5 segundos por defecto.
* **No abuse**: la frecuencia horaria + 3 páginas por búsqueda es suficiente
  para detectar novedades sin generar tráfico problemático. No bajes el
  intervalo sin un buen motivo.
* **Uso personal**: este sistema está pensado para vigilancia personal de un
  inversor; no redistribuyas los datos scrapeados.
* **Anti-ban**: si una fuente empieza a fallar (status 403/429 sostenidos),
  añade proxies rotativos en `SCRAPER_PROXIES` o reduce `max_pages` en los
  targets.
* **Selectores HTML**: los portales cambian su DOM cada cierto tiempo. Cuando
  algún scraper deje de extraer datos, revisa los selectores en
  `scraper/scrapers/<fuente>.py`. Los logs JSONL en `logs/scraper.jsonl` te
  dirán exactamente qué falló (`fetch_failed`, `parse_error`, etc.).

---

## 🧪 Tests

```bash
pytest -v
```

Cubren la lógica de scoring (espejo del SQL) y el normalizador.

---

## 🐛 Troubleshooting

| Síntoma | Posible causa | Acción |
|---------|---------------|--------|
| `supabase_not_configured` en logs | Faltan `SUPABASE_URL`/`KEY` | Revisar `.env` |
| Todos los listings con `campos_vacios` alto | Selectores HTML obsoletos | Inspeccionar `raw_data` en BD y actualizar el scraper |
| 0 anuncios scrapeados de Idealista | DataDome | Asegúrate de tener `playwright install chromium`, considera proxies |
| Alertas no llegan | SMTP/Telegram mal configurado | Probar `python -c "from scraper.alerts import send_email; send_email('test','hola')"` |
| GitHub Action falla por timeout | Demasiados targets | Reduce `max_pages` o divide en varios workflows |

---

## 📝 Licencia

Uso personal. No incluido para distribución comercial.

# 🏠 InversorInformado — Vigilancia del mercado inmobiliario

Sistema automatizado que vigila Idealista, Fotocasa, Habitaclia y Pisos.com,
almacena los anuncios en Supabase, calcula un **score 0–100** por vivienda y
notifica por **email** y **Telegram** cuando aparece una oportunidad.

Incluye una **interfaz web** (React + FastAPI) con dashboard de anuncios,
filtros, paginación, buscador por zona y exportación a Excel.

---

## 📐 Arquitectura

```
┌─────────────────────────────────────────┐
│          React Frontend (Vite)          │
│  Dashboard · Filtros · Buscador · Excel │
└────────────────────┬────────────────────┘
                     │ /api/*
┌────────────────────▼────────────────────┐
│           FastAPI Backend               │
│  /api/listings  /api/scraper            │
│  /api/zones     /api/export/excel       │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│         Scraper (Python)                │
│  infrastructure/  →  config, db, http   │
│  services/        →  normalizer, scorer │
│  scrapers/        →  un parser/portal   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│        Supabase (PostgreSQL)            │
│  Tabla listings · Triggers SQL · Score  │
└─────────────────────────────────────────┘
```

---

## 🚀 Instalación desde cero

### Requisitos previos

- **Python 3.12** (no usar 3.14 — incompatible con pyiceberg)
- **Node.js 18+**

### 1. Clonar y preparar el entorno Python

```powershell
git clone <tu-repo>
cd InversorInformado

# Crear venv con Python 3.12 explícitamente
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

# Si PowerShell bloquea la activación:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Instalar el frontend

```powershell
cd frontend
npm install
cd ..
```

### 3. Configurar Supabase

1. Crea proyecto en <https://supabase.com> → anota la **URL** y la **anon key**.
2. En **SQL Editor**, ejecuta en orden:
   - `supabase/001_create_listings.sql`
   - `supabase/002_create_price_history.sql`
   - `supabase/003_scoring_function.sql`

### 4. Crear `.env`

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=tu-anon-key

# Notificaciones (opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu@gmail.com
SMTP_PASS=xxxx-xxxx-xxxx-xxxx
ALERT_EMAIL_FROM=tu@gmail.com
ALERT_EMAIL_TO=destinatario@gmail.com

TELEGRAM_BOT_TOKEN=token-de-botfather
TELEGRAM_CHAT_ID=tu-chat-id
```

### 5. Configurar búsquedas automáticas

Edita `config/search_targets.json` con las URLs de búsqueda de cada portal:

```json
{
  "targets": [
    {
      "source": "habitaclia",
      "name": "Barcelona Eixample",
      "url": "https://www.habitaclia.com/...",
      "max_pages": 3,
      "max_results": 100,
      "filters": { "price_min": 150000, "price_max": 400000 }
    }
  ]
}
```

Fuentes soportadas: `idealista`, `fotocasa`, `habitaclia`, `pisos`.

---

## ▶️ Arrancar la aplicación

Necesitas **dos terminales** abiertas en la raíz del proyecto:

**Terminal 1 — Backend (FastAPI):**
```powershell
.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload
```
Queda en `http://localhost:8000` · Documentación: `http://localhost:8000/docs`

**Terminal 2 — Frontend (React):**
```powershell
cd frontend
npm run dev
```
Abre `http://localhost:5173` en el navegador.

---

## 🖥️ Uso de la interfaz web

### Dashboard
- **Tarjetas**: resumen de anuncios activos, nuevos esta semana, score medio y bajadas de precio.
- **Filtros**: municipio, portal, score label, score mínimo y rango de precio.
- **Tabla**: 10 anuncios por página ordenados por score, con enlace directo al anuncio original.
- **Exportar Excel**: descarga un `.xlsx` con los anuncios filtrados, con colores por score.
- **Lanzar scraper**: ejecuta un ciclo completo en background con los targets configurados.

### Buscador
Lanza una búsqueda puntual sin esperar al ciclo automático:
1. Escribe la zona en el campo de autocompletar (ej: "sants", "eixamp").
2. Pon precio mínimo y máximo.
3. Marca los portales que quieras.
4. Elige cuántas páginas scrapear (10 = rápido, 100 = completo).
5. Pulsa **Buscar ahora** — los resultados aparecen en el Dashboard en 1–3 minutos.

---

## ⚙️ Ejecutar el scraper sin interfaz

```powershell
# Ciclo único (probar / ejecutar manualmente)
python -m scraper.scheduler once

# Planificador continuo (cada 60 minutos)
python -m scraper.scheduler
```

---

## 📊 Sistema de score

El score (0–100) se recalcula en cada upsert mediante un trigger SQL y está
espejado en `scraper/services/scorer.py` para tests offline.

| Componente          | Puntos | Detalle |
|---------------------|--------|---------|
| Rentabilidad bruta  | 0–40   | ≥7%=40 · ≥5%=25 · ≥4%=10 |
| Descuento vs zona   | 0–25   | ≤-10%=25 · ≤-5%=15 · ≤0%=8 |
| Estado y extras     | 0–20   | Buen estado 8 · Ascensor/Terraza/Garaje 4 c/u |
| Señales urgencia    | 0–15   | Bajada precio 10 · >60 días en mercado 5 |
| Penalizaciones      | —      | Campos vacíos>5 → cap 40 · A reformar -5 |

| Label          | Rango       | Color    |
|----------------|-------------|----------|
| `alto`         | ≥ 80        | 🟢 verde |
| `medio`        | 50–79       | 🟡 amarillo |
| `normal`       | 0–49        | sin resaltar |
| `incompleto`   | >3 campos vacíos | 🔴 rojo |
| `bajada_precio`| (campo bool) | 🟣 morado |

---

## 🔔 Configurar Telegram (opcional)

1. Habla con [@BotFather](https://t.me/BotFather) → `/newbot` → anota el token.
2. Envía un mensaje a tu bot, luego visita:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   y busca `"chat":{"id":<numero>}`.
3. Añade ambos valores al `.env`.

---

## 🗂️ Estructura del proyecto

```
InversorInformado/
├── api/                          # Backend FastAPI
│   ├── main.py
│   ├── schemas.py
│   ├── routers/                  # listings, scraper, zones, export
│   └── services/                 # listings_service, scraper_service, export_service
├── frontend/                     # React + Vite + Tailwind
│   └── src/
│       ├── pages/                # Dashboard, SearchForm
│       ├── components/           # StatsCards, Filters, ListingsTable
│       ├── services/api.ts
│       └── types/index.ts
├── scraper/                      # Motor de scraping
│   ├── infrastructure/           # config, logger, http_client, db
│   ├── services/                 # normalizer, scorer, alerts
│   ├── scrapers/                 # idealista, fotocasa, habitaclia, pisos
│   ├── models.py
│   ├── runner.py
│   └── scheduler.py
├── config/
│   ├── search_targets.json       # URLs de búsqueda automática
│   └── zones.json                # Zonas disponibles por portal (~80 zonas)
├── docs/
│   └── templates/                # Mockups HTML de referencia visual de informes
│       ├── informe_inversion_piso.html
│       ├── informe_zona_inmobiliario.html
│       └── property_investment_marketplace.html
├── supabase/                     # Migraciones SQL
├── tests/                        # pytest: scorer, normalizer, http_client
├── .env                          # Variables de entorno (no en git)
└── requirements.txt
```

---

## 🧪 Tests

```powershell
pytest -v
```

Cubren scoring (espejo del SQL), normalización de datos y cliente HTTP.

---

## 📅 Automatización horaria — GitHub Actions

1. Sube el repo a GitHub (privado).
2. En **Settings → Secrets → Actions**, añade los valores del `.env` como secrets.
3. El workflow `.github/workflows/scrape.yml` se ejecuta cada hora automáticamente.
4. Ejecución manual: **Actions → Scrape viviendas → Run workflow**.

---

## 🛡️ Estado de los portales

| Portal     | Estado      | Notas |
|------------|-------------|-------|
| Habitaclia | Funcionando | 200 OK |
| Pisos.com  | Funcionando | 200 OK |
| Idealista  | Bloqueado   | 403 DataDome — requiere proxies |
| Fotocasa   | Verificar   | Comprobar URL en `search_targets.json` |

Para Idealista: añadir proxies rotativos en `SCRAPER_PROXIES` del `.env`.

---

## 🐛 Troubleshooting

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `supabase_not_configured` en logs | Variables incorrectas | Revisar `SUPABASE_URL` y `SUPABASE_KEY` en `.env` |
| 0 anuncios de Idealista | DataDome activo | Añadir proxies en `SCRAPER_PROXIES` |
| Frontend no carga | Backend no está corriendo | Arrancar `uvicorn api.main:app --reload` primero |
| Error al instalar deps | Python 3.14 incompatible | Usar `py -3.12 -m venv .venv` |
| Alertas no llegan | SMTP/Telegram sin configurar | Rellenar variables de notificación en `.env` |
| Selectores sin datos | El portal cambió su HTML | Revisar `raw_data` en Supabase y actualizar `scraper/scrapers/<fuente>.py` |

---

## ⚖️ Consideraciones legales y técnicas

- **Delays aleatorios** de 2–5 s entre peticiones para no sobrecargar los portales.
- **Uso personal**: el sistema está pensado para vigilancia propia; no redistribuyas los datos.
- **Frecuencia recomendada**: ciclo horario con ≤5 páginas por búsqueda.
- Si una fuente falla sostenidamente (403/429), revisa los logs en `logs/scraper.jsonl`.

---

## 📝 Licencia

Uso personal. No incluido para distribución comercial.
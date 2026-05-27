# Informes & Comunicaciones — Design Spec
**Fecha:** 2026-05-27  
**Estado:** Aprobado para implementación

---

## Resumen

Añadir dos nuevas secciones al menú de InversorInformado:

- **Informes** — generación y gestión de análisis de inversión por piso (documento A4, generado con IA, descargable como PDF)
- **Comunicaciones** — historial y gestión de publicaciones al canal de Telegram, incluyendo auto-publicación semanal con IA

---

## 1. Navegación

El nav actual pasa de:
```
Dashboard · Buscar · Carga · Revisión · Monitor
```
A:
```
Dashboard · Buscar · Carga · Revisión · Monitor · Informes · Comunicaciones
```

Rutas nuevas:
```
/informes            → Lista de análisis de piso generados
/informes/nuevo      → Formulario de creación de nuevo análisis
/informes/:id        → Vista del informe (HTML preview + PDF + Publicar)
/comunicaciones      → Historial Telegram + composición manual + estado auto-publicación
```

---

## 2. Modelo de datos

### Tabla `reports` (Supabase)

```sql
id           uuid PRIMARY KEY DEFAULT gen_random_uuid()
type         text NOT NULL DEFAULT 'analysis'   -- 'analysis' | futuro: 'mercado' | 'zona'
title        text NOT NULL
property_id  uuid REFERENCES listings(id) ON DELETE SET NULL
data         jsonb NOT NULL                      -- todos los campos del informe
created_at   timestamptz DEFAULT now()
```

Estructura del campo `data` para tipo `analysis`:
```jsonb
{
  "property": {
    "direccion": "Calle Provença 214, 3º 1ª",
    "municipio": "Barcelona",
    "barrio": "Eixample Dret",
    "precio": 385000,
    "metros": 93,
    "habitaciones": 3,
    "banos": 1,
    "estado": "buen estado",
    "url": "https://..."
  },
  "market": {
    "precio_m2_zona_medio": 4580,
    "precio_m2_zona_min": 3200,
    "precio_m2_zona_max": 5900,
    "alquiler_estimado_mes": 1750,
    "rentabilidad_bruta": 5.4,
    "rentabilidad_neta": 3.9,
    "demanda_alquiler": "muy_alta",
    "dias_hasta_alquiler": 8,
    "ai_estimated": true         -- indica si los datos de mercado son estimados por IA
  },
  "building": {
    "anyo_construccion": 1972,
    "ite_resultado": "favorable",
    "ite_fecha": "2023",
    "humedades": false,
    "ascensor": true,
    "electrica": "parcial",
    "cee": "D",
    "fondo_reserva": 28400
  },
  "scores": {
    "global": 77,
    "precio": 85,
    "rentabilidad": 81,
    "edificio": 63,
    "vecindario": 88
  },
  "amenities": {
    "transporte": 9.2,
    "colegios": 8.7,
    "salud": 8.4,
    "comercios": 9.5,
    "zonas_verdes": 6.1,
    "seguridad": 8.0,
    "ambiente": 8.9,
    "aparcamiento": 5.8
  },
  "verdict": "Este piso está un 9,6% por debajo del precio medio..."
}
```

### Tabla `telegram_log` (Supabase)

```sql
id          uuid PRIMARY KEY DEFAULT gen_random_uuid()
type        text NOT NULL    -- 'manual' | 'auto' | 'from_report'
content     text NOT NULL    -- texto enviado al canal
report_id   uuid REFERENCES reports(id) ON DELETE SET NULL
status      text NOT NULL DEFAULT 'sent'   -- 'sent' | 'failed'
sent_at     timestamptz DEFAULT now()
```

### Campo `last_featured_at` en tabla `listings`

```sql
ALTER TABLE listings ADD COLUMN last_featured_at timestamptz;
```

Permite al scheduler evitar repetir propiedades publicadas en los últimos 14 días.

---

## 3. Backend — Nuevos endpoints

### Routers nuevos

**`api/routers/reports.py`**

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/reports` | Lista todos los reports (paginado, filtro por tipo) |
| `POST` | `/api/reports` | Crea un nuevo report (guarda JSON en Supabase) |
| `GET` | `/api/reports/:id` | Detalle de un report (JSON) |
| `GET` | `/api/reports/:id/html` | Renderiza el template Jinja2 con los datos del report |
| `GET` | `/api/reports/:id/pdf` | Genera y devuelve PDF via WeasyPrint |
| `POST` | `/api/reports/ai-estimate` | Claude recibe datos del piso y devuelve estimados de mercado |

**`api/routers/telegram.py`** (ampliación del existente)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/telegram/log` | Lista el historial de mensajes enviados |
| `POST` | `/api/telegram/publish-report/:report_id` | Claude genera resumen del informe + link y publica |
| `POST` | `/api/telegram/generate-weekly` | Genera y publica el informe semanal automático (también llamado por scheduler) |

Los endpoints existentes `/api/telegram/publish` y `/api/telegram/status` no se modifican.

### Scheduler (APScheduler en FastAPI)

- **Cuándo**: lunes y jueves a las 10:00h
- **Qué hace**:
  1. Consulta las 5 propiedades con mayor score donde `last_featured_at IS NULL OR last_featured_at < now() - interval '14 days'`
  2. Llama a Claude con los datos de esas propiedades
  3. Claude genera el texto del informe semanal (resumen de oportunidades)
  4. Llama a `publish_to_channel(text)`
  5. Actualiza `last_featured_at = now()` en las 5 propiedades
  6. Guarda en `telegram_log`

### Template Jinja2

El archivo `informe_inversion_piso.html` se porta a `api/templates/reports/analysis.html.j2` usando variables Jinja2 para todos los valores dinámicos. El endpoint `/api/reports/:id/html` renderiza el template con los datos del report desde Supabase.

### Dependencias backend nuevas

```
weasyprint          # generación de PDF
APScheduler         # scheduler embebido en FastAPI
anthropic           # ya debe estar, para AI estimate y generación semanal
jinja2              # probablemente ya presente en FastAPI
```

---

## 4. Frontend — Nuevas páginas y componentes

### `/informes` — Página de listado

- Tabla/grid de reports existentes: título, fecha, barrio/municipio, score global, estado
- Botón "Nuevo análisis" (→ `/informes/nuevo`)
- Click en fila → `/informes/:id`
- Estado vacío con CTA si no hay informes

### `/informes/nuevo` — Formulario de creación

**Paso 1 — Seleccionar piso**
- Input de búsqueda sobre la tabla `listings` (por dirección, municipio, barrio)
- Al seleccionar, carga automáticamente: precio, m², habitaciones, baños, estado, barrio, municipio, url

**Paso 2 — Completar datos del informe**
- Sección "Datos del piso" (pre-cargados, editables)
- Sección "Datos de mercado" (vacíos por defecto):
  - Precio/m² zona (min, medio, max)
  - Alquiler estimado mensual
  - Rentabilidad bruta / neta
  - Demanda de alquiler
  - Días hasta alquiler
  - Botón **"Estimar con IA"** → llama a `POST /api/reports/ai-estimate` → rellena los campos con los estimados (marcados visualmente como "estimado por IA")
- Sección "Estado del edificio" (campos opcionales)
- Sección "Scores" (editables, con sugerencia de la IA)
- Sección "Veredicto" (textarea, con botón "Generar con IA")
- Botón "Guardar informe"

### `/informes/:id` — Vista del informe

- Panel izquierdo / header: metadatos (fecha, piso, score global)
- **Preview HTML**: el frontend hace fetch autenticado a `/api/reports/:id/html`, crea un Blob URL con el HTML recibido y lo inyecta en un iframe via `src={blobUrl}`. Esto evita el problema de que los iframes no envían el header `Authorization`.
- Botones:
  - "Descargar PDF" → fetch autenticado a `/api/reports/:id/pdf` + descarga via Blob URL (mismo patrón que el HTML)
  - "Publicar en Telegram" → POST `/api/telegram/publish-report/:id` con confirmación
- Indicador si los datos de mercado son estimados por IA

### `/comunicaciones` — Telegram

- **Sección "Auto-publicación"**: estado del scheduler (activo/inactivo), próxima ejecución programada, botón "Ejecutar ahora"
- **Sección "Nueva publicación manual"**: formulario (tipo, título, cuerpo, zona opcional) + preview del mensaje + botón "Publicar"
- **Sección "Historial"**: tabla con todos los mensajes enviados (fecha, tipo, primeras líneas del texto, estado enviado/fallido)

### Servicios API frontend nuevos (`frontend/src/services/api.ts`)

```typescript
// Reports
fetchReports(): Promise<Report[]>
createReport(data: ReportCreateIn): Promise<Report>
fetchReport(id: string): Promise<Report>
getReportHtmlUrl(id: string): string        // URL directa para iframe src
getReportPdfUrl(id: string): string         // URL directa para descarga
aiEstimateReport(propertyData: PropertyData): Promise<MarketEstimate>

// Telegram
fetchTelegramLog(): Promise<TelegramLogEntry[]>
publishReport(reportId: string): Promise<{ status: string }>
generateWeeklyReport(): Promise<{ status: string }>
```

---

## 5. Integración de IA (Claude)

### 1. Estimación de datos de mercado (`/api/reports/ai-estimate`)

**Input**: municipio, barrio, precio, m², habitaciones, estado del piso  
**Output**: precio/m² zona (min/medio/max), alquiler estimado, rentabilidad bruta/neta estimada, demanda alquiler, días hasta alquiler, scores sugeridos, veredicto  
**Nota**: los datos se marcan como `ai_estimated: true` en el JSON guardado, visible para el usuario en la interfaz

### 2. Publicación de informe a Telegram (`/api/telegram/publish-report/:id`)

**Input**: datos del report (property, market, scores, verdict)  
**Output**: texto de 3-5 líneas con los datos más destacados del informe + enlace al informe completo en la app  
Formato: texto + HTML tags de Telegram (bold, italic) + URL de login/informe al final

### 3. Informe semanal automático (`generate-weekly` / scheduler)

**Input**: lista de 5 propiedades (datos del scraper)  
**Output**: texto del informe semanal para el canal (formato existente de `reports.py` + oportunidades concretas)

---

## 6. Flujo de publicación a Telegram desde un informe

El canal público @inversorinformado recibe un mensaje así:

```
📊 ANÁLISIS DE INVERSIÓN · Eixample Dret, Barcelona
─────────────────────────────────
🏠 Piso 93m² · 3 hab · 385.000 €
💶 Precio/m²: 4.140 € (media zona: 4.580 €) · -9,6%
📈 Rentabilidad bruta: 5,4% · Media: 4,1%
⭐ Score global: 77/100 (B+)

👉 Análisis completo en plataforma:
https://inversorinformado.vercel.app/login
```

El enlace lleva al login de la plataforma. Solo usuarios registrados acceden al informe completo. Esto convierte el canal en top-of-funnel hacia la plataforma.

---

## 7. Fuera de alcance (esta fase)

- Tipos de informe adicionales (mercado, zona) — misma arquitectura, se añaden en fases posteriores
- Autenticación del canal Telegram (mensajes privados / grupos premium)
- Envío de PDF directamente por Telegram (posible extensión futura)
- Integración con APIs externas de datos de mercado (Idealista API, INE)
- Notificaciones email desde Comunicaciones

---

## 8. Resumen de archivos nuevos/modificados

### Backend
- `api/routers/reports.py` — nuevo router
- `api/routers/telegram.py` — ampliado con log y publish-report
- `api/services/reports_service.py` — lógica de generación, AI estimate, scheduler
- `api/templates/reports/analysis.html.j2` — template Jinja2 portado desde `Templates_Informes/`
- `api/main.py` — registrar nuevo router + iniciar APScheduler
- `requirements.txt` — añadir weasyprint, apscheduler

### Frontend
- `frontend/src/pages/Informes.tsx` — listado de reports
- `frontend/src/pages/InformeNuevo.tsx` — formulario creación
- `frontend/src/pages/InformeDetalle.tsx` — vista informe
- `frontend/src/pages/Comunicaciones.tsx` — Telegram hub
- `frontend/src/services/api.ts` — nuevas funciones
- `frontend/src/App.tsx` — nuevas rutas y nav links
- `frontend/src/types/index.ts` — nuevos tipos Report, TelegramLogEntry

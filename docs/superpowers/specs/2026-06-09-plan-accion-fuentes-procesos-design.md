# Plan de Acción — Fuentes de Datos y Procesos del Sistema

**Fecha:** 2026-06-09
**Estado:** Borrador para validación (socio + Andrés)
**Tipo:** Documento maestro de roadmap (estrategia y secuenciación, NO implementación)
**Autor de la sesión:** Kevin (info@riquezadigital.es) + Claude

---

## Cómo leer este documento

Este NO es un spec de implementación. Es el **mapa maestro** que organiza todo lo que queremos
construir en torno a dos ejes —**fuentes de datos** y **procesos**— los prioriza y los secuencia
en fases. Cada bloque grande del roadmap tendrá después su propio ciclo
`spec → plan → implementación` por separado.

- **Parte A** — Fuentes de datos (cómo rellenamos el "data center")
- **Parte B** — Procesos (los 12 procesos del sistema)
- **Parte C** — Secuencia de fases (el roadmap priorizado)
- **Parte D** — Registro de decisiones (qué decidimos, qué alternativas había, para validar/virar)
- **Parte E** — Constraints y riesgos transversales
- **Parte F** — Preguntas abiertas pendientes

> **Nota para el socio y Andrés:** la **Parte D** está pensada para vosotros. Recoge cada
> decisión tomada en la sesión de brainstorming con sus alternativas, para que podáis confirmar
> el rumbo o cambiarlo antes de que se invierta esfuerzo de desarrollo.

---

## Contexto: qué existe HOY en el sistema

Antes de planificar lo nuevo, esto es lo que ya está construido y funcionando:

- **Scraping** de Fotocasa, Idealista, Habitaclia, Pisos.com → `normalizer` → `scorer` →
  tabla `listings` en Supabase. (`scraper/`)
- **Carga manual** (`frontend/src/pages/Carga.tsx`) y **revisión de duplicados** (`Review.tsx`).
- **Informes** generados con IA (Claude) + PDF (WeasyPrint) + template Jinja2
  (`api/routers/reports.py`, `api/templates/reports/analysis.html.j2`).
- **Comunicaciones Telegram** con auto-publicación semanal vía scheduler APScheduler
  (`api/routers/telegram.py`).
- **Scoring** por piso basado en datos del scraping (`scraper/services/scorer.py`).
- Esquema de datos ya migrado a campos `condition`, `status`, `ocupacion`, `situacion_legal`
  + ~26 campos de amenities (`scraper/models.py`).

El roadmap de este documento **construye sobre** esta base; no la reemplaza.

---

# PARTE A — Fuentes de datos

Objetivo: rellenar la mayor cantidad de campos del `Listing` con el mejor dato disponible,
al menor coste y riesgo. Las fuentes se ordenan por **viabilidad bajo nuestro ámbito
(nacional)** y por ROI.

### Tabla resumen

| # | Fuente | Viabilidad nacional | Coste | Automatización | Estado |
|---|--------|---------------------|-------|----------------|--------|
| 1 | **Scraping portales** (Fotocasa, Idealista, Habitaclia, Pisos) | ✅ Total | Gratis | Total | ✅ Ya existe |
| 2 | **Catastro (OVC web service)** | ✅ Servicio nacional | Gratis | Total | 🆕 Nuevo |
| 3 | **Google Maps / Places API** | ✅ Cobertura nacional | 💶 De pago (controlado) | Total | 🆕 Nuevo |
| 4 | **INE + Mº Interior (datos abiertos)** | ✅ Nacional por municipio/sección | Gratis | Batch | 🆕 Nuevo |
| 5 | **Contacto propietario / inmobiliaria (agente IA)** | ⚠️ Solo quien publicó contacto | Gratis | Semi-auto | 🆕 Fase tardía (riesgo legal) |
| 6 | **Documentos del dueño (ITE, actas, CEE) — PDF** | ⚠️ Subida manual | Gratis | LLM parsing post-subida | 🆕 Nuevo |
| 7 | **Registro de la Propiedad / cargas** | ❌ No automatizable gratis | 💶 ~9 €/nota simple | Manual / bajo demanda | 🆕 Limitado |

Leyenda: ✅ viable · ⚠️ viable con condiciones · ❌ no viable automáticamente

---

### A.1 — Scraping de portales *(ya existe)*

- **Aporta:** la mayoría de campos base — precio, m², habitaciones, baños, planta, extras,
  ubicación, fotos (URLs), descripción.
- **Cómo:** scrapers ya implementados en `scraper/scrapers/`.
- **Pendiente de decidir/ampliar:**
  - **Fotos:** decisión tomada = **híbrido** (ver D-4). Guardar URLs de todas; descargar y
    almacenar (Supabase Storage/S3) solo las de pisos top o cuando se genera informe.
  - Posible extracción de **teléfono/email del anunciante** cuando esté publicado
    (habilita la fuente A.5 de forma conforme).
- **Riesgo:** fragilidad ante cambios de los portales (ya asumido hoy).

### A.2 — Catastro (Sede Electrónica del Catastro — OVC) 🆕

- **Por qué es la primera fuente nueva:** gratuita, **cobertura nacional homogénea**, y mayor
  ROI inmediato. Permite **validar el anuncio** (cuadrar m², uso, ubicación) y aporta datos
  que el anuncio suele omitir.
- **Aporta:**
  - Año de construcción → cálculo de **obligación de ITE/IEE** (edificios > X años).
  - Superficie catastral (cruce con m² del anuncio → detectar discrepancias).
  - Uso del inmueble, referencia catastral, antigüedad.
- **Cómo:** servicios web públicos OVC (Consulta de Datos No Protegidos por referencia
  catastral o por dirección/coordenadas). Formato SOAP/REST, sin coste, sin login.
- **Alimenta campos:** `anyo_construccion` (nuevo), validación de `metros_cuadrados`,
  `tipo_propiedad`, y deriva la obligación ITE (modelo de 3 niveles del análisis de ITE
  realizado el 2026-06-02: automático Catastro → semi-auto registros → manual PDF).
- **Riesgo:** bajo. Datos protegidos (titularidad) NO accesibles —no los necesitamos.

### A.3 — Google Maps / Places API 🆕

- **Aporta (bloque "vecindario / amenities" de los informes):**
  - Nivel de servicios (comercios, salud, colegios, transporte, ocio).
  - Tráfico y conectividad.
  - **Fotos reales del exterior del edificio y del entorno** (Street View / fotos de lugares)
    para evaluar estado de conservación de zona y cubierta cuando el anuncio no las muestra.
- **Cómo:** Google Maps Platform (Places API, Street View Static API). De pago, pero con
  cuota controlada y **solo sobre pisos mejor valorados** (ver D-2), el coste es acotado.
- **Alimenta:** scores de amenities (`transporte`, `colegios`, `salud`, `comercios`,
  `zonas_verdes`, `seguridad`, `ambiente`, `aparcamiento`) que ya consume el template de informe.
- **Riesgo:** coste si se dispara el volumen → mitigado por el disparador "solo top".

### A.4 — INE + Ministerio del Interior (datos abiertos) 🆕

- **Aporta (a nivel municipio / sección censal):**
  - Demografía, renta media, tasas de ocupación/vivienda.
  - **Criminalidad** → fuente real es el **Portal Estadístico del Mº Interior** (no el INE).
  - Turismo (INE: encuesta de ocupación, viviendas turísticas).
  - Indicadores socioeconómicos y de entorno.
- **Cómo:** descargas batch / APIs de datos abiertos (INE Tempus, Mº Interior). Se cachean
  por municipio; no se consultan por piso individual (son datos de zona).
- **Alimenta:** contexto de zona en informes y rating (señal de zona, no de piso).
- **Nota de expectativas:** "felicidad / convivencia / clima" no existen como dataset oficial
  directo. Se aproximan con proxies (renta, criminalidad, servicios) o se descartan. Ver F-2.
- **Riesgo:** bajo. Trabajo principal = ETL y normalización por código de municipio.

### A.5 — Contacto con propietario / inmobiliaria (agente IA) 🆕 ⚠️

- **Aporta (lo que ninguna fuente pública da):**
  - Estado del ITE y desperfectos a arreglar; **copia del ITE** si la tiene.
  - **Actas de las últimas 3 juntas** → derramas abiertas, morosidad, temas pendientes.
  - Cargas pendientes del piso.
  - Costes recurrentes: IBI, gastos de comunidad.
  - CEE si no está en el anuncio; estado de suministros (altas, cortes, cargas).
  - Ocupación, nuda propiedad, temas críticos del estado.
  - **Visitabilidad:** si el piso se puede ver y la dificultad para visitarlo (NO concertar
    visitas reales — solo entender disponibilidad y fricción).
- **Cómo (postura legal acordada, ver D-3):** **solo se contacta a propietarios/inmobiliarias
  que ya publicaron su teléfono/email en el anuncio**, con propósito legítimo declarado, el
  agente **identificándose como asistente** (no fingir ser un humano anónimo), con opt-out y
  registro RGPD. Mail y/o WhatsApp.
- **Por qué es fase tardía:** es la pieza de **mayor riesgo legal** (RGPD, LSSI, comunicaciones
  comerciales no solicitadas). Se diseña pero queda **bloqueada hasta validación legal** y
  hasta tener el resto de fuentes consolidadas.
- **Alimenta:** campos premium del informe + la fuente A.6 (documentos que el dueño envíe).

### A.6 — Documentos aportados por el dueño (ITE, actas, CEE) — PDF 🆕

- **Aporta:** el detalle fino que solo está en los documentos (deficiencias concretas del ITE,
  acuerdos de juntas, derramas exactas).
- **Cómo:** **subida manual** (por el dueño vía A.5, o por el usuario de la plataforma) +
  **parsing con LLM** para extraer campos estructurados. Coherente con el modelo de 3 niveles
  de ITE: (1) automático Catastro, (2) semi-auto registros, (3) manual PDF.
- **Riesgo:** bajo técnicamente; depende de que lleguen los documentos (depende de A.5).

### A.7 — Registro de la Propiedad / cargas administrativas 🆕 ❌(auto)

- **Aporta:** cargas reales, hipotecas, embargos, situación jurídica del inmueble.
- **Realidad:** la **nota simple** del Registro **no es gratuita ni scrapeable** (~9 €, vía
  registradores.org, con identificación). No existe fuente pública gratuita de cargas por piso.
- **Cómo:** queda como **paso manual / bajo demanda de pago**, típicamente solo para un piso
  que un cliente va a comprar (informe premium / due diligence). No es enriquecimiento masivo.
- **Alimenta:** `situacion_legal` (a nivel confirmado) solo en casos puntuales.

---

# PARTE B — Procesos

Los 12 procesos descritos, con estado, disparador y dependencias. Se agrupan por familia.

### Familia 1 — Ingesta del catálogo

**P1. Carga de pisos** *(parcial: existe)*
- Subprocesos: **P1a carga automática** (scraping, ✅ existe) y **P1b carga manual**
  (`Carga.tsx`, ✅ existe).
- Disparador: cron (auto) + acción usuario (manual).

**P2. Revisión periódica de anuncios** 🆕
- Cada 10/15/30 días (recomendado: **revalidación escalonada**, ver D-5), revisita los anuncios
  guardados para confirmar que siguen **activos** y detectar **cambios** (precio, estado).
- Disparador: cron. Salida: actualiza `status`, `bajada_precio`, `ultima_actualizacion`.

### Familia 2 — Enriquecimiento del dato

**P3. Carga de datos adicionales (enriquecimiento)** 🆕 — *núcleo de la prioridad actual*
- Recorre las fuentes de la Parte A y rellena los campos del piso.
- Disparador: tras P1 (baseline) + cron de re-enriquecimiento, **solo sobre pisos top** (D-2).
- Es el proceso que materializa las fuentes A.2–A.7.

### Familia 3 — Inteligencia / rating

**P9. Gestión del rating de pisos** 🆕 — con 3 subprocesos:
- **P10. Gestión inicial del rating:** calcula el rating con toda la info cargada + comparación
  contra el resto de viviendas.
- **P11. Revisión periódica del rating:** cada 10/15/30 días revalida que el rating se mantiene.
- **P12. Normalización "Campana de Gauss" por zonas:** evita que haya demasiados pisos con la
  máxima nota; fuerza una distribución diversificada **por barrio** para un cribado fino.
- **Dependencia clave:** necesita datos enriquecidos (P3). Por eso va **después** del
  enriquecimiento. Resuelto el huevo-gallina con scoring de dos niveles (ver D-6).

### Familia 4 — Funnel y monetización *(todo nuevo; nada en producción aún)*

**P4. Informes y mensajes automatizados — Telegram freemium** 🆕
- Subproceso: **P4b interacción con usuarios** cuando responden a los mensajes.
- (Existe la auto-publicación semanal al canal; falta el modelo freemium con interacción.)

**P5. Informes automatizados — Premium (Telegram + WhatsApp)** 🆕
- Envío personalizado por zonas de interés / listados de propiedades a cada usuario de pago.

**P6. Push de upselling** 🆕
- Mover freemium → pago, y pago → siguiente nivel. Basado en comportamiento en el funnel.

**P7. Informes bajo demanda** 🆕
- Usuario solicita informe específico → formulario (qué informe, datos del piso) → **pago** →
  generación y entrega automática.

**P8. Retención / anti-churn** 🆕
- Detecta clientes inactivos o en riesgo de pérdida y lanza procesos de reenganche al panel.

### Mapa de dependencias entre procesos

```
P1 (carga) ──► P2 (revisión activos)
     │
     └──► P3 (enriquecimiento) ──► P9/P10/P11/P12 (rating + Gauss)
                                          │
                                          └──► P4,P5,P7 (informes freemium/premium/demanda)
                                                     │
                                                     └──► P6 (upselling), P8 (retención)
```

El dato (P1→P3→P9) es el cimiento; el funnel (P4–P8) se apoya en él. Por eso el roadmap
prioriza la columna izquierda primero.

---

# PARTE C — Secuencia de fases (roadmap)

**Premisas que fijan este orden** (ver Parte D): prioridad = **calidad/profundidad del dato**;
ejecuta **Andrés (senior) + Claude**; **nada monetizado en producción aún**; ámbito **nacional**;
**preferencia gratis, pago si aporta mucho**; enriquecer **solo los mejor valorados**.

| Fase | Nombre | Contenido | Procesos / Fuentes | ¿Por qué aquí? |
|------|--------|-----------|--------------------|----------------|
| **0** | Cimientos de datos | Modelo de enriquecimiento (procedencia + frescura por dato), scoring de 2 niveles, storage de fotos híbrido | Base de A.1, P3 (infra) | Habilita todo lo demás |
| **1** | Catastro | Integración OVC: validación anuncio, año construcción, obligación ITE | A.2 | Gratis, nacional, máximo ROI |
| **2** | Entorno (Places + INE) | Amenities, servicios, criminalidad, demografía de zona | A.3, A.4 | Completa el bloque "vecindario" de informes |
| **3** | Rating Gauss por zonas | Rating inicial + revisión + normalización Gauss | P9, P10, P11, P12 | Ya hay datos que ratear |
| **4** | Ciclo de vida del catálogo | Revisión periódica de anuncios + enriquecimiento programado | P2, P3 (cron) | Mantiene vivo y fresco el dato |
| **5** | Documentos manuales | Subida de ITE/actas/CEE + parsing LLM | A.6, (A.7 puntual) | Profundidad fina, depende de subida manual |
| **6** | Funnel freemium | Telegram freemium + interacción | P4, P4b | Empieza monetización sobre dato sólido |
| **7** | Premium + bajo demanda | Informes premium (TG/WhatsApp) + informes de pago bajo demanda | P5, P7 | Requiere pasarela de pago |
| **8** | Crecimiento | Upselling + retención/anti-churn | P6, P8 | Optimiza un funnel ya en marcha |
| **Tardía / bloqueada** | Agente IA a propietarios | Outreach conforme a quien publicó contacto | A.5 | Alto riesgo legal — tras validación |

> Las fases 0–5 cumplen la prioridad declarada (**dato**). Las fases 6–8 (funnel) llegan
> **después** de consolidar el dato, salvo que el socio decida virar (ver D-1).

---

# PARTE D — Registro de decisiones

> Esta sección documenta cada decisión de la sesión, **la opción elegida** y las
> **alternativas descartadas** con su trade-off. Pensada para que el socio y Andrés validen
> el rumbo o propongan virar. Si se cambia una decisión, conviene anotar la fecha y el motivo.

### D-1. Prioridad de los próximos 1-3 meses
- **Elegido:** Calidad / profundidad del dato (enriquecer con nuevas fuentes).
- **Alternativas descartadas:**
  - *Convertir y monetizar usuarios* (funnel premium/upselling/retención) — descartada como
    primera prioridad: monetizar sobre un dato pobre limita el valor diferencial.
  - *Volumen y fiabilidad del catálogo* (escalar nº de pisos) — útil, pero más pisos con poco
    dato no es el cuello de botella ahora.
  - *Sistema de rating diferencial* — es el objetivo, pero depende del dato; va después.
- **Si se vira:** subir las fases 6–8 (funnel) por delante de 3–5.

### D-2. ¿A qué pisos se aplica el enriquecimiento costoso?
- **Elegido:** Solo a los mejor valorados (por score baseline).
- **Alternativas descartadas:**
  - *Todos, por niveles* (barato a todos, caro solo a top) — más cobertura, más coste/complejidad.
  - *Bajo demanda* (solo al generar informe) — el más barato, pero deja el catálogo "frío" y
    resta valor a los listados automáticos.
- **Consecuencia:** obliga al scoring de 2 niveles (D-6).

### D-3. Postura legal del agente IA que contacta propietarios
- **Elegido:** Contactar **solo a quien publicó su contacto** en el anuncio, con propósito
  legítimo, identificándose como asistente, con opt-out y registro RGPD.
- **Alternativas descartadas:**
  - *Outreach 100% conforme a cualquiera* — más alcance, pero más exposición legal y necesidad
    de base jurídica más sólida.
  - *Aparcar como fase tardía sin más* — se mantiene parte de esto: sigue siendo fase tardía.
  - *Asistido por humano* (IA redacta, humano envía) — opción de mitigación válida si la
    validación legal lo exige; queda como fallback recomendado.
- **Nota importante:** se descartó explícitamente "simular humano anónimo" por ser potencialmente
  **engañoso** y agravar el riesgo legal (RGPD/LSSI). El agente siempre se identifica.

### D-4. Almacenamiento de fotos del scraping
- **Elegido:** **Híbrido** — URLs para todos; descarga y almacenamiento propio solo para pisos
  top o al generar informe.
- **Alternativas descartadas:**
  - *Solo URLs* — barato, pero las imágenes caducan al desaparecer el anuncio.
  - *Descargar y almacenar todo* — permanencia y permite visión IA, pero más coste y riesgo de
    copyright.

### D-5. Ámbito geográfico
- **Elegido:** Nacional / cualquier municipio.
- **Consecuencia:** las fuentes **municipales** (registros ITE locales, datos abiertos de un
  ayuntamiento) quedan **best-effort o descartadas**; se priorizan fuentes **nacionales
  homogéneas** (Catastro, INE, Mº Interior, Google).
- **Alternativas descartadas:**
  - *Una sola ciudad* — permitiría explotar datos municipales en profundidad (p. ej. registro
    ITE de Barcelona), pero limita el mercado.
  - *Pocas ciudades grandes* — equilibrio intermedio; reconsiderar si se concentra el catálogo.

### D-6. Scoring de dos niveles (resuelve huevo-gallina dato↔rating)
- **Elegido:** **Score baseline barato** con datos del scraping (ya existe `scorer.py`) decide a
  qué pisos enriquecer; el **rating fino** (P9) se calcula después con los datos enriquecidos.
- **Alternativa descartada:** un único rating que requiriera todos los datos para todos los pisos
  → inviable con D-2 (solo enriquecemos los top).

### D-7. Presupuesto de APIs
- **Elegido:** Preferencia gratis; pago donde aporte mucho y con coste controlado (p. ej. Google
  Places solo sobre top).
- **Alternativas descartadas:**
  - *Solo gratis / scraping* — cero coste, más fragilidad y menos cobertura (Street View, Places).
  - *Presupuesto abierto* — aceleraría, pero no es la postura actual.

### D-8. Naturaleza del entregable de esta sesión
- **Elegido:** Documento maestro de Plan de Acción (este doc).
- **Alternativas descartadas:** plan + spec del primer bloque; o empezar a implementar ya.
- **Siguiente paso natural:** convertir la **Fase 0/1** en su propio spec cuando se decida arrancar.

---

# PARTE E — Constraints y riesgos transversales

- **Municipal vs nacional:** por D-5, no se integran registros ITE municipales; el nivel
  "detalle de deficiencias ITE" solo llega por documento manual (A.6), no automatizado.
- **Registro de la Propiedad:** sin fuente pública gratuita de cargas; queda manual/de pago y
  puntual (A.7).
- **Riesgo legal del outreach (A.5):** requiere validación jurídica antes de activarse;
  bloqueante de esa fase.
- **Fragilidad del scraping:** los portales cambian; coste de mantenimiento continuo (ya asumido).
- **Coste de APIs:** controlado por el disparador "solo top" (D-2) y por cachear datos de zona
  (A.4) en lugar de consultarlos por piso.
- **Copyright de imágenes:** la descarga selectiva (D-4) limita exposición, pero conviene revisar
  términos de uso de los portales.
- **Procedencia y frescura del dato:** cada campo enriquecido debería registrar de qué fuente
  viene y cuándo se obtuvo (se diseña en Fase 0), para auditar y revalidar.

---

# PARTE F — Preguntas abiertas pendientes

Se resolverán al especificar cada fase; no bloquean la aprobación de este roadmap.

- **F-1.** Rating Gauss: ¿estricto (curva forzada por barrio) o blando (penalización suave a la
  concentración de notas altas)? ¿Qué define "barrio" cuando el dato de barrio es pobre?
- **F-2.** INE/entorno: ¿qué indicadores entran en el score de zona y cuáles se descartan por no
  existir como dataset (p. ej. "felicidad")?
- **F-3.** Cadencia de revisión (P2/P11): ¿10, 15 o 30 días? ¿Escalonada según antigüedad/score?
- **F-4.** Modelo de tiers de monetización (freemium/premium) y pasarela de pago a usar (Stripe?)
  — se define al llegar a Fase 6.
- **F-5.** Umbral de "piso top" que dispara el enriquecimiento costoso (percentil de score).
- **F-6.** WhatsApp: ¿API oficial (WhatsApp Business Platform) o alternativa? Afecta a A.5 y P5.

---

## Próximos pasos

1. **Validación** de este documento por el socio y Andrés (especial atención a la Parte D).
2. Si se aprueba el rumbo: convertir **Fase 0 + Fase 1 (Catastro)** en un spec de implementación
   con su propio ciclo `spec → plan → ejecución`.
3. Si se decide virar: ajustar la Parte C según la decisión revisada en la Parte D.

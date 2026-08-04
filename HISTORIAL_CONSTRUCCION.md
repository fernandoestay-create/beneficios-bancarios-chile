# Historial de construcción — MiCartera Scrapers + Bot

> Cronología de decisiones y construcción del proyecto.
> Pensado para: una nueva IA que llegue al proyecto, o yo mismo retomándolo en 3-6 meses.
> Cada entrada es una sesión productiva o un hito significativo.

---

## 📋 Índice

| Sesión | Fecha | Hito principal |
|--------|-------|----------------|
| 1 (inferida) | ~2026-03 | Build inicial: 15 scrapers + API + página web + bot WhatsApp + RAG |
| 2 (inferida) | 2026-03-15 | Documentación V01 + ARCHITECTURE.md + SETUP_GUIDE.md, deploy estable en Render |
| 3 | 2026-05-26 | Migración al sistema workspace `Claude_code/` (FORMA: solo documentación) |
| 4 | 2026-06-01 | Fix Falabella (Playwright→requests/SSR): 0→86 beneficios en producción |
| 5 | 2026-06-02 | Calidad 100% (v1.3–v1.6): Santander browserless, BICE/ids cleanup, cards sin texto |
| 6 | 2026-06-22 | **Auto-monitoreo + resiliencia + aprendizaje**: red de seguridad, chequeo experto por banco, refresco local desde Chile, auditoría de credibilidad, Consorcio 50%, mail diario, aprendizaje |
| 7 | 2026-06-23 | Fix JS de `/ver` (L-21) + correo alineado a **09:00 Chile** + refresco a **08:30** (no chocan, L-22/L-23) |
| 8 | 2026-07-01 | **Apartado de Cuotas sin interés** (`/ver/cuotas`): curado + trazable por banco/categoría, logos+mes, en el correo (L-24) |
| 9 | 2026-07-29 | **Auditoría ácida de filtros/búsqueda + seguridad**: 5 bugs "el dato existe pero no se muestra" (277 nacionales sin pin), buscador comuna+tags, endpoints destructivos eliminados, Falabella nombres reales (L-28) |
| 10 | 2026-08-03 | **Guardia de madrugada + apartado "Otros beneficios"**: check determinista 03:00 (cada bug conocido = un check), Falabella local+trazable, dataset separado `beneficios_otros.json` (228 no-restaurante) sin tocar `/ver` |
| 11 | 2026-08-03 | **Trazabilidad total + filtros dinámicos (v2.0)**: "Otros beneficios" filtrado 228→24 verificables, auditoría de trazabilidad de los 4 datasets, bencina re-curada desde fuente oficial (5 errores corregidos), guardia ampliada a trazabilidad, filtros de día dinámicos |

> Nota: las sesiones 1 y 2 son inferidas de fechas de archivos y metadata. No hubo cronología explícita previa a la migración.

---

## 📅 Sesiones

### Sesión 1 (inferida) — ~2026-03 — Build inicial completo

**Contexto previo:**
Fernando quería agregar beneficios bancarios chilenos para MiCartera. Decisión inicial: cubrir el vertical más visible (descuentos en restaurantes) y construir el stack completo: scrape → almacenamiento → API → web → bot WhatsApp.

**Decisiones tomadas:**
- **Scraping individual por banco** (15 clases independientes) en vez de un scraper genérico configurable — los 15 sitios son muy heterogéneos (APIs CMS, HTML, JS embebido).
- **Archivos planos `beneficios.json` / `.csv`** en vez de DB relacional — el volumen es chico (985 items, ~1.2 MB) y simplifica deploy.
- **Pinecone para RAG** (no pgvector) — decisión heredada de proyectos legacy; hoy se mantiene como deuda técnica.
- **Monolito en `api.py`** mezclando API REST + página web HTML embebido + webhook WhatsApp + RAG — deploy simple a Render con 1 servicio.
- **Render como hosting** — auto-deploy desde GitHub.

**Lo que se construyó:**
- `scrapers.py` (~3162 líneas): 15 clases scraper + dataclass `Beneficio` + `OrquestadorScrapers` con normalización (fechas DD-MMM-AAAA, regiones unificadas, comunas RM, descuentos "X% dcto.").
- `api.py` (~1586 líneas): FastAPI con endpoints `/`, `/beneficios`, `/buscar`, `/bancos`, `/estadisticas`, `/restaurantes/top`, `/rag`, `/scrape/ejecutar`, `/ver`, `/webhook`.
- Página web `/ver`: HTML/CSS/JS embebido en f-string Python con filtros multi-select (banco, día, zona, comuna, descuento mínimo, modalidad), 2 vistas (tarjetas + mapa Leaflet).
- Bot WhatsApp en `/webhook`: flujo conversacional de 3 pasos (banco → día → comida) + consulta libre con RAG (Pinecone + GPT-4o-mini).
- `upload_pinecone.py`: vectorización de 985 beneficios con `text-embedding-3-small`.
- `whatsapp_bot.py`: bot alternativo Flask sin IA (legacy).

**Lo que NO se hizo (y por qué):**
- Geocoding real por dirección: usa coordenadas aproximadas por región. Razón: complejidad y costo de geocoding para 985 items no justifica precisión adicional.
- Persistencia del estado conversacional del bot: `user_flow` vive en memoria del proceso. Razón: simple y suficiente para escala actual.
- Migración a pgvector: Pinecone ya estaba funcionando. Razón: no romper lo que funciona.

**Estado al final de la sesión:**
Sistema completo en producción en https://api-beneficios-chile.onrender.com/ver. 985 beneficios. 15 bancos. Bot WhatsApp funcionando vía Twilio.

---

### Sesión 2 (inferida) — 2026-03-15 — Documentación V01

**Contexto previo:**
Sistema funcionando pero sin documentación formal para handoff o referencia futura.

**Decisiones tomadas:**
- Crear documentación natural en HTML estático (6 documentos: resumen, arquitectura, scrapers, API+web, bot, combustibles) + Memoria en DOCX/PDF.
- Crear documentación técnica en `ARCHITECTURE.md`, `SETUP_GUIDE.md`, `DOCUMENTACION_V01.md`, luego `DOCUMENTACION_V02.md`.

**Lo que se construyó:**
- Carpetas `00.Información_propia_explicación/` y `00.Informacion_proyecto/` con HTMLs (duplicado parcial).
- Documentación técnica en `beneficios-bancarios-chile/`.

**Estado al final:**
Documentación completa, sistema estable en producción.

---

### Sesión 3 — 2026-05-26 — Migración al sistema workspace

**Contexto previo:**
Fernando consolidó un sistema workspace `Claude_code/` con estructura canónica (CLAUDE.md, ESTADO.md, LECCIONES_APRENDIDAS.md, etc.). Este proyecto era legacy con nombre que tiene espacios y sin los archivos canónicos.

**Decisiones tomadas:**
- **Migrar al nivel raíz** (no al sub-proyecto `beneficios-bancarios-chile/`).
- **Preservar nombre legacy con espacios** ("01.Scraping y bot descuentos").
- **NO tocar código** (.py, .json, .yaml).
- **NO tocar docs técnica** existente en `beneficios-bancarios-chile/`.
- **Documentar las 2 carpetas duplicadas** de docs natural como "decisión humana pendiente", sin borrar ninguna.

**Lo que se construyó:**
- `CLAUDE.md` con @imports del workspace.
- `README.md`, `ESTADO.md`, `LECCIONES_APRENDIDAS.md`, `HISTORIAL_CONSTRUCCION.md` (este archivo), `ENTREGA_FINAL.md`.
- Carpeta `docs/` con `01_contexto.md`, `02_arquitectura.md`, `03_decisiones.md`, `04_runbook.md` (rellenado con info inferida del proyecto, dejando `[Por completar]` donde no se podía inferir).

**Lo que NO se hizo:**
- No se creó `00.Información_propia_explicación/index.md` ni `build_html.py` — la docs natural ya estaba en HTML estático, no en .md.
- No se unificaron las 2 carpetas duplicadas — requiere decisión humana.
- No se modificó nada en `beneficios-bancarios-chile/`.

**Estado al final:**
Proyecto alineado con la estructura canónica del workspace en términos de FORMA. El FONDO (código, datos, deploy) no cambió.

---

### Sesión 4 — 2026-06-01 — Fix Falabella (Playwright → requests/SSR)

**Contexto previo:**
Fernando reportó: "No me aparece los descuentos de banco falabella, revisar que pasa". En producción (`/ver`) no salía ningún beneficio Falabella.

**Diagnóstico (causa raíz confirmada end-to-end):**
- Banco Falabella migró su sitio a **Next.js con datos embebidos como payload RSC** (React Server Components) escapado dentro del HTML, anclado en `"discountDays":[`.
- El scraper viejo de Falabella usaba **Playwright + Contentful** e intentaba `playwright install chromium` en runtime.
- En producción, un **auto-scraper diario** (cron que pushea commits "🔄 Actualizar beneficios y bencinas") re-scrapea y Render auto-redeploya. Pero ese entorno **no corre Chromium** → el scraper Falabella devolvía **0** cada día → producción quedaba con 0 Falabella aunque el resto de bancos sí se actualizaba.

**Decisiones tomadas:**
- **Reescribir SOLO la clase `ScraperBancoFalabella`** (regla del proyecto: tocar solo el banco afectado, no el orquestador ni otras clases).
- **Enfoque requests plano + brace-matching** sobre el RSC (sin browser, sin token, compatible con Render/CI). Anclar en `"discountDays":[`, hacer rfind del `{` contenedor, balancear llaves hacia adelante (string-aware), `json.loads`, dedup por `linkUrl`.
- **NO re-scrapear los otros 12 bancos** (regla: no regenerar beneficios.json sin avisar). En vez de eso, **inyectar los 86 Falabella frescos sobre la data fresca del auto-scraper** (763 → 849), preservando los demás bancos intactos.
- **Git vía clone local** (`/tmp/micartera-clone`) porque el `.git` en Google Drive CloudStorage tiene I/O inestable (timeouts mmap/index/FETCH_HEAD).

**Lo que se construyó:**
- `ScraperBancoFalabella` reescrita en `scrapers.py` (líneas 331-521): `scrapear()`, `_extraer_cards(html)` (brace-matcher estático), `_parsear_card()`, `_normalizar_dias()`. Una mejora defensiva: ventana de rfind del `{` ampliada de 6000 → 10000 chars (evitaba descartar cards silenciosamente).
- Resultado: **86 beneficios frescos** de restaurantes, normalizados al esquema existente (fechas DD-MMM-AAAA).

**Verificación (antes de pushear):**
- 849 cargan como `Beneficio()` sin error.
- `/beneficios/buscar?banco=Falabella` → 86.
- `/ver` renderiza Falabella.
- Revisión por subagente (sin críticos).

**Shipped a producción:**
- Commit `42bfbd2` en `origin/main`, tag `v1.1-falabella-ssr`. Render auto-redeployando.
- Como el fix vive en `scrapers.py` en origin, **el auto-scraper diario ahora se auto-cura**: las próximas corridas incluirán Falabella sin intervención.

**Lo que quedó BLOQUEADO (pendiente de decisión humana):**
- **Santander**: bloqueo Akamai (403) ante requests → necesita browser real.
- **BancoEstado**: sitio es SPA JS (shell ~2.5KB) + campaña estacional caída → necesita browser y/o nueva fuente.
- Ninguno regresiona nada (ya estaban en 0); se difiere a decisión de Fernando sobre cómo correr un browser en Render/CI.

---

### Sesión 5 — 2026-06-02 — Calidad 100% (v1.3 a v1.6)

**Contexto:** tras restaurar Falabella, una jornada de subir la calidad de datos a 100%.

**Lo que se hizo:**
- **Santander browserless** (v1.3): reescrito de Playwright a `requests` con UA `curl/8.4.0` (bypassa el WAF de Akamai). 0→77. (L-08)
- **BICE card basura** (v1.4): `dict.get` con default falsy dejaba pasar una card sin restaurante; fix con cadena `or` + descarte. (L-10)
- **Calidad 100%** (v1.5): health check blindado (crash-parity con los modelos reales, pisos por banco, guards de mojibake/ids), unicidad de ids (`_asegurar_ids_unicos`), Itaú+LiderBCI migrados a requests. (L-11, L-12, L-13)
- **Cards sin `descuento_texto`** (v1.6): híbrido — Security recupera el dato adyacente ("Menú Priceless"), Itaú/Falabella reciben etiqueta genérica vía `__post_init__`. (L-14)

**Resultado:** 929 beneficios, 14 bancos, health check verde. Lecciones L-08 a L-14.

---

### Sesión 6 — 2026-06-22 — Auto-monitoreo + resiliencia + aprendizaje

**Contexto:** Fernando reportó "faltan descuentos de Falabella". El diagnóstico abrió una sesión grande que transformó el sistema de "scraper + web" a "sistema auto-monitoreado y auto-resiliente con aprendizaje".

**Diagnóstico inicial:** Falabella cayó 97→0 el 06-20. NO era un bug: Banco Falabella activó geo-fencing (sirve su página vacía a IPs no chilenas); el cron corre en USA → veía 0 y el commit del bot borró el banco en silencio. (L-15)

**Lo que se construyó (en orden de commits):**
1. **Restauración + red de seguridad** (`bdc61bc`, `c4b66d9`): Falabella restaurado desde Chile; el orquestador ahora PRESERVA cualquier banco que caiga a 0 (reinyecta datos previos) en vez de borrarlo. (L-16)
2. **Chequeo experto por banco** (`0f72571`): `chequeo_bancos.py` clasifica cada banco + reintentos + email con estado por banco. (L-17)
3. **Refresco local desde Chile** (`7472793`): `refrescar_local.ps1` + Tarea Windows — scrapea los 15 desde IP chilena (sin geo-fence), resuelve Falabella solo. `diagnosticar.py` guarda el HTML de caídos.
4. **Fixes de validación** (`69b6cf1`): correr en Windows reveló bugs que Linux ocultaba — ids de Santander (global) + encoding de BICE (UTF-8). (L-18)
5. **Auditoría de credibilidad** (`3e94879`): los 14 bancos auditados. Santander/Consorcio sin % → etiqueta honesta; mapa con aviso de 222 ofertas sin local fijo. (L-19)
6. **Consorcio 50%** (`82b6951`): Fernando aportó que Consorcio SÍ tiene % (Casacostanera 50% devolución, tope $40.000); estaba en un type hermano de la API → capturado, trazable.
7. **Mail detallado + asunto claro** (`02cc9f1`): reporte por banco + "cómo funciona"; asunto "✅ TODO OK" / "⚠️ REVISAR".
8. **Aprendizaje** (`1d8622d`): `aprendizaje.py` + `historial.json` — nivel normal por banco, pisos adaptativos, alerta de tendencia. (L-20)
9. **Cron diario + estado PRESERVADO** (`0e933e3`): el cron pasó a diario y manda el mail con los secrets de GitHub (sin config local); PRESERVADO evita falsas alarmas por geo-fence.

**Resultado:** 954 beneficios, 14 bancos, mail diario funcionando (verificado por Fernando), sistema andando solo. Lecciones **L-15 a L-20**. Doc nueva: **`COMO_FUNCIONA.md`** (guía completa del sistema).

---

### Sesión 7 — 2026-06-23 — Fix JS de `/ver` + alineación del correo

**Contexto:** Fernando reportó "no se ven los beneficios de restaurantes" y luego pidió alinear el correo diario con sus otros reportes (que llegan ~09:00).

**Lo que se hizo:**
1. **Fix del JS de `/ver`** (`20d10ab`): el aviso del mapa (agregado en `0e933e3`) tenía un `onclick` inline cuyas comillas cerraban el string `innerHTML='...'` → rompía TODO el `<script>`; la página cargaba (HTTP 200) pero no renderizaba ningún beneficio. Fix: `id` + `.onclick` en JS puro, validado con `node --check`. (L-21)
2. **Correo alineado a 09:00 Chile** (`0 13 * * *`) + **refresco local movido a 08:30** (vía `Set-ScheduledTask`, sin password — tarea LogonType Interactive) para que no choquen los `git push` de dos procesos que regeneran la misma fuente de verdad. (L-22)
3. **Verificación contra el scheduler** (workflows `active` + tarea `Ready` + últimas corridas OK), no de palabra. (L-23)

**Resultado:** web renderizando OK, correo a las 09:00, flujo **08:30 refresco (Chile) → 09:00 cron (nube)**. Lecciones **L-21 a L-23** (+ L-W44 en el workspace).

---

### Sesión 8 — 2026-07-01 — Apartado de Cuotas sin interés

**Contexto:** Fernando pidió un apartado de **cuotas sin interés del mes por banco** (referencia: Chócale), pero **desde las fuentes oficiales de los bancos** (trazable), enfocado en todos los medios / automotriz / educación / etc.

**Decisiones:**
- **Curado + trazable, no scraper automático:** las campañas de cuotas cambian cada mes y muchas fuentes bloquean el fetch (WAF) o publican en imágenes → un scraper sería frágil y daría datos errados (peor que no tener). Se optó por **curado con link oficial por campaña + cruce con Chócale como control** de inconsistencias. (L-24)
- **Leer las oficiales desde Chile** con curl UA-curl: pasa el geo/WAF donde el fetch remoto (USA) da 403.

**Lo que se construyó:**
1. **`cuotas_sin_interes.json`**: 14 bancos (12 con campaña; Ripley/Mach sin), por categoría (todos los comercios, automotriz, educación, supermercados, salud, contribuciones), con condiciones de uso, vigencia, link oficial y nivel de confianza. Distingue **0% real vs tasa preferencial**.
2. **Apartado `/ver/cuotas`** (`a5558a0`): render server-side, botón 💳 en la barra de las 3 páginas. Selector de bancos por **logo** + selector de **mes** + chips de categoría (`528ab8c`).
3. **Correo diario** con sección de cuotas (`33b4aad`) + **aviso automático de desfase de mes** (`ee0abad`).
4. **Itaú en observación:** bajó de 71 a ~23 restaurantes (NO es bug — su Ruta Gourmet tiene solo 23 hoy); piso bajado 25→15 para no bloquear el health check (`0ebf168`).
5. **Refinamiento (tarde) — apartado 100% dinámico** (`8399ab8`→`8441276`): selector de mes real (junio→diciembre, junio como "historia" atenuado, abre en el mes en curso) donde cada campaña sale en los meses vigentes; los **logos de bancos** y los **contadores del hero** se filtran por mes. Barrido de fuentes oficiales con navegador desde Chile: **BCI corregido a jul-sep**, **Consorcio a hasta-dic** (dato oficial). Límite hallado: ~6 bancos publican en imágenes/SPA no legibles → se mantienen con el aviso de desfase; Fernando aporta datos puntuales trazables. Regla en memoria: barrer SIEMPRE los 14 bancos.

**Nota técnica:** la rutina en la nube para curar cuotas sola (`create_trigger`) no es viable en esta sesión local (404); la **detección** de desfase es automática (en el correo), la **curación** la hace Claude cuando el correo avisa o Fernando lo pide.

**Resultado:** 3 apartados web (restaurantes · bencina · cuotas). Scraper de beneficios intacto. Lección **L-24**.

---

### Sesión 9 — 2026-07-29 — Auditoría ácida de filtros/búsqueda + seguridad

**Contexto:** Fernando reportó **"Falabella + jueves no sale nada"** en el mapa. El bug puntual destapó un patrón sistémico ("el dato existe pero no se muestra") → se corrió una **auditoría ácida** completa de los filtros y la búsqueda. Todo verificado con `py_compile` + `node --check` + health check y desplegado a producción.

**Diagnóstico (causa raíz del bug reportado):**
- Las ofertas **sin local fijo** (aplican en toda la cadena, con `ubicacion` vacía) no generaban pin en el mapa → al filtrar "Falabella + jueves" el mapa quedaba vacío aunque las ofertas existían. Es el mismo patrón que L-06/L-19 pero en 3 filtros distintos: un filtro sobre un campo **opcional** que **excluye el vacío en silencio** en vez de dejarlo pasar.

**Decisiones tomadas:**
- **Un filtro/búsqueda de UI sobre un campo opcional debe dejar PASAR el vacío** ("aplica siempre"), no excluirlo. Es la decisión de fondo de la sesión → **lección L-28**. Aplicada a los 3 filtros (mapa, modalidad, zona) y al buscador.
- **Ofertas nacionales se muestran como TARJETAS bajo el mapa** en vez de descartarse (no se inventa un pin falso — coherente con L-19: dato faltante → mostrar honesto, nunca inventar).
- **Seguridad: cerrar los agujeros antes que agregar features.** Los endpoints `/scrape/*` eran POST anónimos **destructivos** (regeneraban/borraban data) → se eliminan, no se "protegen a medias".
- **Twilio y RAG-revectorización NO se tocan a ciegas:** el webhook necesita prueba en vivo del bot; la revectorización toca costo de API → requiere OK de Fernando (regla de costos del workspace). Se dejan como pendientes explícitos.

**Lo que se construyó (en orden de commits):**
1. **Mapa + 5 bugs de filtros** (`9b3fd67`): (#1) el mapa mostraba solo ofertas geolocalizables y **escondía 277 sin local fijo** → ahora salen como tarjetas bajo el mapa; (#2) el filtro **Modalidad** borraba **222 ofertas** con `presencial=online=False` (200 del Banco de Chile); (#3) el filtro **Zona** borraba las **277 nacionales** (ubicación vacía) al elegir región; (#4) normalización de días en `__post_init__` (preventivo); (#5) mutación de un array en el render.
2. **Buscador de `/ver` indexa comuna + tags** (`748571e`): buscar "providencia" pasó de **41 → 75** resultados, "ñuñoa" de **8 → 15**.
3. **Seguridad** (`c90eb07`): eliminados `/scrape/ejecutar` y `/scrape/bencinas` (POST anónimo destructivo que borraba 12 bancos); `/rag` con guard `ADMIN_TOKEN` + `max_length=1000` en la pregunta; **CORS restringido** (era `"*"` con `credentials=True`); tokens hardcodeados caducados limpiados; `buscar_beneficios` (API + bot) busca en nombre + descripción + comuna + tags.
4. **Falabella — nombres reales** (`d1781d7`): 95 nombres recuperados del **slug del `linkUrl`** (Petit, Vapiano, Muu Grill, Tanta, Mamma Mia...) en vez de "Dcto en Restaurante" — el nombre vivía en el slug del link, no en el campo `title`.
5. **Fine-tuning operativo `TUNING_PAGINAS.md`** (`9b0cf31`): todos los errores/cambios de las páginas registrados como lecciones operativas.

**Incidente operativo (registrado como aprendizaje):** el **refresco local corrió `git reset --hard origin/main`** en medio de la sesión y **borró 4 fixes sin commitear**. Regla reforzada: **commitear pronto**, no dejar trabajo sin commitear entre pasos cuando hay un proceso automático que puede resetear el working tree.

**Pendientes que quedaron abiertos:**
- **Webhook Twilio:** validación de firma (requiere prueba en vivo del bot).
- **RAG Pinecone:** revectorización (toca costo de API → requiere OK de Fernando).
- **Falabella:** filtrar las ofertas que no son restaurantes (`app-copec`, `pronto-copec`, `novedades-cmr-puntos`).

**Resultado:** filtros y búsqueda corregidos (277 ofertas nacionales ya no se esconden), superficie de ataque reducida (endpoints destructivos eliminados, CORS y `/rag` cerrados), Falabella con nombres reales. Lección nueva **L-28** + `TUNING_PAGINAS.md`.

---

### Sesión 10 — 2026-08-03 — Guardia de madrugada + apartado "Otros beneficios"

**Contexto:** tres frentes en una sola jornada — blindar la vigilancia con un check determinista, cerrar el caso Falabella (acotar al local + hacerlo trazable) y **abrir un apartado nuevo** para los beneficios no-restaurante que Santander/Consorcio traían y que hasta ahora se botaban. Todo verificado y en producción salvo la pantalla del apartado nuevo, que quedó en curso.

**Decisiones tomadas (con su porqué):**
- **Vigilancia con un script determinista, no con un agente cada madrugada.** La guardia de madrugada corre `revision_madrugada.py` en GitHub Actions (gratis, reproducible, auditable). Se descartó poner un LLM a revisar cada noche porque sería **caro y frágil**: un check determinista que reproduce cada bug conocido da una señal confiable ("esto reapareció / no reapareció"), mientras que un agente a ciegas puede alucinar un problema o pasar uno por alto. Es el patrón L-07 (cada bug → un guard permanente) elevado a un cron nocturno.
- **Falabella: acotar al local + trazabilidad, no prometer de más.** El nombre real vive en el slug del link (L-19), así que se **preserva el mall** en el nombre (Tanta [Mallplaza] ≠ otro Tanta). Y como el beneficio de Falabella aplica **por local** (no por toda la cadena), en vez de afirmar algo que no se puede garantizar se agrega una **restricción trazable consistente** en las 95 ofertas — *"Revisa los locales del beneficio. Comprueba en la página oficial."* Coherente con la regla de no inventar (L-19): cuando no se puede garantizar el alcance, se acota y se apunta a la fuente.
- **Apartado "Otros beneficios" en dataset SEPARADO, sin tocar el de restaurantes.** Santander/Consorcio traían beneficios no-restaurante (farmacias, transporte, ski, hoteles, retail) que se descartaban al filtrar solo gastronomía. La decisión clave fue **no meterlos en `beneficios.json`**: se capturan con un campo `seccion="otro"` en un archivo aparte (`beneficios_otros.json`). Razón — Fernando fue explícito: *"el apartado de restaurantes está perfecto, no lo toques"*. Un dataset separado (1) no arriesga regresionar el apartado estable de restaurantes, (2) no interfiere con los pisos por banco ni la red de seguridad (que están calibrados para restaurantes), y (3) permite **reusar los scrapers que ya traían el dato** en vez de duplicar lógica.
- **Respaldo antes de abrir el apartado nuevo.** Se dejó el tag **`v1.8-estable-pre-beneficios`** como punto de retorno: si el apartado nuevo desestabiliza algo, hay un estado conocido-bueno al que volver.

**Lo que se construyó (en orden de commits):**
1. **Guardia de madrugada** (`2696af9`): `revision_madrugada.py` + workflow con cron **03:00 Chile**. Convierte cada bug conocido en un check automático contra producción + la data; manda correo **solo si algo reaparece** (silencioso si todo está OK).
2. **Falabella — local específico + trazabilidad** (`dd62ddc`): mall preservado en el nombre + restricción trazable consistente en las **95 ofertas**.
3. **Tarjetas con condiciones + link oficial** (`b4d0925`): cada tarjeta muestra sus **condiciones (📋)** + link **"Comprobar en la página"**.
4. **Apartado "Otros beneficios"** (`7ebf2cf` + pantalla en curso): dataset separado `beneficios_otros.json` con **228 beneficios** no-restaurante de Santander/Consorcio, campo `seccion="otro"`, sin tocar `beneficios.json` ni `/ver`.
5. **Respaldo:** tag `v1.8-estable-pre-beneficios` (punto de retorno).

**Lo que quedó pendiente:**
- **Otros 12 bancos para el apartado:** hoy el dataset tiene solo Santander/Consorcio; falta scrapear las páginas de beneficios generales de los otros 12 bancos (mismo enfoque: dataset separado, `seccion="otro"`).
- **Pantalla web del apartado:** la vista que muestra `beneficios_otros.json` quedó en curso.
- **Webhook Twilio** (validación de firma, requiere prueba en vivo) y **RAG revectorización** (toca costo de API → requiere OK de Fernando) siguen abiertos desde la sesión 9.

**Resultado:** vigilancia nocturna determinista (03:00 → 08:30 refresco → 09:00 cron), Falabella acotado al local y trazable, y un apartado nuevo de beneficios no-restaurante con 228 items en dataset separado — todo sin tocar el apartado de restaurantes que ya estaba estable. Punto de retorno en `v1.8-estable-pre-beneficios`.

---

### Sesión 11 — 2026-08-03 — Apartado "Otros beneficios" + trazabilidad total + filtros dinámicos (v2.0)

**Contexto:** cierre del arco que arrancó el 29-jul (sesión 9, auditoría de filtros/seguridad) y siguió el 3-ago (sesión 10, guardia de madrugada + apertura del apartado "Otros beneficios" con 228 candidatos sin filtrar). Esta sesión resuelve lo que había quedado abierto: reducir el apartado nuevo a solo lo verificable, auditar la trazabilidad de TODOS los datasets de cara al usuario (no solo el nuevo) y llevar los filtros de día de una grilla fija a algo dinámico según lo que cada banco realmente tiene.

**Decisiones tomadas (con su porqué):**
- **"Si no está chequeado, mejor no mostrar."** De los 228 candidatos de "Otros beneficios", solo **24** tienen un % de descuento real y verificable; los otros ~204 eran financiamiento/servicios (tasas, CAE, cuotas) que no son un descuento — mostrarlos como "beneficio" habría sido engañoso. Se descartaron en vez de forzarlos con una etiqueta genérica: extiende L-19/L-33 (dato no verificable → no se muestra, no se inventa ni se disfraza).
- **Auditar trazabilidad MIDIENDO el dominio de la fuente, no asumiendo.** Se midió `url_fuente` en los 4 datasets de cara al usuario: restaurantes (887), otros (24) y cuotas (28) resultaron 100% de fuente oficial; **bencina-descuentos (31) resultó 100% de un agregador** (`descuentosrata.com`) — nadie lo había verificado antes de esta auditoría. Ese hallazgo es el que gatilló re-curar bencina desde cero (L-33).
- **El agregador es control de calidad, no fuente — re-curar bencina desde lo oficial.** Se re-curaron los 31 descuentos: Copec (15) leído directo de `ww2.copec.cl`, Aramco/Shell (16) desde medios verificados. Se agregó el campo `confianza` + `url_fuente` por dato para que cada descuento cargue su propia procedencia. Al re-curar aparecieron **5 errores que el agregador tenía y nadie había cuestionado**: Shell/Scotiabank era **jueves** (el agregador decía sábado), Itaú Copec era **martes** (decía viernes), BancoEstado era **martes $50** (decía viernes $100), BCI era **7% cashback con tope $7.000** (decía $100/L fijo), Santander Consumer era **viernes-domingo** (decía lunes-viernes) (L-35).
- **La guardia de madrugada se amplía a trazabilidad, no solo a bugs de datos.** El check de las 03:00 (`revision_madrugada.py`) ahora también vigila que ningún dato pierda su `confianza` o vuelva a depender solo del agregador sin que nadie lo note — mismo rol de "agente que revisa siempre" que ya tenía para los bugs de página, extendido al nuevo campo.
- **Filtros de día DINÁMICOS, no una grilla fija de 7 días.** En `/ver` y `/ver/beneficios`, los días sin resultados para el banco/filtro elegido se atenúan o bloquean en vez de dejar al usuario clickeando un día vacío; cuando una sección entera no tiene data aún, se muestra **"Estamos confirmando los descuentos"** en vez de una pantalla vacía sin explicación — mismo principio de honestidad de L-19, aplicado ahora a la ausencia de datos y no solo al dato mismo.
- **El apartado de restaurantes `/ver` sigue intacto.** Ninguno de estos cambios tocó `beneficios.json`, sus pisos ni la red de seguridad — la decisión viene desde la sesión 10 ("lo que ya tenemos está perfecto") y se sostuvo durante todo el arco.

**Lo que se construyó (foco en lo nuevo de esta sesión, sobre la base de las sesiones 9 y 10):**
1. **Apartado "Otros beneficios" filtrado 228 → 24 verificables:** solo quedan los beneficios con % de descuento real comprobable; el resto (financiamiento/servicios/CAE) se descarta en vez de mostrarse con etiqueta genérica.
2. **Bug del % del CAE corregido (L-34):** "Bip Solar" de Santander mostraba **54% de descuento** cuando ese número era el **CAE del financiamiento (1,54%)** — el regex que extraía el % no distinguía descuento de tasa. Corregido excluyendo el contexto financiero antes de buscar el %.
3. **Auditoría de trazabilidad de los 4 datasets** (L-33): restaurantes/otros/cuotas 100% oficial; bencina 100% agregador → dispara el punto 4.
4. **Bencina re-curada desde fuente oficial** (L-35): Copec (15, `ww2.copec.cl`) + Aramco/Shell (16, medios verificados), campo `confianza` + `url_fuente` por dato, 5 errores corregidos (detalle arriba), fuente marcada en la web.
5. **Guardia de madrugada ampliada a trazabilidad:** alerta si algún dato pierde `confianza` o vuelve a depender solo del agregador.
6. **Filtros dinámicos de día** en `/ver` y `/ver/beneficios` + mensaje "Estamos confirmando descuentos" cuando falta data de una sección.

**Verificado en producción:** las 4 vistas (`/ver`, `/ver/bencinas`, `/ver/cuotas`, `/ver/beneficios`) responden HTTP 200; JS validado con `node --check`; filtros dinámicos y el apartado "Otros beneficios" (24 verificables) operando en vivo.

**Lecciones nuevas:** L-28 a L-35 — contador del proyecto llega a **35 lecciones formalizadas**. Tags de este arco: **`v1.9-otros-beneficios`** (apertura del apartado, sesión 10) y **`v2.0-otros-trazabilidad-filtros`** (cierre de esta sesión: 24 verificables + trazabilidad total + filtros dinámicos).

**Lo que quedó pendiente:**
- Re-curar Shell/Aramco desde sus apps oficiales (hoy la fuente es "medios verificados", no la fuente primaria del banco).
- Extender los filtros dinámicos a región/comuna, y llevarlos también a `/ver/bencinas` y `/ver/cuotas` (hoy solo día, y solo en `/ver` y `/ver/beneficios`).
- Los otros 12 bancos del apartado "Otros beneficios" (hoy solo Santander + Consorcio).
- Webhook Twilio (validación de firma, requiere prueba en vivo) y RAG Pinecone (revectorización, requiere OK de costo) — abiertos desde la sesión 9.

**Resultado:** el apartado "Otros beneficios" pasó de 228 candidatos sin filtrar a 24 confiables; los 4 datasets de cara al usuario quedaron con su procedencia medida y marcada (3 ya eran oficiales, bencina se re-curó y corrigió 5 errores heredados del agregador); la guardia de madrugada vigila trazabilidad además de bugs de página; y los filtros de día dejan de mostrar casillas vacías sin explicación. Cierra el arco 29-jul→3-ago con el sistema en `v2.0-otros-trazabilidad-filtros`.

---

## 🏗️ Hitos mayores del proyecto

### M01 — Build inicial completo (~2026-03)

**Qué cambió:** De cero a sistema funcional en producción.
**Por qué fue un hito:** Validó la viabilidad de scrapear 15 bancos chilenos y consolidar datos heterogéneos.
**Impacto:** 985 beneficios indexados, bot WhatsApp activo.

### M02 — Documentación V01 (2026-03-15)

**Qué cambió:** Sistema sin docs → docs completa (técnica + natural).
**Por qué fue un hito:** Facilita handoff y mantenimiento futuro.

### M03 — Migración al workspace (2026-05-26)

**Qué cambió:** Proyecto legacy → aligned con sistema workspace canónico.
**Por qué fue un hito:** Habilita que el próximo Claude que abra el proyecto herede contexto del workspace vía @imports.

### M04 — Fix Falabella SSR + auto-cura del auto-scraper (2026-06-01)

**Qué cambió:** Falabella pasó de 0 → 86 beneficios en producción reescribiendo su scraper de Playwright a requests/SSR.
**Por qué fue un hito:** Resolvió la incompatibilidad estructural "scraper con browser vs entorno Render/CI sin Chromium". El fix vive en `scrapers.py` en origin, así que el auto-scraper diario ahora incluye Falabella sin intervención manual.
**Impacto:** Producción 763 → 849 beneficios. Reveló que 2 bancos más (Santander, BancoEstado) siguen bloqueados por la misma causa raíz (necesitan browser).

---

## 🔀 Decisiones arquitectónicas clave

Para detalle con formato ADR, ver [`docs/03_decisiones.md`](./docs/03_decisiones.md).

Resumen:

1. **Pinecone en vez de pgvector** — heredado, hoy deuda técnica
2. **Monolito en `api.py`** — deploy simple a 1 servicio Render
3. **15 scrapers independientes** — robustez (un banco caído no rompe los otros)
4. **Archivos planos JSON/CSV** en vez de DB — volumen chico, simpleza
5. **Coordenadas aproximadas por región** en mapa — pragmatismo sobre precisión

---

## 🚧 Cosas que se intentaron y no funcionaron

- **Playwright en Falabella (RESPUESTA, 2026-06-01):** Sí se usó Playwright (+ Contentful) para Falabella, con `playwright install chromium` en runtime. **Funcionaba local pero fallaba en Render/CI** (no hay Chromium en ese entorno), devolviendo 0 silenciosamente. Reemplazado por requests/SSR en la Sesión 4. Lección: cualquier scraper que dependa de un browser está condenado a 0 en el auto-scraper diario de Render — preferir requests/SSR siempre que el sitio exponga datos en el HTML (RSC, JSON-LD, `__NEXT_DATA__`, etc.).
- **Santander con requests (2026-06-01):** bloqueo Akamai (HTTP 403) ante requests sin browser. No resuelto — necesita browser real o endpoint alternativo. BLOQUEADO.
- **BancoEstado con requests (2026-06-01):** el sitio es una SPA JS (shell ~2.5KB sin datos) y además la campaña estacional de beneficios estaba caída. No resuelto. BLOQUEADO.

---

**Última actualización:** 2026-08-03

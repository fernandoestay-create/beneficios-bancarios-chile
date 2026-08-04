# Lecciones Aprendidas — MiCartera Scrapers + Bot

> **Documento vivo.** Se actualiza al cerrar cada sesión productiva.
> Lecciones específicas de ESTE proyecto, formato L-XX.
> Si una lección aplica a 2+ proyectos del workspace, promoverla a `Claude_code/LECCIONES.md` con prefijo L-W.
> Si aplica globalmente, promoverla a `~/.claude/CLAUDE.md` con prefijo L-G.

---

## 📋 Índice de lecciones

| ID | Título | Categoría | Fecha |
|----|--------|-----------|-------|
| L-01 | Scrapers con browser (Playwright) devuelven 0 en Render/CI | Scraping / Deploy | 2026-06-01 |
| L-02 | Datos en RSC de Next.js se sacan con requests + brace-matching | Scraping | 2026-06-01 |
| L-03 | `.git` en Google Drive CloudStorage es inestable para red → usar clone local | Deploy / Git | 2026-06-01 |
| L-04 | Inyectar el banco arreglado sobre la data fresca del auto-scraper, no sobre base stale | Datos y calidad | 2026-06-01 |
| L-05 | Wikimedia/Google bloquean hotlink (400/403) → self-hostear logos; bajar vía Special:FilePath | Frontend / Assets | 2026-06-01 |
| L-06 | "No aparece" puede ser gap de datos, no bug de filtro — verificar la data antes de tocar lógica | Debugging / Datos | 2026-06-01 |
| L-07 | Health check estático pre-deploy como guard de regresión (logos + integridad JSON) | QA / Deploy | 2026-06-01 |
| L-08 | Akamai da 403 a UA de browser/python pero 200 a UA estilo `curl` → usar UA curl en requests | Scraping / Anti-bot | 2026-06-02 |
| L-09 | "Bloqueado" puede ser campaña estacional caída, no anti-bot — distinguir antes de pagar un browser service | Scraping / Debugging | 2026-06-02 |
| L-10 | `dict.get(k, default)` no aplica el default si el valor existe pero es falsy (`''`) → usar cadena `or` + descartar | Debugging / Datos | 2026-06-02 |
| L-11 | Los `id` deben ser únicos (rompen `/beneficios/{id}` + upsert Pinecone) → disambiguar colisiones (`_2/_3`), no borrar | Datos y calidad | 2026-06-02 |
| L-12 | Cleanup de datos durable: round-trip por el dataclass real (lossless) + regenerar CSV con `csv.DictWriter` (CRLF-safe), no editar a mano | Datos y calidad | 2026-06-02 |
| L-13 | Una migración scraper Playwright→requests hay que verificarla EN VIVO (el health check prueba data-at-rest, no que el fetch reescrito traiga datos) | Scraping / QA | 2026-06-02 |
| L-14 | Cards sin campo de display: recuperar el dato real adyacente donde existe + red de seguridad genérica en `__post_init__` (chokepoint único que corre en cron + cleanup) | Datos y calidad | 2026-06-02 |
| L-15 | Un banco que funcionaba en el cron cae a 0 por geo-fence del runner (IP datacenter), no por el código → confirmar con fetch desde IP del país objetivo vs externa | Scraping / Debugging | 2026-06-22 |
| L-16 | Red de seguridad anti proceso-estéril POR BANCO: el orquestador preserva el banco caído a 0 + alerta por email, en vez de que el cron lo borre en silencio | Datos y calidad / Deploy | 2026-06-22 |
| L-17 | Chequeo experto por banco: clasificar (OK/DEGRADADO/CAÍDO con piso absoluto Y relativo) + reintentar transitorios + preservar caídos + email con estado por banco | QA / Deploy | 2026-06-22 |
| L-18 | Correr el mismo scraper en otro entorno (Windows vs Linux/cron) revela bugs ocultos: encoding-dependiente (mojibake BICE) + ids latentes (Santander); fijar UTF-8 e invariantes globales | Scraping / QA | 2026-06-22 |
| L-19 | Auditar la CALIDAD DE OFERTA por banco (lo que ve el usuario: % real, geolocalizable, texto claro), no solo integridad; y dato faltante en la fuente → etiqueta honesta, NUNCA inventar | Datos y calidad / UX | 2026-06-22 |
| L-20 | "Aprendizaje" honesto para un cron de N fuentes = estadística sobre el propio histórico (pisos adaptativos + tendencias), no un modelo neuronal; ser explícito con el usuario para no vender humo | Datos y calidad / Meta | 2026-06-22 |
| L-21 | JS embebido en f-string: una comilla mal escapada (`\'` → `'` cerrando un `innerHTML='...'`) tumba TODO el `<script>` y la página no renderiza nada; el health check de datos no lo ve → validar con `node --check` | Frontend / QA | 2026-06-22 |
| L-22 | Dos procesos que REGENERAN y pushean la misma fuente de verdad (cron nube + refresco local a la misma hora) → ordenarlos en el tiempo, no mergear (el rebase choca en el archivo regenerado) | Deploy / Datos | 2026-06-23 |
| L-23 | "¿Está operando?" se verifica contra el SCHEDULER (workflow `active` + última corrida OK; Tarea Windows `Enabled`+`LastTaskResult 0`), no se afirma; + cambiar hora de Tarea Windows Interactive sin password (`Set-ScheduledTask`) | QA / Deploy | 2026-06-23 |
| L-24 | Dataset nuevo de fuentes oficiales que cambian mensual y bloquean fetch remoto (403/WAF) → curado + trazable (link oficial por dato) + cruce con agregador como control, leyendo las oficiales con `curl` desde el país objetivo; no scraper automático frágil | Datos y calidad / Scraping | 2026-07-01 |
| L-25 | Un cambio de nivel abrupto y SOSTENIDO (banco que renueva campaña con menos ofertas) queda DEGRADADO en falso si la ventana del "nivel normal" es larga (12 corridas) → bajarla a ~1 semana (7); el piso fijo sigue de red mínima | Datos y calidad / Meta | 2026-07-06 |
| L-26 | El sistema debe AUTO-GESTIONARSE, no solo avisar "falta algo" en el correo: auto-corregir lo auto-corregible (transitorios/geo-fence/resiliencia/recalibración) + auto-diagnosticar lo que no; NO auto-reparar el código del scraper (peligroso) | Meta / Infraestructura | 2026-07-06 |
| L-27 | Cerrar el loop de auto-gestión: la revisión humana confirma un nivel real y el sistema deja de alarmar por él, pero re-alarma si empeora (feedback humano explícito, no solo histórico automático) | Meta / Datos y calidad | 2026-07-10 |
| L-28 | Un filtro/búsqueda de UI sobre un campo OPCIONAL (ubicación, comuna, modalidad) debe dejar PASAR el vacío ("aplica siempre"), no excluirlo en silencio → esconde ofertas reales que el usuario sí ve en la fuente; primo de L-10 en la capa de cara al usuario | Datos y calidad / UX | 2026-07-29 |
| L-29 | Campo genérico de una card ("Dcto en Restaurante") → el dato real vive en un campo HERMANO (el slug del `linkUrl` de Falabella): des-slugificar y recuperar, NUNCA inventar (L-19 aplicado) | Scraping / Datos | 2026-07-29 |
| L-30 | El refresco local hace `git reset --hard origin/main` y BORRA lo no commiteado → commitear+pushear PRONTO cada bloque verificado, no dejar trabajo sin commitear entre pasos | Deploy / Git | 2026-07-29 |
| L-31 | Apartado nuevo que reusa una vista existente → dataset SEPARADO (campo `seccion`), no tocar el pipeline que funciona (pisos, red de seguridad, health check) | Arquitectura / UX | 2026-08-03 |
| L-32 | Scrapers que ya traen datos y los BOTAN con `return None` → capturarlos con un flag (`seccion`), no duplicar el scraping | Scraping / Datos | 2026-08-03 |
| L-33 | Auditar TRAZABILIDAD midiendo el DOMINIO de la fuente por dataset (oficial vs agregador vs sin url): revela qué data no es confiable; marcar la procedencia; "si no es trazable/chequeado, mejor no mostrar" | Datos y calidad / Meta | 2026-08-03 |
| L-34 | Un regex laxo `(\d+)\s*%` sobre descripción cruda captura el CAE del financiamiento como descuento (Bip Solar 54% = CAE 1,54%) → excluir la frase del CAE + solo % de 1-2 dígitos no decimal | Scraping / Datos | 2026-08-03 |
| L-35 | Curar desde la fuente OFICIAL + campo `confianza` por dato + guardia que verifica trazabilidad SIEMPRE; si no hay dato chequeado, mostrar "estamos confirmando" en vez de un dato dudoso (agregador ≠ fuente, L-24) | Datos y calidad / Meta | 2026-08-03 |
| L-36 | Filtros DINÁMICOS/faceteados: al elegir un eje (banco), recalcular los otros ejes (día, comuna, %) y ATENUAR/bloquear las opciones sin resultados, en vez de dejarlas seleccionables y devolver vacío; un guard vigila que siga así; sin data → "estamos confirmando" | UX / Frontend | 2026-08-03 |
| L-37 | Curación manual protegida SOLO por un guard, PERO el generador (scraper) sigue produciendo la data mala desde el agregador → el output del scraper falla el guard y BLOQUEA todo el pipeline (deadlock) → la curación debe PRESERVARSE en el generador (el `guardar` conserva el dato curado), no solo defenderse con un guard | Datos y calidad / Deploy | 2026-08-04 |
| L-38 | Al configurar/activar algo en un webhook (firma, seguridad), VERIFICAR en la consola del proveedor a qué URL/servicio apunta REALMENTE — no asumir. El Sandbox de Twilio apuntaba a OTRO servicio y OTRA ruta (`micartera-ttaa/api/webhooks/whatsapp`), no al que yo modificaba → el bot "no respondía" y la firma quedó en el servicio equivocado; se confirma con los logs del destino (¿llega el POST? ¿200/403?) | Integraciones / Deploy | 2026-08-04 |
| L-39 | Un bot de lógica ÚNICA sirve varios canales con un adaptador delgado (Twilio/WhatsApp + Telegram): solo cambian el TRANSPORTE (recibir update + enviar respuesta) y el FORMATO por canal (WhatsApp renderiza `*_`; Telegram en texto plano los muestra LITERALES → strippear). Prefijar el usuario por canal (`tg_<id>`) para no mezclar el estado del flujo. Cada canal = endpoint opt-in por su token | Integraciones / Bot | 2026-08-04 |
| L-40 | Un audit de datos con agente INDEPENDIENTE pilla lo que el filtro de código no: un financiamiento (CAE) colado como "% dcto." en la data CURADA (Proyecta Energía 90%), pese a que el fix del scraper (L-34) existía; y campos semánticamente mal (nombre=descripción). Auditar la DATA curada, no solo el código; el que construye NO revisa | Datos y calidad / Meta | 2026-08-04 |

---

## 📚 Categorías sugeridas

Usar las que apliquen a este proyecto:

- Scraping (sitios bancarios chilenos)
- APIs / FastAPI / Flask
- Vector DB (Pinecone legacy)
- Integraciones (Twilio / WhatsApp / OpenAI / Pinecone)
- Deploy (Render)
- Datos y calidad
- Comunicación con el usuario (bot conversacional)
- Meta: trabajo con IA

---

## Lecciones

### L-01 · Scrapers con browser (Playwright) devuelven 0 en Render/CI (2026-06-01) · Scraping / Deploy

**Problema**
Banco Falabella no aparecía en producción (`/ver`), 0 beneficios, todos los días, aunque el resto de bancos sí se actualizaba.

**Causa raíz**
El scraper de Falabella usaba Playwright e intentaba `playwright install chromium` en runtime. En producción corre un **auto-scraper diario** sobre Render/CI, que **no tiene Chromium**. El scraper fallaba silenciosamente y devolvía `[]` → 0 Falabella, día tras día. Local funcionaba (porque local sí tiene browser), lo que enmascaraba el problema.

**Fix**
Reescribir el scraper sin browser, usando `requests` sobre el HTML SSR (ver L-02). Resultado: corre idéntico en local y en Render.

**Lección**
Cualquier scraper que dependa de un navegador está **condenado a 0 en el auto-scraper de Render/CI**. "Funciona en mi máquina" es exactamente el síntoma engañoso. El entorno de producción (donde corre el cron) es el que manda.

**Evitar a futuro**
Antes de escribir un scraper con Playwright/Selenium, preguntar: ¿esto va a correr en el cron de Render? Si sí → buscar primero datos en el HTML plano (RSC, `__NEXT_DATA__`, JSON-LD, API interna). Solo usar browser si NO hay alternativa, y entonces resolver el tema de Chromium en el build de Render explícitamente (no en runtime).

---

### L-02 · Datos en RSC de Next.js se sacan con requests + brace-matching (2026-06-01) · Scraping

**Problema**
Sitios migrados a Next.js (como Falabella) ya no traen los datos en HTML clásico; vienen como payload RSC (React Server Components) escapado dentro del HTML.

**Causa raíz**
Next.js App Router embebe los datos serializados en el HTML inicial (SSR), no en un `<script type="application/json">` limpio sino como string RSC escapado. No es JSON parseable directo, pero los objetos sí están ahí.

**Fix**
Patrón requests/SSR sin browser: (1) `requests.get(url)`; (2) anclar en un marcador estable del payload (acá `"discountDays":[`); (3) `rfind('{', ...)` hacia atrás para encontrar el `{` que abre el objeto contenedor (ventana amplia, 10000 chars — una ventana corta descarta cards silenciosamente); (4) balancear llaves hacia adelante respetando strings; (5) `json.loads`; (6) dedup por una key estable (`linkUrl`).

**Lección**
La mayoría de los sitios "modernos JS" igual exponen sus datos en el HTML inicial por SSR/SEO. No hace falta browser: hace falta encontrar el ancla y parsear con cuidado de strings/llaves.

**Evitar a futuro**
Ante un sitio Next.js/React, primero `curl` el HTML y buscar `__NEXT_DATA__`, `self.__next_f`, o marcadores del dominio (nombres de campos esperados). Casi siempre los datos están ahí.

---

### L-03 · `.git` en Google Drive CloudStorage es inestable para red → usar clone local (2026-06-01) · Deploy / Git

**Problema**
`git push`/`fetch` desde el repo en la carpeta de Drive fallaban con timeouts (mmap/index/FETCH_HEAD), y un commit local quedó huérfano.

**Causa raíz**
El `.git` vive en Google Drive CloudStorage (FUSE/streaming), que tiene I/O poco confiable para los muchos archivos pequeños y locks que git necesita en operaciones de red.

**Fix**
Clonar el repo a disco local (`/tmp/micartera-clone`), hacer ahí todas las operaciones de red (commit/push/tag), y dejar la carpeta de Drive solo para editar archivos.

**Lección**
Operaciones git de red sobre Drive CloudStorage son frágiles. El working tree en Drive está bien para editar; el `.git` para push/fetch no.

**Evitar a futuro**
Para cualquier push/pull/fetch de este proyecto (u otro en Drive), usar un clone en disco local como intermediario. No pelear con el `.git` de Drive.

---

### L-04 · Inyectar el banco arreglado sobre la data fresca del auto-scraper, no sobre base stale (2026-06-01) · Datos y calidad

**Problema**
Mi `beneficios.json` base (en Drive) estaba ~1 semana atrasado respecto a producción. Si pusheaba mi archivo completo, **regresionaba** los otros 12 bancos a su estado viejo.

**Causa raíz**
Producción tiene un auto-scraper diario que actualiza `beneficios.json` en origin constantemente. Cualquier base local se vuelve stale en horas/días.

**Fix**
En vez de pushear mi archivo, tomé el `beneficios.json` **fresco de origin** (763 ítems, con la data al día de los otros bancos), le quité los Falabella viejos (0) e inyecté mis 86 Falabella frescos → 849. Verifiqué que las keys calzaran con el esquema. Así solo cambió Falabella; los demás bancos quedaron con su data fresca.

**Lección**
Cuando un sistema tiene un proceso automático que toca el mismo archivo, **nunca pushear tu copia completa**: hacer merge quirúrgico de tu cambio sobre la versión fresca de origin. Respeta la regla "no regenerar beneficios.json sin avisar" y evita regresiones invisibles.

**Evitar a futuro**
Antes de pushear data que un cron también modifica: `git fetch`, tomar la versión de origin como base, aplicar solo tu delta encima, verificar conteos por banco antes y después.

---

### L-05 · Wikimedia/Google bloquean hotlink → self-hostear logos (2026-06-01) · Frontend / Assets

**Problema**
Los logos de bancos dejaron de aparecer en `/ver` y `/ver/bencinas`. Los `BANK_LOGOS` apuntaban a `upload.wikimedia.org/.../200px-....png` y a URLs de `googleusercontent`/`play-lh`.

**Causa raíz**
Wikimedia bloquea el hotlinking de thumbnails: las URLs `upload.wikimedia.org` devuelven **HTTP 400** aunque mandes un User-Agent válido. Las de Google (`play-lh`, `googleusercontent`) eran además placeholders falsos (400). El `<img onerror>` caía al texto, por eso "no salían las imágenes".

**Fix**
Self-hostear todo: bajar los originales con `https://commons.wikimedia.org/wiki/Special:FilePath/<archivo>` (devuelve 200, sirve el original), guardarlos en `static/logos/` y repuntar ambos `BANK_LOGOS` a `/static/logos/*`. Para los que ya no están en Wikimedia (Banco Internacional) o no son marca pública (SBPay, SPIN), generar un badge SVG con el color de marca (`BANK_COLORS`). Resultado: 0 dependencias externas en runtime.

**Lección**
Nunca depender de hotlink a Wikimedia/Google para assets de producción: bloquean el thumbnail aunque el archivo exista. `upload.wikimedia.org` ≠ `Special:FilePath` — el segundo sí sirve el original. Self-hostear es la única opción robusta.

**Evitar a futuro**
Cualquier `<img src>` externo en producción es deuda. Bajar el asset al repo (`Special:FilePath` para Wikimedia) y servir local. El health check (L-07) ahora falla si reaparece una URL externa de logo.

---

### L-06 · "No aparece X" puede ser gap de datos, no bug de filtro (2026-06-01) · Debugging / Datos

**Problema**
El descuento Scotiabank Shell de los sábados "no salía" en `/ver/bencinas`. El primer instinto fue sospechar del filtro por día (normalización de tildes, `getDay()`, etc.).

**Causa raíz**
El filtro estaba **correcto** en los 3 lugares (JS `DIAS_SEMANA[getDay()]`, Python `weekday()`, normalización sin tilde). El descuento simplemente **no existía en la data curada** (`bencinas.json` / `_cargar_datos_estaticos`). Era un gap de datos, no un bug de lógica.

**Fix**
Verificar primero la data (¿el ítem existe con `dias_validos=['sabado']`?) antes de tocar el filtro. Una vez confirmado el gap, agregar el dato en el source (scrapers.py) + inyectar en el JSON, y simular el filtro para el sábado para probar que ahora sí aparece.

**Lección**
Ante "no aparece", la pregunta 1 es "¿el dato existe?", no "¿el filtro falla?". Confirmar la presencia del dato antes de asumir bug de lógica ahorra horas de debugging del filtro equivocado (alineado con systematic-debugging: root cause antes de fix).

**Evitar a futuro**
Para cualquier "no sale Y": grep/print la data cruda filtrando por la condición exacta. Si el ítem no está → gap de datos. Si está pero no se muestra → recién ahí mirar el filtro/render.

---

### L-07 · Health check estático pre-deploy como guard de regresión (2026-06-01) · QA / Deploy

**Problema**
No había forma automática de saber, antes de pushear, si un cambio rompía los logos (URL externa colada) o la integridad de la data (campos faltantes, días sin normalizar, un descuento clave desaparecido).

**Causa raíz**
La verificación era manual y se olvidaba. El auto-scraper diario puede regenerar los JSON y reintroducir problemas sin que nadie lo note.

**Fix**
`verificar_salud.py` (en la raíz del repo): script estático (no levanta servidor) que valida (1) todo logo referenciado en api.py existe local y 0 URLs externas; (2) integridad de beneficios.json; (3) integridad de bencinas.json + guard de regresión del Scotiabank sábado. Exit 0/1 → wireable a CI/pre-push. Corre en segundos.

**Lección**
Un health check estático y barato (parsear archivos, no levantar infra) es el mejor guard contra regresiones silenciosas, sobre todo cuando un cron toca los mismos archivos. Incluir guards específicos de cada fix (no solo genéricos) convierte cada bug resuelto en un test permanente.

**Evitar a futuro**
Cada vez que se arregle algo que "se puede volver a romper" (logo, dato clave, formato), agregar una aserción al health check. Correr `python3 verificar_salud.py` antes de cada push.

---

### L-08 · Akamai da 403 a UA de browser pero 200 a UA estilo `curl` (2026-06-02) · Scraping / Anti-bot

**Problema**
Santander devolvía 0 beneficios. El scraper usaba Playwright (browser) supuestamente "para bypass 403", pero eso lo condenaba a 0 en el cron de Render (L-01) y aun así el WAF lo trataba como sospechoso.

**Causa raíz**
El WAF de Akamai de `banco.santander.cl` bloquea (403) requests cuyo `User-Agent` parece **browser a medias** o `python-requests`, pero deja pasar (200) un `User-Agent` estilo `curl/8.4.0`. Contraintuitivo: un UA "más simple/no-browser" pasa, uno "tipo Chrome" se bloquea. Además el sitio sirve el HTML SSR completo (`li.item`), así que no se necesita browser para nada.

**Fix**
`requests.Session()` con `headers={'User-Agent': 'curl/8.4.0'}`, paginar `?page=1..N` parseando `soup.select('li.item')` con BeautifulSoup, cortar cuando una página devuelve 0 items. El parser de items (`_parsear_item`) se reutilizó tal cual del scraper Playwright — solo cambió el mecanismo de fetch. Resultado: 0 → 77 restaurantes, corre igual en local y en Render.

**Lección**
Ante un 403, antes de saltar a un browser, probar variantes de `User-Agent` — especialmente `curl/X` o UAs no-browser. Muchos WAF tunean el fingerprint de browser y un UA "honesto y simple" pasa donde uno "tipo Chrome a medias" se bloquea. Verificar con un test mínimo de `requests` (status + len + ¿el selector calza en el HTML crudo?) antes de escribir el scraper completo.

**Evitar a futuro**
Matriz de prueba rápida ante 403: `python-requests` (default) → UA vacío → `curl/8.4.0` → UA Chrome completo. Si alguno da 200 con el contenido real (no una challenge page de 1-2KB), usar ese y NO meter browser. Confirmar que el cuerpo trae los datos esperados, no un shell/challenge.

---

### L-09 · "Bloqueado" puede ser campaña estacional caída, no anti-bot (2026-06-02) · Scraping / Debugging

**Problema**
BancoEstado devolvía 0. La hipótesis heredada era "SPA/Akamai necesita browser". Se evaluó pagar un servicio externo de browser (Apify/ScrapingBee) para resolverlo.

**Causa raíz**
La URL de campaña (`.../un-mes-de-sabores---bancoestado-personas.html`) devuelve un **soft-404 de Akamai Edge** (página "Página no encontrada", ~1-2KB, código de referencia tipo `0.461dd517...`) a **todo** cliente — incluso con `User-Agent` de browser y en todos los endpoints AEM (`.model.json`, `.infinity.json`, `/jcr:content.json`, `.1.json`). Que un UA de **browser real** también reciba el 404 es la señal clave: no es solo anti-bot, la **campaña estacional ya no existe** en esa ruta.

**Fix**
Ninguno aplicable ahora: diferir (opción D) hasta que BancoEstado relance una campaña de gastronomía con URL viva. Recién ahí, si bloquea por anti-bot (no por 404), evaluar un browser service.

**Lección**
Antes de concluir "necesita browser" y peor aún pagar por uno, distinguir **anti-bot** de **contenido inexistente**. Test discriminante: pegarle a la URL con un `User-Agent` de browser real. Si igual da 404/soft-404 → el recurso no existe (campaña caída/cambió de ruta), y ningún browser service lo va a resolver. Si da 200 solo con browser y 403 sin él → ahí sí es anti-bot y un browser service tiene sentido.

**Evitar a futuro**
Diagnóstico de "banco en 0": (1) ¿la URL responde contenido real con UA de browser? Si no → buscar la URL/campaña actual antes que cualquier otra cosa. (2) Solo si el contenido existe pero se bloquea programáticamente → técnicas anti-bot (UA curl L-08, o browser service como último recurso). No gastar plata en C sin pasar (1).

---

### L-10 · `dict.get(k, default)` NO aplica el default si el valor existe pero es falsy (`''`) (2026-06-02) · Debugging / Datos

**Problema**
Una card basura de BICE (`Dólares BICE Aplica`, `restaurante=""`) se colaba a `beneficios.json` y a `/ver` pese a que el scraper tenía un default `'Desconocido'` para el nombre. El default "no se aplicaba" misteriosamente.

**Causa raíz**
`nombre = fields.get('Marca', meta.get('name', 'Desconocido'))`. `dict.get(k, default)` solo usa el `default` cuando la **key falta**, no cuando la key existe con valor **falsy**. BICE entregaba `Marca=''` (presente pero vacío), así que `.get` devolvía `''` (no el default) y la card quedaba con restaurante vacío.

**Fix**
Cadena `or` (que sí cae al siguiente operando ante un valor falsy) + descarte explícito:
```python
nombre = (fields.get('Marca') or meta.get('name') or '').strip()
if not nombre:
    return None
```
Más: remoción quirúrgica de la entrada basura ya presente en `beneficios.json`/`.csv` (931→930) y un guard en `verificar_salud.py` (extensión de L-07) que **falla** si reaparece cualquier beneficio con `restaurante=''`.

**Lección**
`dict.get(k, default)` ≠ "valor o default". Cubre solo key ausente, no valores falsy (`''`, `0`, `None`, `[]` explícitos). Para "primer valor no vacío", usar `a or b or c`. Y para campos que un scraper puede entregar vacíos, **validar y descartar** (`return None`), no confiar en el default de `.get`.

**Evitar a futuro**
- Cuando un default "no se aplica", sospechar valor presente-pero-falsy antes que bug de lógica.
- En scrapers, todo campo identificador (nombre de comercio/restaurante) que puede venir vacío → validar y descartar la entrada, no dejarla pasar.
- Cada fix de card basura se convierte en aserción del health check (patrón L-07): el guard `sin_restaurante` ya protege esta regresión.

---

### L-11 · Los `id` deben ser únicos: disambiguar colisiones, no borrar (2026-06-02) · Datos y calidad

**Problema**
Había `id` duplicados en `beneficios.json` (ej. `ripley_hitomi_tomi`, `ripley_rossie_la_loca`, `entel_just_burger`) y en `bencinas.json` (tiers Gold/Silver/Plus del mismo descuento colapsando al mismo id).

**Causa raíz**
Dos patrones de colisión: (a) cuando la fuente no trae un id propio (Ripley/Entel), el scraper cae a un **slug del nombre** → dos ofertas distintas del mismo restaurante chocan; (b) el id de bencina **omitía la `tarjeta`** → los 3 tiers de un mismo banco/día/cadena colapsaban a un id. Un id repetido rompe `/beneficios/{id}` (api.py:345 devuelve **solo el primer match**) y el upsert a Pinecone (el id es el id del vector → colisión sobrescribe).

**Fix**
Helper `_asegurar_ids_unicos()` en `scrapers.py` (auto-cura en el cron), wireado en Ripley/Entel/Bencina. Política **disambiguar, no borrar**: firma = `json.dumps(asdict(it) sin id ni fecha_scrape, sort_keys=True)`; si `(id_base, firma)` ya se vio → dup exacto, se descarta; si el id colisiona con **otra** firma → se suffija `_2/_3` preservando la 1ra ocurrencia. Idempotente. Cleanup quirúrgico sobre la data ya presente (930→929: 1 dup exacto dropeado, 2 colisiones reales suffixadas) + 7 tier-ids de bencina suffixados. Guard nuevo en `verificar_salud.py`: **falla** si reaparece cualquier id duplicado (beneficios y bencinas).

**Lección**
Cualquier id que un scraper derive de un slug de nombre (o que omita un campo discriminante como `tarjeta`) **va a colisionar**. Borrar una de las dos cards pierde una oferta real; la política correcta es **disambiguar** (suffix `_2/_3`) y solo dropear el duplicado **exacto** (idéntico salvo `fecha_scrape`).

**Evitar a futuro**
- Todo id que no venga de la fuente con garantía de unicidad → pasar por un disambiguador idempotente en el `scrapear()` del banco.
- Convertir cada clase de colisión en aserción del health check (patrón L-07): el guard `dup_ids` ya protege ambos archivos.
- Para distinguir "dup exacto" de "colisión real": comparar la firma del objeto **excluyendo** los campos volátiles (`id`, `fecha_scrape`).

---

### L-12 · Cleanup de datos durable: round-trip por el dataclass real + `csv.DictWriter` (2026-06-02) · Datos y calidad

**Problema**
Para limpiar `beneficios.json`/`.csv` sin regresionar nada, había que garantizar que el resultado fuera **idéntico** a lo que produce el cron (paridad), no una versión "parecida" editada a mano.

**Causa raíz**
Editar los JSON/CSV a nivel de dict/texto a mano arriesga (a) perder campos o cambiar su orden vs. el output del cron, y (b) en el CSV, romper los CRLF (el bloat "945/968 líneas falsas" de L-10 venía de editar en **text-mode**, no del módulo `csv`).

**Fix**
Cleanup por **round-trip a través del modelo real**: `Beneficio(**d)` / `DescuentoBencina(**d)` → correr el disambiguador → `asdict()` de vuelta. Es **lossless** porque `__post_init__` preserva `fecha_scrape` (verificado: 0/930 y 0/31 ítems cambiados en un round-trip puro). El CSV se regeneró con la **misma lógica `guardar_csv`** (`csv.DictWriter`, `newline=''`) → byte-idéntico al de disco (594279 bytes), CRLF intactos.

**Lección**
Para un cleanup que debe tener **paridad con el cron**, no edites el artefacto a mano: reconstruí por el **mismo código** que lo genera (el dataclass + el writer real). Antes de confiar en el round-trip, **probá que es lossless** (round-trip puro → 0 ítems cambiados). El módulo `csv` **sí** respeta CRLF; el problema de L-10 era el text-mode manual, no `csv.DictWriter`.

**Evitar a futuro**
- Cleanup de data que un cron regenera → importar los modelos/writers reales y round-trippear, no editar dicts/texto.
- Verificar losslessness con un round-trip de control (sin cambios) ANTES de aplicar el delta real.
- CSV generado por `csv.DictWriter` se puede regenerar sin miedo al CRLF; solo el text-mode manual lo rompe.

---

### L-13 · Una migración Playwright→requests hay que verificarla EN VIVO (2026-06-02) · Scraping / QA

**Problema**
Al migrar Itaú + LiderBCI de Playwright a `requests` (L-01), el health check daba verde — pero eso solo probaba que la **data ya presente** en el JSON era válida, no que el scraper reescrito **realmente trajera datos** del sitio.

**Causa raíz**
`verificar_salud.py` valida data-at-rest (el JSON en disco). Un scraper reescrito que silenciosamente devuelve `[]` (el modo de falla de L-01 en el cron de Render) **pasaría** el health check igual, porque la data vieja sigue ahí — hasta que el próximo cron la regenere a 0 y recién ahí se note en producción.

**Fix**
Correr ambos scrapers **en vivo** antes de shippear: `ScraperItau().scrapear()` → 68, `ScraperLiderBCI().scrapear()` → 11, confirmando que traen ítems con campos reales (no shell/challenge). Recién con eso confirmado, push.

**Lección**
El health check prueba **el artefacto**, no **el fetch**. Toda migración de mecanismo de scraping (browser→requests, cambio de UA, nuevo endpoint) debe verificarse **ejecutando el scraper contra el sitio real** y contando ítems, porque el modo de falla (silent 0 en el cron) es invisible para un check de data-at-rest.

**Evitar a futuro**
- Tras reescribir un `scrapear()`, correrlo en vivo y assertar `len(items) >= piso_esperado` ANTES del push, no confiar en el health check.
- Idealmente, el piso por banco del health check (ya existe) atrapa el 0 en el **próximo** cron — pero verificar en vivo lo atrapa **antes** de shippear.

---

### L-14 · Cards sin campo de display: recuperar el dato real + red genérica en `__post_init__` (2026-06-02) · Datos y calidad

**Problema**
6 cards llegaban con `descuento_texto=''` Y `descuento_valor=0` (`falabella_caoba-bar`, `itau_men__priceless...`, 4× `security_*`). No eran basura como BICE (L-10) — tenían `restaurante` real —, pero renderizaban una card "muda" en `/ver`, sin nada que comunicar al usuario.

**Causa raíz**
Cada scraper construye el `descuento_texto` a partir del `%` (`f"{valor}% dcto."`). Cuando la fuente **no expone un porcentaje** (menús Priceless de Security; entradas genéricas de programa de Itaú; promos presenciales sin % de Falabella), el texto quedaba `''`. Dos sub-casos distintos: en Security el dato **sí existe** en un campo adyacente (`field_titulo_caluga = "Menú Priceless"`) que el parser ignoraba; en Itaú/Falabella **no hay** un % ni un texto recuperable de la fuente.

**Fix (híbrido)**
- **Opción A (recuperar dato real) donde existe:** `ScraperBancoSecurity._parsear_item` cae a `attrs.get('field_titulo_caluga')` cuando `descuento_valor == 0`. Toca **solo la clase del banco afectado** (regla del proyecto). Verificado en vivo (L-13).
- **Opción B (red de seguridad genérica) para el resto:** en `Beneficio.__post_init__` —el **único chokepoint que corre en TODA construcción** de `Beneficio`, o sea en el cron y en cualquier cleanup— si queda sin `%` ni texto, `descuento_texto = "Beneficio exclusivo"`. Como corre **después** del parser de Security, no pisa el "Menú Priceless" ya seteado.
- Cleanup data-at-rest por round-trip del dataclass (L-12) + guard nuevo en `verificar_salud.py`: **falla** si reaparece `descuento_texto=''`.

**Lección**
Ante un campo de display vacío, **no saltes directo a la etiqueta genérica**: primero busca si la fuente trae el dato en un campo adyacente (acá `field_titulo_caluga`). El híbrido — recuperar dato real donde existe, genérico solo donde no — da mejor UX sin inventar. Y la red de seguridad va en el **único punto por donde pasan todos los objetos** (`__post_init__`), no replicada en N scrapers: así el invariante "ninguna card sin texto" se cumple para cualquier banco, presente o futuro, en cron y en cleanup.

**Evitar a futuro**
- Para un display vacío, revisar el payload crudo de la fuente por un campo título/descripción adyacente ANTES de etiquetar genérico.
- Invariantes que deben valer para TODOS los objetos (no quedar vacío, normalizar, default) → ponerlos en `__post_init__` del dataclass, no en cada parser. Un solo lugar, cobertura total, sin olvidos.
- Convertir el invariante en guard del health check (patrón L-07): `descuento_texto=''` ya está protegido.
- Recuperación tipo A (campo adyacente del scraper) hay que verificarla **en vivo** (L-13): el health check no prueba que el parser reescrito traiga el campo nuevo.

---

### L-15 · Un banco que funcionaba en el cron cae a 0 por geo-fence del runner — no es el código (2026-06-22) · Scraping / Debugging

**Problema**
Banco Falabella desapareció de producción (**97 → 0** beneficios) el 2026-06-20. El cron de GitHub Actions seguía dando "success" y mandando email de scraping exitoso. Fernando reportó "faltan muchos descuentos".

**Causa raíz**
Falabella activó **geo-fencing**: desde ~2026-06-20 sirve su página `/descuentos/restaurantes` **vacía** ("No se encontraron beneficios") a IPs no chilenas. El runner de GitHub Actions corre en datacenter USA → recibe HTTP 200 con 0 cards, **sin error ni captcha**. El scraper (`requests` + brace-matching en `"discountDays":[`) devuelve `[]` sin excepción → 0 Falabella. El código NO cambió (último commit al scraper: 2026-06-02). Confirmado con dos sondas: el scraper trae **95 desde la IP de Fernando (Chile)** HOY, y `WebFetch` (infra datacenter) trae la **página vacía**. En el historial del JSON, Falabella estaba en 97 el 06-18 y cayó a 0 en la corrida del 06-20.

**Fix**
(1) Restaurar ya: scrapear Falabella desde Chile (95) e inyectar sobre la data fresca del repo (merge quirúrgico L-04), commit+push → Render redeploya. (2) Que no recaiga: red de seguridad del orquestador (L-16). El geo-fence en sí solo se resuelve scrapeando desde una IP chilena (proxy/runner self-hosted) — backlog.

**Lección**
Un banco que **funcionaba** en el cron y cae a 0 **sin cambio de código** casi nunca es bug propio: es el sitio (geo-fence/WAF/caída). Test discriminante (extensión de L-09): correr el scraper desde la **IP de producción del cron** (datacenter) vs una **IP del país objetivo**. Datos desde Chile pero 0 desde datacenter → geo-fence, no el código. `WebFetch` sirve como "fetch desde IP externa" sin montar infra.

**Evitar a futuro**
- Ante "un banco cayó a 0": fijar la **fecha exacta** de caída en los commits del bot y revisar si el código cambió en esa ventana (`git log` del scraper). Sin cambio de código → sospechar el sitio, no el parser.
- Geo-fence vs anti-bot: geo-fence da 200-vacío a IP foránea; anti-bot da 403/challenge. El UA NO lo resuelve (es por IP — L-08 no aplica).
- `ultimo_scrape` de la API es `datetime.now()` al arrancar, **NO** la fecha real del scrape — no sirve para saber si el cron corrió. Mirar los commits del bot en GitHub.

---

### L-16 · Red de seguridad anti proceso-estéril POR BANCO: preservar el banco caído + alertar (2026-06-22) · Datos y calidad / Deploy

**Problema**
El cron corrió con "success" pero un banco (Falabella) trajo 0, y el `git commit` del bot **borró el banco entero** de `beneficios.json` en silencio. El email salió como exitoso ("858 beneficios") sin avisar que faltaba un banco completo. Es la regla cardinal del workspace (**L-W20, "proceso estéril"**) a nivel banco: *corrió ≠ insertó*.

**Causa raíz**
El orquestador captura el fallo por banco como `0` (try/except → []) y `guardar_json` **sobreescribe** la data previa sin comparar. El cron commitea lo que haya, aunque un banco haya colapsado. El email reportaba solo el total, no la pérdida de un banco. El `verificar_salud.py` SÍ tiene pisos por banco que lo habrían atrapado, pero **no estaba wireado al cron** (solo pre-push local).

**Fix**
`OrquestadorScrapers.preservar_bancos_caidos()`: tras scrapear y ANTES de guardar, compara el conteo por banco nuevo vs el `beneficios.json` previo en disco; si un banco trae 0 teniendo datos previos, **reinyecta los previos** (quedan stale pero presentes) y lo registra. `escribir_status()` vuelca los preservados a `scrape_status.json`; el `scraper.yml` lee el flag y el email **ALERTA** en asunto + banner (antes reportaba "success" liso). Idempotente; no toca bancos sanos (verificado: caso caído reinyecta 95 + alerta=True; caso de control no toca nada).

**Lección**
Cuando un proceso automático **sobreescribe** una fuente de verdad con el resultado de N fuentes independientes, una sola fuente caída no debe poder **borrar** su sección. La defensa correcta no es solo alertar: es **preservar el último dato bueno** (mejor stale que ausente) Y alertar. El chokepoint va en el orquestador (corre en cada cron), igual que el invariante de L-14 fue al `__post_init__`. Un "success" que esconde un banco en 0 es peor que un fallo ruidoso.

**Evitar a futuro**
- Todo cron que sobreescriba un agregado de N fuentes → comparar contra el snapshot previo y preservar las que cayeron a 0, no commitear el colapso.
- El reporte de éxito del cron debe **distinguir** "todo ok" de "ok pero faltó X" — un email verde uniforme oculta el proceso estéril parcial.
- Wirear el health check con pisos por banco al cron (no solo pre-push local), como gate o como fuente de la alerta. (Backlog: pre-deploy gate en Render.)

---

### L-17 · Chequeo experto por banco: clasificar + reintentar + preservar + reportar por banco (2026-06-22) · QA / Deploy

**Problema**
La red de seguridad de L-16 cubría "banco cae a 0", pero (a) no detectaba degradación parcial (un banco que trae 5 de 95), (b) no reintentaba fallas transitorias (un timeout/rate-limit puntual condenaba al banco), y (c) el email seguía siendo un total agregado, no el estado por banco. Fernando pidió que NINGÚN banco pueda caerse en silencio si cambia su página, con auto-corrección y un mail con el estado de cada banco.

**Causa raíz / contexto**
Un agregador de N fuentes necesita un chequeo POR FUENTE, no solo del total: el total puede verse "sano" (953) mientras un banco colapsó. Y "auto-corregible" tiene niveles: reintentar (transitorios) y preservar (resiliencia) SÍ son automáticos; auto-reparar el parser cuando una página cambia de estructura NO es seguro (requiere intervención humana avisada).

**Fix**
Módulo `chequeo_bancos.py` como fuente única: `PISOS_BANCOS` + `evaluar_corrida()` que clasifica cada banco **OK / DEGRADADO / CAÍDO** con piso efectivo = `max(piso_absoluto, 0.6 × previo)` (atrapa el colapso a 0 Y la caída relativa) + `generar_asunto()/generar_html()` (reporte por banco). En el orquestador: `_scrapear_con_reintentos()` (3 intentos con backoff; 1 para bancos diferidos) auto-corrige transitorios; `aplicar_red_de_seguridad()` preserva los CAÍDOS (reinyecta previos) y deja los DEGRADADOS sin preservar (podrían ser baja real) pero marcados; `generar_reporte()` vuelca `scrape_status.json` + `reporte_email.html` + `asunto_email.txt`. El `scraper.yml` manda el email con esos artefactos (tabla por banco; verde si todo OK, ⚠️ALERTA con nombres si algo falla). `verificar_salud.py` importa los pisos de `chequeo_bancos` (una sola fuente).

**Lección**
Para un cron que agrega N fuentes, el monitoreo correcto es **por fuente y en tres niveles**: detectar (clasificar cada fuente contra piso absoluto Y relativo al histórico), auto-corregir lo auto-corregible (reintentar transitorios, preservar el último dato bueno) y reportar con granularidad (estado por fuente, no un total que oculta el colapso de una). El piso relativo (60% del previo) atrapa degradaciones que un piso fijo deja pasar. La auto-reparación de código NO entra en "automático": se delega al humano, pero el sistema garantiza no caerse y avisar con detalle.

**Evitar a futuro**
- Centralizar pisos/umbrales en un módulo único que compartan el cron y el health check — no duplicar.
- Distinguir CAÍDO (preservar, es inequívoco) de DEGRADADO (no preservar, podría ser real) — preservar a ciegas inventaría data stale.
- El email de un cron de N fuentes debe listar el estado de CADA fuente; un asunto verde uniforme es el disfraz del proceso estéril (L-16 / L-W20).
- "Auto-corregible" ≠ "auto-repara el parser": sé explícito con el usuario sobre qué se corrige solo (transitorios, resiliencia) y qué necesita intervención (cambio de estructura del sitio).

---

### L-18 · Correr el cron en otro entorno (Windows) revela bugs que Linux ocultaba (2026-06-22) · Scraping / QA

**Problema**
Al montar el refresco local (mismo `scrapers.py`, pero en Windows en vez del runner Linux de GitHub Actions), el health check —ahora gate previo al push— atrapó 2 fallos que en producción NO existían: (a) `santander_ac-kitchen` duplicado, (b) 24 restaurantes de BICE con mojibake (`La PlÃ¢ce PastelerÃ­a`).

**Causa raíz**
Ambos eran bugs LATENTES que el entorno Linux del cron ocultaba:
- **Mojibake BICE = encoding-dependiente del OS.** El widget de BICE no manda charset; `response.text` deja que requests adivine. En Linux (locale UTF-8) adivina bien; en Windows (cp1252) adivina mal → mojibake. Mismo código, distinto resultado por OS.
- **Dup Santander = bug latente gatillado por la data.** Santander deriva el id de un slug del nombre y `_asegurar_ids_unicos` nunca se le wireó (sí a Ripley/Entel/BICE). Solo colisiona con 2 ofertas del mismo restaurante — apareció el día que Santander publicó una 2da "AC Kitchen".

**Fix**
- BICE: `response.encoding = 'utf-8'` antes de `.text` (no depender de la adivinanza).
- Santander y todos: `_asegurar_ids_unicos` **GLOBAL** en el orquestador (tras `_normalizar_todos`), no scraper-por-scraper. Un invariante que debe valer para TODOS va en el chokepoint único (mismo principio que L-14 con `__post_init__`).
- El health check como **gate del refresco** atrapó ambos ANTES de pushear: el push se bloqueó, producción quedó intacta.

**Lección**
Correr el mismo scraper en un **segundo entorno** (Windows local vs Linux cron) es un test gratis que destapa bugs encoding-dependientes y supuestos de locale. Y un bug "que nunca pasó" puede ser solo latente, esperando la data que lo gatille. Por eso: (1) nunca confíes en la adivinanza de encoding de requests — fija UTF-8 explícito cuando sabes que el contenido lo es; (2) los invariantes (ids únicos, no-mojibake, no-vacío) van en un chokepoint global, no wireados banco por banco; (3) un gate de health check antes de cada push convierte estos hallazgos en "bloqueo seguro" en vez de "data basura en producción".

**Evitar a futuro**
- Encoding: `response.encoding = 'utf-8'` en todo scraper cuyo origen no mande charset — no esperar a que otro OS lo revele.
- Unicidad/normalización/no-vacío: aplicar GLOBAL en el orquestador, no por scraper.
- El refresco local DEBE mantener el health check como gate (ya lo tiene): si falla, no pushea. Windows-vs-Linux nunca mete data mala.

---

### L-19 · Auditar la CALIDAD DE OFERTA por banco, no solo el conteo — y no inventar datos faltantes (2026-06-22) · Datos y calidad / UX

**Problema**
Fernando reportó "no salen las ofertas de Falabella para el lunes". El health check daba verde (954 beneficios, todos con campos), pero una auditoría minuciosa de los 14 bancos (lo que VE el usuario) destapó 3 problemas que el check de integridad no veía:
- 222 ofertas (Falabella, Entel, Lider BCI, Mach, Tenpo, Santander) no aparecen en el MAPA porque no tienen ubicación (son ofertas sin local fijo, aplican en toda la cadena).
- Santander (72/77) y Consorcio (8/8) sin % real: el scraper metía la descripción cruda pegada o el tipo de cocina como si fuera el descuento.

**Causa raíz**
El health check valida INTEGRIDAD (campos presentes, ids únicos, no-mojibake), no CALIDAD DE OFERTA (¿el % es real? ¿es geolocalizable? ¿el texto comunica el beneficio?). Un beneficio puede pasar el check y verse mal o no aparecer. Y el % de Santander/Consorcio NO existe en la fuente (verificado: ni listado, ni detalle, ni API; en Consorcio vive dentro de la imagen) — son beneficios de acceso, no descuentos porcentuales. Falabella tampoco trae ubicación en su fuente (ofertas a nivel cadena).

**Fix**
- Auditoría por banco con métricas de CALIDAD (no solo integridad): % con descuento real, % con días específicos, % con ubicación (mapa), texto limpio vs descripción cruda, url trazable. Veredicto: 8 OK, 5 sin-mapa (datos buenos), 2 sin-% real.
- Santander/Consorcio: etiqueta honesta "Beneficio exclusivo" (no "0%" ni descripción cruda) + tipo de cocina como descripción. NO inventar un %.
- Mapa: aviso que cuenta las ofertas sin local fijo y linkea a la Lista. NO inventar ubicaciones (un pin falso confundiría sobre dónde aplica la oferta).

**Lección**
"El dato existe" (pasa el health check) ≠ "la oferta se ve bien". Hay que auditar la CALIDAD DE CARA AL USUARIO por fuente: descuento real, geolocalizable, texto claro. Y cuando un dato NO está en la fuente (el % de Santander, la ubicación de Falabella), la respuesta correcta es mostrar honestamente lo que hay ("Beneficio exclusivo", aviso "sin local fijo"), NUNCA inventar (un 0%, un pin falso). Inventar es lo que MÁS daña la credibilidad y trazabilidad.

**Evitar a futuro**
- Extender el health check con métricas de calidad de oferta por banco (no solo integridad): % sin descuento, % sin ubicación, ratio de texto-largo (descripción cruda colada como descuento).
- Antes de "arreglar el filtro", verificar DÓNDE mira el usuario (mapa vs lista): el mismo dato puede estar en una vista y no en otra (amplía L-06).
- Dato faltante en la fuente → etiqueta/aviso honesto, jamás inventar el valor.
- **Antes de concluir "el dato no existe", agotar los endpoints/types HERMANOS** de la misma plataforma. Caso Consorcio (corrección posterior): el % SÍ existía (50% Casacostanera) pero no en las cards (`tab-card-credit-card`) sino en un type contenedor (`tab-beneficios-items`). Una API CMS (Modyo, Contentful, etc.) suele partir el dato en varios types relacionados — mirar uno solo da una conclusión falsa de "sin %". El usuario que conoce el producto es la mejor red de seguridad para estos casos.

---

### L-20 · "Aprendizaje" honesto para un cron = estadística sobre el propio histórico, no ML neuronal (2026-06-22) · Datos y calidad / Meta

**Problema**
Fernando pidió "que siempre aprenda (machine learning) y que aprenda cuando haya algún error, para que sea más inteligente". La tentación es prometer un modelo que se entrena solo y arregla scrapers. Eso sería humo: para 14 scrapers no hay dataset ni problema que justifique una red neuronal, y auto-reescribir código de scraping en producción es peligroso (L-15/L-17).

**Causa raíz / encuadre**
"Aprender" para un cron que agrega N fuentes no es entrenar un modelo: es acumular el propio histórico y ajustar el comportamiento con estadística simple y verificable. El sistema YA "aprendía" un poco (cada bug → un guard del health check; las lecciones L-XX). Lo que faltaba: memoria estructurada + autoajuste.

**Fix**
`aprendizaje.py`: cada corrida deja un snapshot en `historial.json` (la memoria, committeada al repo para persistir entre runners efímeros). Con esa serie temporal:
- **nivel_normal(banco)** = mediana de las últimas 12 corridas → aprende cuánto trae normalmente cada banco.
- **piso_aprendido** = max(piso_fijo, 60% del nivel normal) → el piso de alerta se calibra solo (sube si el banco crece; nunca baja del piso fijo, que protege contra degradación lenta).
- **tendencia(banco, nuevo)** → si un banco cae bajo el 70% de su normal histórico, se marca DEGRADADO aunque supere el piso fijo: alerta TEMPRANA, antes del 0.
El cron/refresco registran la corrida; el mail muestra cuántas corridas lleva en memoria. Más corridas → mejor calibración.

**Lección**
Ante un pedido de "machine learning", separar lo que agrega valor de lo que es humo. Para un cron de N fuentes, el "aprendizaje" honesto es: (1) memoria del propio histórico, (2) umbrales que se auto-calibran a la realidad observada, (3) detección de desviaciones del patrón normal. Todo verificable, sin caja negra. Y ser EXPLÍCITO con el usuario: "esto no es una red neuronal, es estadística sobre tu histórico" — la credibilidad vale más que el buzzword.

**Evitar a futuro**
- "Aprender de los errores" ya lo hace el patrón L-07 (cada fix → un guard permanente); el historial además guarda los problemas de cada corrida.
- Piso adaptativo SIEMPRE combinado con un piso fijo mínimo + detección de tendencia: un piso 100% adaptativo bajaría con una degradación lenta y dejaría de alertar.
- Nunca prometer auto-reparación de código como "aprendizaje": eso necesita humano/IA con validación (L-17), no se delega a un modelo en producción.

---

### L-21 · JS embebido en f-string: una comilla rompe TODA la página, y el health check no lo ve (2026-06-22) · Frontend / QA

**Problema**
Tras agregar un aviso en el mapa de `/ver` (un `innerHTML` con un `onclick` inline), la página cargaba (HTTP 200, 714 KB, datos embebidos) pero **no renderizaba ningún beneficio**. La lista quedaba vacía. El health check daba verde.

**Causa raíz**
El `onclick="document.querySelector(\'.view-btn...\')..."` dentro de un `innerHTML='...'` (string JS de comillas simples): el `\'` en el f-string Python produjo un `'` que **cerró el string `innerHTML` prematuramente** → error de sintaxis en el `<script>` → el script ENTERO no se parsea → ningún JS corre → la lista queda muda. **Un solo carácter tumbó toda la web.** El health check NO lo detecta porque prueba la data en disco (`beneficios.json`), no el JS de la página renderizada.

**Fix**
Sacar el `onclick` inline (3 niveles de comillas anidadas: JS string `'` → atributo HTML `"` → querySelector `'`) y usar `id` + `elemento.onclick=function(){...}` con el `querySelector` en JS puro, fuera de cualquier string. Verificado: `node --check` sobre el `<script>` de `/ver` pasa.

**Lección**
El JS embebido en un f-string Python es terreno minado de comillas: `{{`/`}}` para las llaves, `\'` que se vuelve `'`, comillas anidadas. Una comilla mal puesta no da un error parcial: **tumba todo el `<script>`** y la página queda muda aunque cargue con HTTP 200. Y el health check de datos NO lo ve. Tras tocar el HTML/JS embebido de `api.py`, **validar el `<script>` con `node --check`** antes de confiar.

**Evitar a futuro**
- Nunca anidar 3 niveles de comillas en JS embebido. Para handlers, usar `id` + `.onclick`/`addEventListener` en JS puro, no `onclick="..."` inline con strings.
- Tras editar el HTML/JS de `api.py`: descargar `/ver` y correr `node --check` sobre el `<script>` (o extraer el bloque, `{{`→`{`). Candidato a guard del health check.
- "La página carga" ≠ "la página funciona": HTTP 200 con datos embebidos puede tener el JS roto y no renderizar nada. (amplía L-13: verificar la web renderizada, no solo que responda.)

---

### L-22 · Dos procesos que REGENERAN y pushean la misma fuente de verdad → ordenarlos en el tiempo, no mergearlos (2026-06-23) · Deploy / Datos

**Problema**
Al alinear el correo de MiCartera a las 09:00 (pedido de Fernando), el cron de la nube (GitHub Actions, 09:00) quedó a la MISMA hora que el refresco local (PC, 09:00). Ambos corren `scrapers.py` (regeneran `beneficios.json` ENTERO) y hacen `git push` al mismo repo → a la misma hora chocarían.

**Causa raíz**
El step "Commit updated data" del cron hace `git add+commit+push` SIN `git pull` previo. Si el refresco local pushea entre el checkout del cron y su push, el push del cron es **non-fast-forward** → falla → el workflow falla → llega "❌ ERROR" en vez del reporte. Y NO se arregla con `pull --rebase` automático: ambos **regeneran** el archivo completo (no son ediciones parciales) → conflicto de merge sin criterio resoluble.

**Fix**
Separarlos en el tiempo con un ORDEN intencional: refresco **08:30** (Chile, trae los 15 frescos incl. Falabella geo-fenceado) → push ~08:33; cron **09:00** (USA) → checkout (toma esa data) → scrapea → preserva Falabella con la data del checkout → manda el mail → push. Margen 30 min ≫ scrape+push (~3 min). El primero deja la fuente fresca, el segundo la toma como base.

**Lección**
Cuando dos procesos **regeneran** (no editan parcialmente) y pushean la misma fuente de verdad versionada, NO los corras concurrentes ni confíes en merge (el rebase choca en el archivo regenerado). Sepáralos en el tiempo con un orden que haga el resultado correcto (acá Chile ANTES que USA, para que Falabella quede fresco antes del mail). El orden temporal ES la coordinación.

**Evitar a futuro**
Para N productores de un agregado versionado: orden temporal con margen > duración del más lento. Si DEBEN ser concurrentes, el segundo necesita `pull --rebase` + estrategia explícita de resolución por sección — frágil, mejor evitar. (Promovida a workspace **L-W44**.)

---

### L-23 · "¿Está operando?" se verifica contra el SCHEDULER, no se afirma (2026-06-23) · QA / Deploy

**Problema**
Fernando preguntó "¿está todo listo? ¿opera todos los días?". La tentación es responder "sí" de palabra.

**Causa raíz**
"Está en el código / configurado" ≠ "está activo y dispara". Un scheduled workflow de GitHub se **desactiva solo tras 60 días** sin actividad del repo; una Tarea de Windows puede estar deshabilitada o con `LastTaskResult≠0`; un secret puede faltar. Código correcto ≠ scheduler corriendo.

**Fix**
Verificar el estado REAL de cada scheduler (no el código):
- GitHub Actions: API `/actions/workflows` → `state == active`; `/actions/runs` → últimas corridas `conclusion == success`.
- Tarea Windows: `Get-ScheduledTaskInfo` → `State Ready`, `Settings.Enabled True`, `LastTaskResult 0`, `NextRunTime`.

**Lección**
"¿Está operando?" se RESPONDE con evidencia del scheduler (workflow `active` + última corrida `success` + tarea `Enabled` + `LastTaskResult 0` + próxima ejecución), no afirmando. Es **L-W20** ("¿corrió?" → verificar contra la fuente) aplicada a "¿está configurado para correr?" → verificar contra el scheduler.

**Plus técnico (Tarea Windows)**
`schtasks /Change /ST <hora>` RE-PIDE la password del usuario (re-aplica el principal) → se cuelga en shell no-interactivo. Para cambiar SOLO la hora sin password: `Set-ScheduledTask -InputObject` modificando `$task.Triggers[0].StartBoundary`, SI la tarea es **`LogonType Interactive`** (corre con la sesión, sin password guardada). Verificar con `(Get-ScheduledTask).Principal` antes.

**Evitar a futuro**
Ante "¿está listo/operando?", consultar el ESTADO de los schedulers, no leer el código. El código puede estar perfecto y el scheduler deshabilitado.

---

### L-24 · Dataset de fuentes oficiales que cambian mensual y bloquean fetch remoto → curado + trazable + cruce de control, leído desde el país objetivo (2026-07-01) · Datos y calidad / Scraping

**Problema**
Fernando pidió un apartado de "cuotas sin interés del mes por banco" (como Chócale) pero **desde la base de los bancos** (fuente oficial, trazable), con las cláusulas/condiciones. No existían datos ni scrapers para esto: cada banco publica distinto, las campañas cambian cada mes, y muchas páginas son SPA o dan 403 (WAF).

**Decisiones / hallazgos**
1. **Curado, no scraper automático.** Scrapear 15-20 bancos de cuotas de forma automática = frágil e incierto (formatos variables, imágenes/PDF, cambio mensual de estructura) → un scraper malo da cuotas equivocadas = **peor que no tener** (mata la credibilidad). Se eligió **curado mensual + trazable**: cada campaña con su **link oficial** + vigencia + confianza.
2. **Leer las oficiales desde el país objetivo.** El fetch remoto (WebFetch/agentes en infra US) da **403** en varios bancos chilenos; desde el **PC de Fernando (Chile) con `curl` UA-curl** (patrón L-08) responden 200 (Santander, Scotiabank, Lider BCI, Falabella, BCI, Consorcio). El entorno local del país ES el recurso para leer lo que la nube no puede. Aun así, algunas (BICE, Itaú) bloquean incluso desde Chile → dato del agregador + link oficial + nota honesta.
3. **El agregador (Chócale) como CONTROL, no fuente.** Como publica todos los meses, se cruza oficial-vs-Chócale para **marcar inconsistencias** (ej. vigencia Santander), no para copiar.
4. **No vender humo:** distinguir **0% real vs tasa preferencial** (automotriz/educación/salud casi nunca son 0%, son 0,79%-1,19% mensual) y marcar `sin_campana` donde el emisor no ofrece cuotas tipo campaña (Ripley, Mach), en vez de inventar.
5. **Timing de transición de mes:** el día 1 las fuentes aún muestran el mes anterior (campañas vencidas); el "mes en curso" no está publicado aún. Registrar la vigencia real por campaña y ser explícito en la foto (ej. "al 1-jul: la mayoría muestra junio, Scotiabank ya rotó a julio").

**Lección**
Para un dataset nuevo de N fuentes oficiales que cambian mensual y muchas bloquean el fetch remoto: **curado + trazable** (link oficial por dato) + **cruce contra un agregador como control de calidad** + **leer las oficiales con `curl` desde el país objetivo**, NO un scraper automático frágil. Marcar la **confianza por fuente** (oficial-verificada / oficial / secundaria) y no inventar (0% vs tasa; `sin_campana`). El apartado `/ver/cuotas` (server-side render + JS mínimo de filtros validado con `node`, L-21) se alimenta de `cuotas_sin_interes.json`.

**Evitar a futuro**
- Ante "tráelo de la fuente oficial" con fuentes que bloquean/​son SPA: no prometer scraper automático; curar con trazabilidad y leer desde el país objetivo (curl UA-curl).
- Un agregador de terceros es control, no fuente: úsalo para detectar inconsistencias.
- Datos financieros: distinguir 0% de tasa preferencial siempre; es el error que más engaña al usuario.
- En julio se repite la curación para validar que el proceso capta el cambio de mes (pedido de Fernando).

---

### L-25 · Un cambio de nivel sostenido queda "degradado" en falso si la ventana del nivel normal es muy larga → ventana ~1 semana (2026-07-06) · Datos y calidad / Meta

**Problema**
Itaú cayó de 71 a 23 restaurantes el 1-jul (real: renovó su campaña de Ruta Gourmet con menos comercios). 6 días después seguía estable en 23 (nuevo nivel), pero el correo lo marcaba **DEGRADADO** todos los días.

**Causa raíz**
El "nivel normal" del aprendizaje (base del piso adaptativo) era la **mediana de las últimas 12 corridas** (`N_VENTANA=12`). Con ventana de 12, la mediana aún cargaba los valores viejos (71 de junio) → piso = 60% de ~71 = **42**, sobre los 23 reales → DEGRADADO. Una ventana larga tarda ~7-8 días en reconocer un nuevo nivel; durante ese lapso marca un banco sano como degradado. (El piso ABSOLUTO ya se había bajado a 15, pero el efectivo = `max(absoluto, 60%·nivel_normal)`, y el 60% del nivel viejo mandaba.)

**Fix**
Bajar `N_VENTANA` de 12 a **7 días** (1 semana). Con ventana de 7, tras 6 días en 23 la mediana = 23 → piso = 15 → estado **OK**. Verificado con simulación (12 vs 7 vs 6): con 7, Itaú OK y **0 bancos con problema**, ninguno afectado.

**Lección**
En un "aprendizaje" estadístico (nivel normal = mediana de una ventana móvil), **la ventana define qué tan rápido reconoce un CAMBIO DE NIVEL sostenido**. Muy larga (12+) → un banco que cambió de nivel (renovación de campaña) queda marcado en falso por días. Muy corta (2-3) → una caída puntual se acepta como normal demasiado rápido (deja de alertar caídas reales). Para campañas que cambian mensual, **~1 semana (7) es el balance**: reconoce el nuevo nivel en días pero no traga una caída de 1-2 días. El piso fijo protege el mínimo absoluto siempre.

**Evitar a futuro**
- Al calibrar una ventana de media móvil/aprendizaje: dimensionarla a la **velocidad de cambio real** del fenómeno (campañas mensuales → ventana semanal), no dejar el default sin razón.
- Un banco marcado DEGRADADO **N días seguidos con el MISMO valor estable** (no bajando más) = probable nuevo nivel, no falla → la ventana debe reconocerlo. Si no, está mal dimensionada.
- Ventana + piso fijo + detección de tendencia trabajan juntos: la ventana aprende el nivel, el piso fijo es la red dura, la tendencia atrapa la caída temprana.

---

### L-26 · El sistema debe AUTO-GESTIONARSE, no solo avisar "falta algo" — auto-corregir lo auto-corregible, auto-diagnosticar lo que no (2026-07-06) · Meta / Infraestructura

**Principio (pedido de Fernando)**
Un correo que dice "⚠️ REVISAR, falta X" NO basta: pone la carga en el humano (leer + decidir + pedir el arreglo). El sistema debe **auto-gestionarse** — resolver solo lo que pueda cuando un banco cae/degrada, y escalar al humano SOLO lo que genuinamente no se puede automatizar.

**Qué se auto-gestiona (ya implementado):**
- **Fallas transitorias** (timeout, sitio lento) → reintentos automáticos (3× con backoff).
- **Geo-fence / bloqueo por IP** → el refresco local desde Chile lo trae, sin intervención.
- **Banco que cae a 0 teniendo datos** → red de seguridad: preserva los previos (la web no pierde el banco).
- **Cambio de nivel sostenido** (banco que renueva campaña con menos ofertas, ej. Itaú 71→23) → el aprendizaje recalibra el piso solo (ventana 7 días, L-25). Deja de marcar DEGRADADO en falso.

**Qué NO se puede auto-arreglar (y por qué):**
- **Cambio de estructura del sitio** (el banco rediseña su web, el selector del scraper deja de matchear) → requiere REESCRIBIR el scraper. Auto-reescribir código de scraping en producción es peligroso (L-17, L-20): un scraper mal auto-generado mete data basura, que es peor que no tener. NO se delega a un modelo sin validación. Se **auto-diagnostica** (guarda el HTML del caído en `diagnostico/`, detecta que el selector no matchea) y se avisa con el diagnóstico específico para acelerar el arreglo humano/IA.

**Lección**
"Auto-gestionado" tiene 3 niveles: (1) **auto-corregir** (transitorios, geo-fence, resiliencia, recalibración) → SIEMPRE automático; (2) **auto-diagnosticar** (qué falló exactamente, guardar evidencia) → automático; (3) **auto-reparar código** (scraper roto por cambio de estructura) → NO automático, requiere validación. El correo debe **distinguir** "esto se está resolviendo solo" (informativo, no es alarma) de "esto necesita que arregles el scraper" (acción real), para que el humano solo actúe en el nivel 3. Avisar sin auto-gestionar traslada el trabajo al humano; auto-reparar código sin validación mete basura. El balance correcto: automatizar niveles 1-2, escalar el 3 con diagnóstico listo.

**Evitar a futuro**
- Ante "hazlo auto-gestionado": mapear cada modo de falla a su nivel (1/2/3), automatizar 1-2, y ser explícito con el usuario sobre qué queda en 3 — NO prometer auto-reparación de código como si fuera segura.
- El correo de un cron debe separar "preservado / se resuelve solo" de "requiere tu acción": un ⚠️ genérico obliga al humano a investigar cuál es cuál (media L-16/L-17).

---

### L-27 · Cerrar el loop de auto-gestión: la revisión humana confirma un nivel y el sistema deja de alarmar por él — pero re-alarma si empeora (2026-07-10) · Meta / Datos y calidad

**Problema**
Tras el auto-diagnóstico de L-26 (el sistema clasifica cada incidente como `auto` o `revisar` según su histórico), quedaba un caso sin cerrar: un banco que **acaba** de recortar su oferta de forma REAL (Banco Security 108→70, verificado en su API) se clasifica —correctamente— como `revisar`, porque con solo 1-2 días de datos el sistema no puede distinguir "recorte real permanente" de "empezó a caer y va a seguir cayendo". Resultado: el correo marca ⚠️ REVISAR todos los días hasta que pasen ~3 días y el auto-diagnóstico lo dé por estable. Yo YA lo revisé y sé que es real, pero mi conclusión no entraba al sistema: se perdía cada día.

**Causa raíz**
El auto-diagnóstico solo aprendía del **histórico automático** (¿ya pasó antes? ¿está estable?). No tenía un canal para incorporar la **conclusión de una revisión humana**. Un incidente recién confirmado como real por mí seguía tratándose como "sin confirmar" hasta que la estadística sola lo alcanzara días después.

**Fix**
`confirmar_nivel(banco, nivel, motivo, fecha)` en `aprendizaje.py` → registra en `niveles_confirmados.json` (committeado al repo, como `historial.json`) que la baja de ese banco fue **revisada y confirmada como real**. `clasificar_incidente` lo chequea PRIMERO: si el banco trae ≥85% del nivel confirmado → `auto` ("recorte real ya revisado, no una falla") → el correo deja de alarmar. Pero si cae **bajo** ese 85% → NO aplica la confirmación → vuelve a `revisar` (es una caída NUEVA, distinta de la ya revisada). El umbral 85% deja margen de ruido normal sin tragarse una segunda caída real. Aplicado a Banco Security (nivel confirmado 70): asunto verde, y si cae bajo ~60 re-alarma.

**Lección**
Un sistema auto-gestionado que aprende solo de su histórico automático tiene un punto ciego: el conocimiento del humano que YA revisó. Hay que darle un **canal de feedback explícito** para que la revisión humana se vuelva permanente — `confirmar_nivel` convierte "ya lo miré, es real" en un dato que el sistema respeta. Clave: la confirmación es **por nivel, no un mute global** — silenciar el banco "para siempre" perdería una segunda caída real. Anclar la confirmación a un nivel (≥85%) mantiene la alarma viva para lo que de verdad es nuevo. Es el mismo principio de "aprender de los errores" (L-26) pero cerrando el loop con el humano, no solo con la estadística.

**Evitar a futuro**
- Todo auto-diagnóstico basado en histórico necesita un canal para incorporar la revisión humana; si no, re-alarma por algo ya resuelto hasta que la estadística lo alcance.
- Confirmar/silenciar SIEMPRE anclado a una condición medible (un nivel, un rango), NUNCA un mute global — un mute global es un punto ciego para la próxima falla real de esa misma fuente.
- El artefacto de confirmación (`niveles_confirmados.json`) se commitea, igual que la memoria del aprendizaje, para persistir entre runners efímeros.

---

### L-28 · Un filtro/búsqueda de UI sobre un campo opcional debe dejar PASAR el vacío, no excluirlo (2026-07-29) · Datos y calidad / UX

**Problema**
Filtrar "Falabella + jueves" en el mapa de `/ver` no mostraba NADA, aunque las 37 ofertas existían. Una auditoría ácida destapó 4 casos más del mismo tipo: el filtro de Modalidad escondía 222 ofertas (200 del Banco de Chile), el de Zona borraba 277 ofertas nacionales, y la búsqueda por comuna daba resultados incompletos.

**Causa raíz**
Cada filtro comparaba un campo que puede venir VACÍO y excluía el vacío en silencio: `regions.includes(d.ubicacion)` con `ubicacion=''` nunca matchea; `(mode==='presencial' && d.presencial)` con `presencial=False` Y `online=False` no matchea ningún modo específico; el `txt` de búsqueda no incluía `comuna` ni `tags`. El dato EXISTE, pero el filtro lo esconde.

**Fix**
Un filtro sobre un campo opcional deja pasar el registro cuando el campo viene vacío ("aplica siempre"): `mR = !regions || !d.ubicacion || regions.includes(...)`; `mMode = ... || (mode==='presencial' && (d.presencial || !d.online))`; el mapa muestra las ofertas sin local fijo como tarjetas debajo; el buscador indexa `comuna` + `tags`.

**Lección**
Primo de L-10 (`dict.get` con falsy) pero en la capa de cara al usuario: un campo opcional vacío NO es "no cumple", es "aplica siempre". Excluir el vacío esconde datos reales y el usuario concluye "no hay nada".

**Evitar a futuro**
- Al escribir `campo.includes(x)` / `x === valor` en un filtro, preguntar: ¿qué pasa si el campo viene vacío? Si "aplica siempre" es lo correcto, dejarlo pasar explícitamente.
- Verificar MIDIENDO cuántos registros tienen el campo vacío ANTES de asumir que el filtro está bien.
- Un índice de búsqueda incluye TODOS los campos donde el usuario esperaría encontrar algo (nombre, geografía, tipo).

---

### L-29 · Campo genérico de una card → el nombre real vive en un campo hermano (slug del link) (2026-07-29) · Scraping / Datos

**Problema**
95 ofertas de Falabella mostraban "Dcto en Restaurante" en vez del nombre del local (invisibles a la búsqueda por nombre, mala UX).

**Causa raíz**
`ScraperBancoFalabella._parsear_card` tomaba el campo `title` de la card, que Falabella llena con un texto GENÉRICO. El nombre real vive en el slug del `linkUrl` (`falabella_petit`, `falabella_vapiano`, `falabella_40-de-dcto-en-restaurantes-mallplaza-tanta`).

**Fix**
`_nombre_desde_slug()`: cuando el título es genérico, des-slugificar el link (quitar prefijos de campaña/mall, title-case el resto). 95 nombres recuperados (Petit, Vapiano, Muu Grill, Tanta…). Se arregló el scraper Y se regeneraron los nombres en `beneficios.json` con la misma lógica.

**Lección**
Es L-19 aplicado (el dato en un campo hermano, como el % de Consorcio): antes de aceptar un valor genérico/faltante, agotar los campos hermanos de la card. El slug del link suele traer el nombre real. Recuperar, NUNCA inventar.

**Evitar a futuro**
- Un campo genérico repetido en muchas cards (× 95) es señal de que el scraper mira el campo equivocado; buscar el dato en id/slug/link/description.

---

### L-30 · El refresco local hace `git reset --hard` y borra los cambios sin commitear (2026-07-29) · Deploy / Git

**Problema**
Se aplicaron 4 fixes de seguridad al código y, antes de commitearlos, se perdieron: el working tree volvió a `origin/main`.

**Causa raíz**
El refresco local (Tarea Windows `MiCartera-Refresco`, ~08:30) corre `git reset --hard origin/main` antes de scrapear, para partir de una base limpia. Cualquier cambio sin commitear en el clone se borra sin aviso.

**Fix**
Re-aplicar y commitear+pushear INMEDIATAMENTE cada bloque verificado, sin acumular trabajo sin commitear entre pasos.

**Lección**
En un repo donde un proceso automático hace `git reset --hard`, los cambios sin commitear son efímeros. No juntar varios fixes "para pushear todo junto al final": commitear pronto cada bloque verificado. Un commit local frecuente es la única red contra el reset.

**Evitar a futuro**
- Tras verificar un fix (py_compile + node --check + health check) → commit + push de inmediato.
- Si la herramienta de escritura está intermitente, priorizar commitear lo aplicado antes que aplicar más.

---

### L-31 · Apartado nuevo que reusa una vista existente → dataset SEPARADO, no tocar la vista que funciona (2026-08-03) · Arquitectura / UX

**Problema**
Había que agregar un apartado "Otros beneficios" (farmacias, transporte, ski, hoteles) con la misma lógica de `/ver` (filtros + búsqueda), sin romper la página de restaurantes que estaba perfecta.

**Causa raíz**
Mezclar los "otros" en el mismo `beneficios.json` / la misma vista habría afectado `/ver`, los pisos por banco, la red de seguridad y el health check. Al capturar TODO, Santander pasó de ~71 restaurantes a 295 → habría disparado falsas alarmas de degradación/nivel y contaminado la vista de restaurantes.

**Fix**
Campo `seccion` en el modelo (`"restaurante"` por defecto | `"otro"`); el orquestador SEPARA los `"otro"` a `beneficios_otros.json`; `/ver` (restaurantes) queda intacto; el apartado nuevo carga el dataset separado. 228 otros de Santander + Consorcio.

**Lección**
Para un apartado nuevo que reusa lógica existente, aislar los datos en un dataset separado y NO tocar el pipeline que funciona. El usuario fue explícito ("no rompas lo que funciona"): reusar la UI/lógica no significa compartir el dataset.

**Evitar a futuro**
- Al agregar una sección, preguntar qué pipelines comparten el dato (pisos, red de seguridad, health check) y aislar ANTES de mezclar.
- Un conteo que se dispara (71 → 295) al capturar más es la señal de que estás contaminando el dataset original, no ampliándolo.

---

### L-32 · Scrapers que ya traen datos y los BOTAN → capturarlos con un flag, no duplicar el scraping (2026-08-03) · Scraping / Datos

**Problema**
Se necesitaban beneficios no-restaurante de los bancos (farmacias, transporte, ski, hoteles); parecía requerir escribir scrapers nuevos.

**Causa raíz**
Santander y Consorcio YA scrapeaban TODOS sus beneficios, pero descartaban los no-restaurante con `if not es_restaurante: return None`. El dato ya se estaba trayendo y tirando a la basura antes de llegar al modelo.

**Fix**
En vez de descartar, marcar `seccion = "restaurante" if es_restaurante else "otro"` y capturarlos; el dato ya venía gratis (0 requests extra). 224 de Santander + 4 de Consorcio.

**Lección**
Antes de escribir un scraper nuevo, revisar si el existente ya trae el dato y solo lo filtra/bota. Convertir un descarte en una etiqueta es más barato y robusto que un scraper nuevo.

**Evitar a futuro**
- Buscar `return None` / `continue` por filtro de keywords en los scrapers — ahí puede haber datos que se están tirando.
- "Necesito un scraper nuevo" es una hipótesis a verificar, no un hecho: primero medir qué trae y descarta el scraper actual.

---

### L-33 · Auditar trazabilidad midiendo el DOMINIO de la fuente por dataset (2026-08-03) · Datos y calidad / Meta

**Problema**
Fernando pidió "todo trazable y chequeado, si no, no mostrar". No había forma de saber qué datos eran de fuente oficial y cuáles de un agregador poco confiable.

**Causa raíz**
Se mezclaban datos oficiales (webs de bancos) con datos de agregadores (`descuentosrata.com`) sin distinguirlos. La bencina (31 descuentos) venía 100% de un agregador — por eso Shell estaba desactualizado (sábado en vez de jueves) sin que nadie lo notara.

**Fix**
Medir el DOMINIO de `url_fuente` por dataset y clasificar OFICIAL / AGREGADOR / SIN FUENTE. Resultado: restaurantes (887), otros (24) y cuotas (28) → 100% oficial; bencina-descuentos (31) → 100% agregador. Se marcó la procedencia del agregador en la web y se filtró "otros" a solo verificables.

**Lección**
La trazabilidad se AUDITA midiendo el dominio de la fuente, no asumiendo. Un dataset "que funciona" puede venir de un agregador no confiable y estar desactualizado. Regla: marcar la procedencia (oficial vs agregador) y "si no es trazable/chequeado, mejor no mostrar" (o marcarlo explícito). Es L-24 aplicado como auditoría.

**Evitar a futuro**
- Al agregar un dataset, registrar la fuente por dato y su nivel de confianza.
- Un agregador es control de calidad, NO fuente de verdad (L-24): si es la única fuente, marcarlo y planificar la curación oficial.

---

### L-34 · Un regex laxo de % captura el CAE del financiamiento como descuento (2026-08-03) · Scraping / Datos

**Problema**
En "otros beneficios", Bip Solar (paneles solares) mostraba "54% dcto." — un descuento que no existe. Pasaba con todo lo que era financiamiento en cuotas.

**Causa raíz**
`re.search(r'(\d+)\s*%', f"{nombre} {descripcion}")` sobre la descripción cruda tomaba el "54" de "CAE 1,54%" (Costo Anual Equivalente del financiamiento) como si fuera un 54% de descuento.

**Fix**
Excluir la frase del CAE antes de buscar (`re.sub(r'CAE[^.]*', '', ...)`) + regex estricto `(?<![\d,])(\d{1,2})\s*%`. Bip Solar y similares quedaron sin % inventado. De 228 "otros", solo 24 tienen % real verificable.

**Lección**
Un regex `(\d+)\s*%` sobre texto crudo captura CUALQUIER número%, incluyendo tasas de financiamiento (CAE, interés). Para extraer un descuento, excluir el contexto financiero y acotar el formato. Mostrar un % inventado es peor que no mostrar % (L-19).

**Evitar a futuro**
- Al extraer un % de una descripción, preguntar qué OTROS % puede haber (CAE, interés) y excluirlos.
- Verificar que el % que se muestra corresponde a un descuento, no a una tasa.

---

### L-35 · Curar desde la fuente oficial + confianza por dato + guardia de trazabilidad (2026-08-03) · Datos y calidad / Meta

**Problema**
Los descuentos de bencina venían 100% de un agregador (`descuentosrata.com`) y tenían errores reales: Shell/Scotiabank en sábado (era jueves), Itaú Copec en viernes (era martes), BancoEstado viernes $100 (era martes $50), BCI $100/L (era 7% cashback tope $7.000), Santander Consumer lun-vie (era vie-dom).

**Causa raíz**
Un agregador de terceros no es fuente de verdad (L-24): se desactualiza y comete errores, y no había forma de saber la procedencia de cada dato.

**Fix**
(1) Re-curar desde la **fuente oficial** (Copec `ww2.copec.cl/personas/promociones`) + medios verificados (ago-2026) para Aramco/Shell. (2) Campo **`confianza`** por dato ("oficial (...)" vs "secundaria (medios...)") + `url_fuente` oficial por cadena. (3) **Guardia de madrugada** que verifica la trazabilidad SIEMPRE (alerta si un descuento pierde la `confianza` o vuelve al agregador). (4) Marcar la procedencia en la web ("verifica en tu banco").

**Lección**
Un agregador es CONTROL de calidad, no fuente (L-24). La data de cara al usuario se cura desde la fuente oficial, se marca su `confianza` por dato, y un **guard automático la vigila en cada corrida** (no una sola vez). Cuando no hay dato chequeado, mostrar **"estamos confirmando descuentos"** en vez de un dato dudoso — nunca mostrar lo no verificado (amplía L-19/L-33).

**Evitar a futuro**
- Ningún dataset de cara al usuario debe depender de un solo agregador sin marcar la procedencia.
- Comparar agregador vs oficial es la forma de DETECTAR los errores (aquí destapó 5).
- Todo campo de calidad (confianza, fuente) va al guard de la guardia, para que se vigile siempre.

---

### L-36 · Filtros dinámicos/faceteados: atenuar las opciones sin resultados, no dejarlas devolver vacío (2026-08-03) · UX / Frontend

**Problema**
Los filtros eran estáticos: al elegir un banco que solo tiene descuentos de lunes a viernes, los botones "sábado" y "domingo" seguían clickeables y, al usarlos, la página devolvía vacío. El usuario no tenía cómo saber qué combinaciones SÍ tienen data — probaba a ciegas y concluía "no hay nada". Pedido de Fernando: "si filtro por banco, ya quiero que los días o ciudades, o % de descuento se auto filtren… un banco que tenga solo descuentos de lunes a viernes, la idea es que sábado y domingo ya no se pueda seleccionar, se ponga más clara como bloqueada".

**Causa raíz**
Cada control de filtro ofrecía TODAS las opciones del universo, sin mirar qué queda disponible tras los OTROS filtros ya aplicados. Un filtro que no refleja el estado del resto de los filtros invita a callejones sin salida (combinación válida en la UI, vacía en la data).

**Fix**
Faceteado dinámico en el `render()` de `/ver` y `/ver/beneficios`: tras cada cambio de filtro se calcula un `_base` (el dataset con TODOS los filtros aplicados MENOS el eje que se está pintando), se arma el conjunto de valores que sí producen resultados (`_diasOK`) y se marca cada opción no disponible con la clase `.day-off` (`opacity:.28; filter:grayscale(1); pointer-events:none`) → se ve claramente bloqueada y no se puede clickear. Cuando una sección entera no tiene data, el estado vacío muestra **"⏳ Estamos confirmando los descuentos de esta sección"** en vez de un vacío mudo. La **guardia de madrugada** (`revision_madrugada.py`) vigila que el patrón siga vivo ("es clave un agente que revise que sea así siempre").

**Lección**
Un filtro debe reflejar el estado de los DEMÁS filtros: al fijar un eje, los otros recalculan sus opciones y las que no tienen resultados se atenúan/bloquean, en vez de dejarlas seleccionables y devolver vacío. Es el complemento "activo" de L-28 (que dejaba PASAR el vacío): aquí, además, se le muestra al usuario qué combinaciones existen. Sin data para una sección → mensaje honesto "estamos confirmando", nunca un vacío que parece un bug.

**Evitar a futuro**
- Pendiente aplicarlo a los OTROS ejes (región/comuna, % de descuento) y a las vistas de bencinas y cuotas — hoy solo el eje de día en `/ver` y `/ver/beneficios`.
- El cálculo de facetas se hace sobre el dataset ya filtrado por el resto de ejes (`_base`), no sobre el universo completo, o las opciones "disponibles" mentirían.
- Todo patrón de UX que el usuario pidió "que sea siempre así" → convertirlo en check de la guardia (patrón L-07), no confiar en que no se regresione.

---

### L-37 · Curación protegida por un guard, pero el generador sigue produciendo la data mala → deadlock del pipeline (2026-08-04) · Datos y calidad / Deploy

**Problema**
Tras re-curar los descuentos de bencina desde fuente oficial (L-35, edición manual de `bencinas.json`: Shell=jueves, campo `confianza`) y agregar un guard en `verificar_salud.py` que EXIGE Shell=jueves, el **refresco local y el cron dejaron de pushear**: corrían `scrapers.py`, cuyo `ScraperBencina` **regenera `bencinas.json` desde el agregador** (`descuentosrata.com`) → volvía a Shell=sábado sin `confianza` → el guard fallaba → el health check (gate del refresco) abortaba el push. Efecto: producción quedó "congelada" (la curación se salvó porque el push nunca ocurría) pero **NADA se actualizaba** (restaurantes, precios) y llegaba un mail de error diario. Se detectó porque el refresco corrió durante una sesión y `origin` no avanzó pese a haber cambios en el working tree.

**Causa raíz**
La curación vivía en DOS lugares desalineados: el DATO curado (en el JSON, manual) y un GUARD que lo exige (en el health check), pero el GENERADOR (el scraper) seguía produciendo la data vieja del agregador. Un guard NO arregla al generador: solo detecta la discrepancia. Cuando el generador y el guard se contradicen, el guard —bien puesto— bloquea el pipeline entero. Es primo de L-30/L-31/L-32: una curación/decisión que el pipeline automático revierte, pero acá el síntoma es un DEADLOCK (el guard, correctamente, no deja pasar la data mala).

**Fix**
`guardar_bencinas_json` ahora **PRESERVA los descuentos ya curados** del `bencinas.json` existente (lee el archivo y conserva su `descuentos`), en vez de escribir los del scrape del agregador; solo `estaciones`/`precios` se actualizan desde la CNE (fuente oficial). Así el generador produce data consistente con el guard: el health check pasa y el pipeline se desbloquea, con la curación intacta. (+ se agregó el `import os` que faltaba). Verificado: preserva 31 descuentos (Shell=jueves, `confianza` intactos), `verificar_salud.py` exit 0.

**Lección**
Cuando curas un dato a mano y lo proteges con un guard, TIENES que arreglar también el **generador** que lo produce (que preserve o produzca el dato curado), o el generador y el guard entrarán en deadlock y bloquearán el pipeline. La curación debe vivir en el CÓDIGO que genera el artefacto (chokepoint), no solo en el dato + un guard que lo defiende. Un dato "curado" que un scraper regenera cada corrida no está curado: está a un `git add` de perderse (o, con guard, de trabar todo).

**Evitar a futuro**
- Al curar a mano un artefacto que un cron regenera: preguntar SIEMPRE "¿qué proceso reescribe este archivo?" y hacer que ese proceso preserve/produzca lo curado (L-31/L-32). Un guard es la red, no la solución.
- Un cron que "no pushea" pese a tener cambios en el working tree = health check fallando → revisar el gate, no asumir "no había cambios" (L-W20: ¿corrió? ≠ ¿insertó/pusheó?).
- `import` faltante que solo revienta en runtime: `py_compile` NO lo atrapa (solo sintaxis); probar la función en vivo (L-13).

---

### L-39 · Un bot de lógica única sirve varios canales con un adaptador delgado (2026-08-04) · Integraciones / Bot

**Problema**
El bot de descuentos (menú guiado) vivía solo en WhatsApp (Twilio). Se quiso agregar Telegram para probarlo, sin duplicar la lógica ni mantener dos bots.

**Fix**
Endpoint `/telegram` que reusa el MISMO `procesar_comando_whatsapp` (menú + datos locales, sin OpenAI). Solo cambia:
- **Transporte:** Telegram entrega un `update` JSON (`message.chat.id` + `text`) y se responde vía `api.telegram.org/bot<token>/sendMessage`; WhatsApp usa TwiML de Twilio.
- **Formato por canal:** WhatsApp RENDERIZA `*negrita*` y `_itálica_`; Telegram, en texto plano, los muestra LITERALES → se strippean (`replace('*','').replace('_','')`) antes de enviar. (Alternativa `parse_mode`, pero un `*`/`_` desbalanceado en los datos da error 400 → strippear es más robusto.)
- **Estado por usuario:** `user_flow[usuario]` con prefijo `tg_<chat_id>` para no mezclar el flujo de Telegram con el de WhatsApp (misma persona, canales distintos).
- **Opt-in + auto-registro:** el endpoint es inerte sin `TELEGRAM_BOT_TOKEN`; al setearlo, el arranque auto-registra el webhook (`setWebhook` a `RENDER_EXTERNAL_URL`/`TELEGRAM_WEBHOOK_URL`).

**Lección**
Para llevar un bot a un 2º/3º canal, NO dupliques la lógica: extrae el "cerebro" (función que recibe texto+usuario y devuelve texto) y escribe un adaptador delgado por canal (transporte + formato). El resto es el mismo. Prefija el estado por (canal, usuario).

**Evitar a futuro**
- El markdown de un canal NO sirve en otro: WhatsApp `*_` ≠ Telegram (texto plano los muestra literales; MarkdownV2 exige escapar). Strippear o adaptar por canal.
- Estado conversacional keyed por (canal, usuario), no solo usuario.
- Endpoint de cada canal opt-in por su token → desplegar sin romper aunque no esté configurado.

---

### L-40 · Auditar la DATA curada con un agente independiente (2026-08-04) · Datos y calidad / Meta

**Problema**
Tras agregar cuotas + otros al bot, Fernando pidió "pon un agente que vea todo y compruebe punto a punto, coherente y consistente". Un agente auditor independiente (el que construye NO es el que revisa) encontró errores que ni el código ni yo veíamos.

**Hallazgos que el código no atrapaba**
- `Proyecta Energía` (otros, Santander) mostraba **"90% dcto."** siendo **financiamiento** de paneles solares (CAE 1,53%) — el MISMO patrón del CAE (L-34), pero colado en la data CURADA (`beneficios_otros.json`), no en el scraper. El fix de L-34 vive en el scraper; este registro venía de la curación → el guard del scraper no lo tocó.
- Un beneficio de Consorcio con `restaurante` = la descripción ("40% dcto. en masajes…") en vez de un nombre.
- Ripley con la región (`ubicacion`) mal asignada en ≥7/72 (afecta filtro/mapa).

**Lección**
El fix de un patrón en el CÓDIGO (scraper) NO limpia los datos ya CURADOS a mano: hay que auditar la data en reposo también. Un agente independiente que revisa "punto por punto" pilla financiamientos disfrazados de descuento, campos semánticamente mal y regiones equivocadas que un `py_compile` o un filtro nunca ven. Es L-19/L-34 aplicado a la data curada + el patrón "el que construye no revisa".

**Evitar a futuro**
- Cuando arregles un patrón en el scraper (ej. CAE, L-34), **barrer también los datasets curados** por el mismo patrón.
- Antes de dar por bueno un dataset de cara al usuario, pasarle un audit independiente (agente) que mida consistencia interna + errores evidentes.
- Los hallazgos que no se arreglan en el momento (Ripley región, cuotas vencidas) van al ROADMAP como pendientes explícitos, no se pierden.

---

## 🎯 Lecciones candidatas a documentar (detectadas durante migración)

Al revisar la documentación existente del proyecto, hay observaciones que podrían formalizarse como lecciones L-XX en futuras sesiones:

1. **Pinecone vs pgvector**: el proyecto usa Pinecone (legacy) cuando el estándar del workspace es pgvector con HNSW. Documentar por qué se quedó en Pinecone y qué costaría migrar.
2. **Monolito intencional en `api.py`**: 1586 líneas mezclando API + página web HTML embebido + webhook WhatsApp. Documentar trade-off (deploy simple vs mantenibilidad).
3. **15 clases scraper independientes**: cuando un banco cambia su sitio, romper aislado. Patrón replicable para otros agregadores.
4. **Estado conversacional en memoria** (`user_flow = {}` en `api.py`): se pierde con cada restart de Render. Documentar si es aceptable o requiere persistencia.
5. **Coordenadas aproximadas por región** en el mapa: decisión deliberada (no geocoding real). Documentar.
6. **Componente extra de combustibles** (`bencinas.json`, `06_precios_combustible.html`): aparece en la docs natural pero no en el README técnico. Documentar su estado.

---

## 🔄 Cómo agregar una nueva lección

Al cerrar sesión, preguntarse:

1. ¿Hubo un **error no obvio** que tomó tiempo diagnosticar?
2. ¿Encontré un **workaround** para una limitación de herramienta/API/servicio?
3. ¿Tomé una **decisión arquitectónica importante** (por qué X y no Y)?
4. ¿Descubrí un **patrón que funciona** y debe repetirse?
5. ¿Confirmé un **anti-patrón** (esto NO funciona, probado)?
6. ¿Logré una **mejora de performance significativa** (x10 o más)?
7. ¿Aprendí algo sobre el **dominio de negocio** (descuentos bancarios chilenos)?

Si sí → escribir lección con formato de abajo.

---

## 🎓 Plantilla para copiar

```markdown
### L-XX · [Título corto] (YYYY-MM-DD) · [Categoría]

**Problema**
[...]

**Causa raíz**
[...]

**Fix**
[...]

**Lección**
[...]

**Evitar a futuro**
[...]
```

---

**Contador:** 40 lecciones formalizadas (L-01 a L-40; 6 candidatas legacy aún pendientes)
**Última lección agregada:** L-40 (2026-08-04)
**Última actualización:** 2026-08-04

> **Candidata a promover a workspace (L-W):** L-15 (geo-fence del runner) y L-16 (preservar banco caído + alerta) aplican a cualquier scraper agregador del workspace (02.Compras_Mayoristas, 03.Compras_supermercado). L-16 refuerza la regla cardinal **L-W20** ("proceso estéril") con un patrón concreto a nivel sub-fuente.

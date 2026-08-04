# TUNING_PAGINAS.md — Fine-tuning operativo de las páginas de MiCartera

> **Qué es:** el catálogo de TODOS los errores que aparecieron de cara al usuario en las
> páginas (`/ver`, `/ver/beneficios`, `/ver/bencinas`, `/ver/cuotas`) y en los scrapers que
> las alimentan, con **síntoma → causa → fix → cómo evitarlo**. Es fine-tuning OPERATIVO: se
> actualiza cada vez que se toca una página. Complementa `LECCIONES_APRENDIDAS.md`
> (desarrollo); aquí vive lo que se ROMPE de cara al usuario y cómo no repetirlo.
>
> **Cómo usarlo:** ANTES de tocar una página, leer su sección + los patrones raíz.
> DESPUÉS de arreglar un bug de página, agregar la entrada aquí.
> Última actualización: 2026-08-03.

---

## 🔴 Los 4 patrones raíz (los que MÁS se repiten — revisar siempre)

1. **"El dato existe pero no se muestra".** Un filtro o la búsqueda comparan un campo que
   puede venir vacío (`ubicacion`, `comuna`, `presencial/online`) y **excluyen el vacío en
   silencio** → esconden ofertas reales. **Regla: un filtro sobre un campo opcional deja
   PASAR el vacío ("aplica siempre"), no lo excluye.** (L-06, L-19, L-28)
2. **200 ≠ funciona.** La página responde HTTP 200 pero el `<script>` está roto (una
   comilla en el f-string) y no renderiza nada. **Regla: verificar el `<script>` con
   `node --check`, no solo el código HTTP.** (L-13, L-21)
3. **Dato faltante en la fuente → NUNCA inventar.** Etiqueta honesta ("Beneficio
   exclusivo") o recuperar de un **campo hermano** (el % de Consorcio, el nombre de
   Falabella en el slug). Jamás un 0% falso, un pin inventado o un nombre a dedo. (L-14, L-19)
4. **Verificar MIDIENDO.** Reproducir el bug en la data real / el navegador antes de tocar
   lógica. "No aparece X" → pregunta 1 es "¿el dato existe?", no "¿el filtro falla?". (L-06)
5. **Trazabilidad: la data de cara al usuario viene de fuente OFICIAL marcada.** Un agregador
   es control de calidad, NO fuente (se desactualiza y comete errores). Cada dato lleva
   `url_fuente` + `confianza`; la guardia de madrugada lo vigila SIEMPRE. Si no hay dato
   chequeado → **"estamos confirmando descuentos"**, nunca mostrar lo dudoso. (L-24, L-33, L-35)
6. **Filtros dinámicos.** Al fijar un eje (banco), los otros (día/comuna/%) recalculan sus
   opciones y **atenúan/bloquean** las sin resultados, en vez de dejarlas devolver vacío. Es
   el complemento activo de #1. (L-36)

---

## 📄 Página `/ver` — lista + mapa de restaurantes

### Filtros
| Síntoma | Causa | Fix | Evitar |
|---|---|---|---|
| Falabella + un día → "no sale nada" en el **Mapa** | Las ofertas sin local fijo (277, aplican en toda la cadena) no tienen pin; el mapa solo dibuja las que tienen `ubicacion`/`direccion` | Mostrarlas como **tarjetas debajo del mapa** (`dealCardHTML` + `#mapCards`), no solo un aviso | Toda vista que filtre por ubicación necesita un plan para las ofertas sin local fijo |
| Filtro **Modalidad** ("Presencial"/"Online") esconde 222 ofertas (Banco de Chile 200) | `presencial=False` Y `online=False` (sin flag) → no matchean ningún modo salvo "Todas" | `(mode==='presencial' && (d.presencial\|\|!d.online))` — presencial incluye las indeterminadas | Un flag booleano ausente ≠ false semántico; el filtro debe contemplar el "sin dato" |
| Filtro **Zona/Región** borra 277 ofertas nacionales | `regions.includes(d.ubicacion)` con `ubicacion=''` → nunca matchea | `!regions \|\| !d.ubicacion \|\| regions.includes(...)` — sin ubicación = nacional = pasa | Patrón raíz #1 |
| "No aparece el descuento Y" | Casi siempre **gap de datos**, no bug de filtro | Verificar la data cruda filtrando por la condición exacta ANTES de tocar el filtro | Patrón raíz #4 (L-06) |
| Un banco solo tiene descuentos L-V pero sábado/domingo se pueden elegir → devuelven vacío | Filtros **estáticos**: cada control ofrece todo el universo sin mirar los otros filtros | **Faceteado dinámico**: tras cada cambio, recalcular `_base` (todos los filtros menos el eje pintado) y marcar `.day-off`/`.ms-off`/`.cat-off` (atenuado + `pointer-events:none`) las opciones sin resultados | Patrón raíz #6 (L-36). Cobertura: `/ver` y `/ver/beneficios` → día + **región + comuna**; `/ver/bencinas` → día; `/ver/cuotas` → **categorías** (atenúa las sin campañas del mes+banco) |

### Búsqueda
| Síntoma | Causa | Fix | Evitar |
|---|---|---|---|
| Buscar por comuna ("Providencia", "Ñuñoa") → resultados incompletos | El `txt` de búsqueda indexaba restaurante+banco+descripción+ubicación+dirección pero **NO `comuna` ni `tags`** (donde vive la geografía) | Agregar `d.comuna` + `(d.tags\|\|[]).join(' ')` al `txt` (las 3 vistas). Medido: providencia 41→75 | Al armar un índice de búsqueda, incluir TODOS los campos donde el usuario esperaría encontrar algo |
| El bot / API no encuentra un restaurante por nombre | `buscar_beneficios` miraba solo `b.restaurante`, y 93 locales tienen nombre genérico | Buscar en nombre+descripción+comuna+tags, sin tildes (`translate`) | — |
| Palabras cortas ("as") matchean de más ("casa") | `includes()` substring sin límite de palabra | Aceptable en MVP; si molesta, límites de palabra | — |

### Mapa
- Coordenadas **aproximadas por región**, no geocoding real por dirección (decisión deliberada).
- **NUNCA inventar pins** para ofertas sin ubicación real: confunde sobre dónde aplica (L-19).

### JS / render (terreno minado — L-21)
| Síntoma | Causa | Fix |
|---|---|---|
| Página carga (200) pero **no renderiza nada** | Una comilla mal escapada en el f-string cierra un string JS → error de sintaxis → TODO el `<script>` muere | Validar con `node --check` el `<script>` tras cada edición del HTML/JS de `api.py` |
| — | `onclick="..."` inline con 3 niveles de comillas anidadas | Usar `id` + `.onclick`/`addEventListener` en JS puro, no inline |
| Mutación silenciosa | `d.dias_validos.sort()` muta el array compartido del deal en render | `[...d.dias_validos].sort()` |
| Recordatorio | JS embebido en f-string: `{{` `}}` para llaves literales, `${{...}}` para interpolar | — |

---

## 🎁 Página `/ver/beneficios` — Otros beneficios (retail, viajes, salud, entretención)

> Apartado NUEVO (ago-2026), SEPARADO de restaurantes. Descuentos "por debajo" con tarjeta
> que no son restaurante/bencina/cuota. **Dataset propio `beneficios_otros.json`** (campo
> `seccion="otro"`), misma lógica filtrable que `/ver`. El apartado `/ver` NO se tocó.

| Síntoma | Causa | Fix | Evitar |
|---|---|---|---|
| "Bip Solar" Santander mostraba **54% de descuento** (irreal) | Regex laxo `(\d+)\s*%` sobre la descripción cruda leía el **CAE 1,54%** del financiamiento como si fuera descuento | Excluir la frase del CAE (`re.sub(r'CAE[^.]*','')`) + exigir solo % de 1-2 dígitos sin decimal/dígito previo (`(?<![\d,])(\d{1,2})\s*%`) | Un número junto a "CAE"/"tasa" es financiamiento, NO descuento (L-34) |
| "Salen solo 2 bancos, hay muchos" | Solo Santander/Consorcio traían la sección "otros"; el resto aún no curado | Se muestran los **24 verificables** (con % real); faltan ~12 bancos por curar | No inflar con datos sin % real ("si no está chequeado, mejor no mostrar") |
| 228 candidatos → 24 mostrados | ~204 eran financiamiento/servicios/CAE sin descuento % real | Filtrar a `descuento_valor>0` verificable | Patrón raíz #3/#5 — no mostrar lo no chequeado |
| Días sin resultados seleccionables | Filtros estáticos | Faceteado dinámico (`.day-off`), igual que `/ver` | Patrón raíz #6 (L-36) |

**Cómo se separan las secciones:** `scrapers.py` etiqueta cada `Beneficio` con `seccion`
("restaurante"/"otro"); el orquestador parte las dos y guarda `beneficios_otros.json` aparte;
`api.py` usa `_render_deals()` reusable + dos endpoints finos `/ver` y `/ver/beneficios`. Así
el apartado nuevo NO toca el pipeline de restaurantes (pisos, red de seguridad, health check). (L-31, L-32)

---

## ⛽ Página `/ver/bencinas`
- ⚠️ **Trazabilidad (ago-2026):** los descuentos venían 100% de un **agregador** (descuentosrata.com)
  con **5 errores reales** → re-curados desde **fuente oficial** (Copec `ww2.copec.cl`) + medios
  verificados (Aramco/Shell). Correcciones: **Shell/Scotiabank es JUEVES, no sábado**; Itaú martes;
  BancoEstado martes $50; BCI 7% cashback; Santander Consumer vie-dom. Cada dato con `confianza` +
  `url_fuente`; la web marca la procedencia. **Pendiente:** re-curar Shell/Aramco desde sus apps
  oficiales (hoy medios; solo Copec es oficial). (L-33, L-35)
- El guard de la guardia **falla** si un descuento de bencina pierde `confianza` o vuelve al agregador.
- "No sale el descuento X un día" → verificar primero si es **gap de datos**, el filtro suele estar bien (L-06).
- Logos: **no hotlinkear** Wikimedia/Google (dan 400) → self-hostear en `static/logos/` (L-05).
- Montos por tier tras SPA no parseable → mantener con caveat, no adivinar (L-06/decisión).

---

## 💳 Página `/ver/cuotas`
- Datos **curados mensual + trazables** (link oficial por campaña), NO scraper automático (frágil, L-24).
- Distinguir **0% real vs tasa preferencial** (automotriz/educación casi nunca son 0%) — el error que más engaña (L-24).
- Leer las fuentes oficiales con `curl` UA-curl **desde Chile** (el fetch remoto da 403/WAF) (L-24/L-08).
- El correo avisa **desfase de mes** automáticamente; la curación la hace un humano al ver el aviso.
- Al re-curar: **barrer SIEMPRE los 14 bancos** yo, sin pedir links a Fernando (memoria).

---

## 🕷️ Scrapers (alimentan las páginas — un banco = una clase aislada)
| Síntoma | Causa | Fix | Lección |
|---|---|---|---|
| Un banco a 0 en el cron pero OK local | Playwright sin Chromium en Render/CI | Reescribir con `requests` sobre el HTML SSR | L-01 |
| Datos no están en el HTML clásico | Sitio Next.js: datos en RSC escapado | `requests` + brace-matching en un marcador estable | L-02 |
| 403 del sitio | WAF Akamai bloquea UA de browser, deja pasar `curl/8.4.0` | UA curl antes de pensar en un browser service | L-08 |
| Banco cae a 0 sin cambio de código | Geo-fence del runner USA | Scrapear desde Chile (refresco local) + preservar el previo | L-15/L-16 |
| Nombre genérico ("Dcto en Restaurante", Falabella) | El scraper usa `title` genérico; el nombre real vive en el **slug del link** | `_nombre_desde_slug()` cuando el título es genérico (recuperar, no inventar) | L-19, sesión 29-jul |
| Card basura `restaurante=''` | `dict.get(k, default)` NO aplica el default si el valor existe pero es `''` | Cadena `a or b or c` + descartar | L-10 |
| ids duplicados | Slug del nombre colisiona | Disambiguar `_2/_3`, no borrar; global en el orquestador | L-11/L-18 |
| Mojibake (`PlÃ¢ce`) en Windows | `response.text` adivina mal el encoding | `response.encoding='utf-8'` explícito | L-18 |
| Días con tilde no matchean el filtro | Cada scraper mapea días a su modo | Normalizar `dias_validos` en `__post_init__` (chokepoint único) | L-14/L-28 |
| Card muda (sin `descuento_texto`) | La fuente no expone % | Recuperar campo hermano; si no hay, "Beneficio exclusivo" en `__post_init__` | L-14 |

---

## ✅ Checklist antes de pushear un cambio de página
1. `python -m py_compile api.py scrapers.py`
2. **`node --check` del `<script>`** de la vista tocada (guard L-21) — 200 no basta.
3. `python verificar_salud.py` → `exit 0`.
4. **Reproducir el cambio MIDIENDO** en la data real / navegador (no asumir).
5. **Commitear y pushear PRONTO** ⚠️ — el refresco local hace `git reset --hard origin/main`
   y **borra lo no commiteado** (pasó el 29-jul: se perdieron 4 fixes). No dejes trabajo
   sin commitear entre pasos.
6. Verificar en **producción** tras el deploy (curl + reproducir el caso).

---

## 🤖 Bot (WhatsApp + Telegram) — menú guiado, sin LLM

> El bot (`procesar_comando_whatsapp` en `api.py`) es **menú-guiado, sin OpenAI → gratis**.
> Sirve DOS canales con la misma lógica: WhatsApp (Twilio, `/webhook`) y Telegram (`/telegram`).
> 4 opciones: **1** Restaurantes (día→banco) · **2** Bencinas (día) · **3** Cuotas sin interés
> (banco, sin día) · **4** Otros beneficios (banco, sin día). Handler unificado `ask_banco_generico`.

| Síntoma | Causa | Fix | Lección |
|---|---|---|---|
| En Telegram salen `*` y `_` literales | El bot usa markdown de WhatsApp; a Telegram se manda texto plano → se ven los símbolos | Strippear `*`/`_` antes de enviar a Telegram (`replace`); NO usar `parse_mode` (un símbolo desbalanceado en los datos da error 400) | L-39 |
| El bot "no responde" pese a estar vivo | El webhook del proveedor (Sandbox Twilio) apuntaba a **otro servicio** | Verificar en la consola del proveedor a qué URL apunta REALMENTE + confirmar en los logs del destino (¿llega el POST? ¿200/403?) | L-38 |
| Un dato dudoso que reporta el usuario (ej. Scotiabank "3,6,12" cuotas, real "3 y 6") | Curación con un valor equivocado | Leer la **página oficial del banco** y corregir; el usuario que conoce el producto es la mejor red de seguridad | L-19/L-35 |
| ¿Preguntas abiertas? | El bot no tiene LLM (a propósito, para ser gratis) | Decisión: queda menú-guiado. Para abrir: conectar al RAG (OpenAI) — costo por pregunta, requiere OK | L-20 |

**Al agregar un canal nuevo:** extraer el "cerebro" (texto+usuario→texto) y escribir un adaptador
delgado (transporte + formato por canal); prefijar el estado por canal (`tg_<id>`); endpoint
opt-in por su token; auto-registrar el webhook en el arranque. (L-39)

---

## 🌙 Guardia automática — `revision_madrugada.py`
Cada madrugada (~03:00 Chile, workflow `revision_madrugada.yml`) se convierte CADA bug de
este doc en un **check automático** contra producción (curl + `node --check`) + la data, y
se manda **correo SOLO si algo reaparece**. Es este fine-tuning hecho código (patrón L-07:
cada bug resuelto → un guard permanente). Es "el agente que revisa que todo esté bien
siempre" (pedido de Fernando). Cubre: página viva + JS sano (L-13/L-21), seguridad
(`/scrape`→404, `/rag`→403), nombres reales (L-29), no-vacíos (L-10/L-14), ids únicos (L-11),
búsqueda por comuna y filtro de modalidad (L-28), no-colapso (L-16) y **trazabilidad**
(bencina con `confianza` y sin agregador; otros beneficios de fuente oficial — L-33/L-35).
Correrlo a mano: GitHub Actions → "Revisión Madrugada" → Run workflow.
**Al agregar un bug nuevo a este doc, agregar también su guard en `revision_madrugada.py`.**

---
_Este doc es fine-tuning operativo (evoluciona con cada corrida). Lo de desarrollo va en
`LECCIONES_APRENDIDAS.md`; lo cross-project sube a `Claude_code/LECCIONES.md` y al global._

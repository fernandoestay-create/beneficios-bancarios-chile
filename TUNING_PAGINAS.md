# TUNING_PAGINAS.md — Fine-tuning operativo de las páginas de MiCartera

> **Qué es:** el catálogo de TODOS los errores que aparecieron de cara al usuario en las
> páginas (`/ver`, `/ver/bencinas`, `/ver/cuotas`) y en los scrapers que las alimentan,
> con **síntoma → causa → fix → cómo evitarlo**. Es fine-tuning OPERATIVO: se actualiza
> cada vez que se toca una página. Complementa `LECCIONES_APRENDIDAS.md` (desarrollo);
> aquí vive lo que se ROMPE de cara al usuario y cómo no repetirlo.
>
> **Cómo usarlo:** ANTES de tocar una página, leer su sección + los patrones raíz.
> DESPUÉS de arreglar un bug de página, agregar la entrada aquí.
> Última actualización: 2026-07-29.

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

---

## 📄 Página `/ver` — lista + mapa de restaurantes

### Filtros
| Síntoma | Causa | Fix | Evitar |
|---|---|---|---|
| Falabella + un día → "no sale nada" en el **Mapa** | Las ofertas sin local fijo (277, aplican en toda la cadena) no tienen pin; el mapa solo dibuja las que tienen `ubicacion`/`direccion` | Mostrarlas como **tarjetas debajo del mapa** (`dealCardHTML` + `#mapCards`), no solo un aviso | Toda vista que filtre por ubicación necesita un plan para las ofertas sin local fijo |
| Filtro **Modalidad** ("Presencial"/"Online") esconde 222 ofertas (Banco de Chile 200) | `presencial=False` Y `online=False` (sin flag) → no matchean ningún modo salvo "Todas" | `(mode==='presencial' && (d.presencial\|\|!d.online))` — presencial incluye las indeterminadas | Un flag booleano ausente ≠ false semántico; el filtro debe contemplar el "sin dato" |
| Filtro **Zona/Región** borra 277 ofertas nacionales | `regions.includes(d.ubicacion)` con `ubicacion=''` → nunca matchea | `!regions \|\| !d.ubicacion \|\| regions.includes(...)` — sin ubicación = nacional = pasa | Patrón raíz #1 |
| "No aparece el descuento Y" | Casi siempre **gap de datos**, no bug de filtro | Verificar la data cruda filtrando por la condición exacta ANTES de tocar el filtro | Patrón raíz #4 (L-06) |

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

## ⛽ Página `/ver/bencinas`
- "No sale el descuento Scotiabank sábado" → era **gap de datos**, el filtro por día estaba bien (L-06).
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
_Este doc es fine-tuning operativo (evoluciona con cada corrida). Lo de desarrollo va en
`LECCIONES_APRENDIDAS.md`; lo cross-project sube a `Claude_code/LECCIONES.md` y al global._

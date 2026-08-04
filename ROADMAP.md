# Roadmap — MiCartera (Scrapers + Bot descuentos)

> Estado real del proyecto. Se actualiza después de cada sesión de trabajo.
> Última actualización: 2026-08-04

## ✅ Hecho (sesión 2026-08-04 — cont.: cuotas a agosto + "Otros" ampliado a 212 + audit de datos)

Continuación de la sesión del bot, frente **datos y calidad**:
- **Cuotas re-curadas a AGOSTO** (v2.2): 11/14 bancos vigentes/cubriendo agosto vía webs oficiales desde Chile (9 `oficial-verificada`); Santander preciso (1-31 ago, CAE 1,19%). Tenpo marcado honesto (junio vencida). `mes_referencia`→agosto. Verificado en `/ver/cuotas`.
- **"Otros beneficios" ampliado 24 → 638 verificables (7 bancos):** flips **L-32** de **BCI** (+172, `ca07c4b`), **Lider BCI** (+17, `8a1b0e3`), **Banco de Chile** (+359, `7c8c93b`), **Entel** (+49) y **Tenpo** (+18, `0b851ef`). BCI/Lider/Entel/Tenpo: sus fuentes ya traían todo y lo botaban (API CMS, tabs de la página, Webflow CMS). Banco de Chile: se quitó su filtro `meta.category` y se clasifica por categoría (salud/belleza/deportes/óptica…). Trampas **L-34** manejadas (Lider "$100"=monto≠100%, cuotas excluidas); parsers con regex `%` estricto. **Restaurantes SIEMPRE intactos** — **GATE verificado en CADA banco: el set de restaurantes queda con IDs IDÉNTICOS** (BdChile 249, Entel 28, Tenpo 7) → `/ver` no cambia (898/14). `beneficios.json` NUNCA tocado. Verificado en prod: BdChile 359 + BCI 172 + Entel 49 + Santander 21 + Lider 17 + Tenpo 18 + Consorcio 2 = **638**.
- **Filtro de calidad DURABLE en el render** (no en el dato): `%>0` + anti-financiamiento (**L-40/L-41**) — sobrevive re-scrapes.
- **Audit de datos con agente independiente (L-40):** removido "Proyecta Energía" (financiamiento 90% CAE colado como % dcto.); Ripley región corregida (`849b708`, `_region_desde_direccion` + `_COMUNA_REGION`, 8 registros); Consorcio "Masajes" (nombre = descripción).
- Lecciones **L-40, L-41**. Tags **`v2.2`→`v2.5`** (`cuotas-otros-audit`, `lider-otros`, `bancochile-otros`, `entel-tenpo-otros`).

## ✅ Hecho (sesión 2026-08-04 — pipeline desbloqueado + bot multicanal (WhatsApp+Telegram) + 4 opciones + firma Twilio)

Sesión grande de infra + bot:
- **Pipeline de datos DESBLOQUEADO (L-37):** el cron/refresco fallaban el health check porque `ScraperBencina` regeneraba `bencinas.json` desde el agregador (Shell→sábado) contra el guard `Shell=jueves`. Fix: `guardar_bencinas_json` **preserva los descuentos curados**; solo los precios CNE se actualizan. El cron volvió a pushear (verificado end-to-end, curación intacta).
- **Firma Twilio ACTIVADA + verificada en vivo:** `TWILIO_AUTH_TOKEN` en Render; POST de Twilio → 200, falso → 403. **Hallazgo L-38:** el Sandbox apuntaba a OTRO servicio (`micartera-ttaa`); se re-apuntó a `api-beneficios-chile/webhook`.
- **CANAL TELEGRAM nuevo** (`@Mi_cartera_descuentos_Bot`): endpoint `/telegram` reusa el MISMO bot (menú, **gratis, sin OpenAI**); auto-registra el webhook; opt-in por token. Verificado en vivo (200). (L-39)
- **Bot ampliado a 4 opciones:** 1 Restaurantes · 2 Bencinas · **3 Cuotas sin interés** · **4 Otros beneficios** (cuotas y otros van solo hasta banco, sin día).
- **Filtro "Otros" en código** (`descuento_valor>0`, sobrevive re-scrapes) + **filtros dinámicos extendidos** a región/comuna (`/ver`, `/ver/beneficios`), día (bencinas), categorías (cuotas).
- **RAG revectorizado** (887 vectores en Pinecone, para el buscador de la web).
- **Doc accesible HTML** actualizada + nav rotos arreglados; **respaldo total en GitHub** (docs de gestión que vivían solo en Drive).
- **Fixes:** Scotiabank cuotas "3,6,12"→**"3 y 6"** (verificado en la web oficial, L-35); Telegram sin markdown literal (L-39).
- **Decisión:** el bot **NO lleva LLM por ahora** (menú-guiado, gratis).
- Lecciones **L-37, L-38, L-39**. Tag: **`v2.1-bot-multicanal`**.

## ✅ Hecho (sesión 2026-08-03 — parte final: trazabilidad, filtros dinámicos y apartado completado)

Cierre real de la sesión que arrancó el 29-jul: el apartado "Otros beneficios" pasó de "pantalla en curso" a **desplegado**, se auditó la trazabilidad de los 4 datasets de cara al usuario y se re-curó la bencina desde la fuente oficial.

- **Apartado "Otros beneficios" (`/ver/beneficios`) DESPLEGADO:** filtrado a **24 beneficios verificables** (de los 228 capturados de Santander/Consorcio) — solo quedan los que tienen un % de descuento real y chequeable; los 204 restantes (financiamiento, servicios, CAE) no se muestran, siguiendo la regla "si no está chequeado, no mostrar" (L-33/L-35). Mismo dataset separado `beneficios_otros.json`, misma lógica de filtros que `/ver`. El apartado de restaurantes `/ver` quedó intacto.
- **Bug del % del CAE corregido (L-34):** un regex laxo `(\d+)\s*%` sobre la descripción cruda capturaba el CAE del financiamiento como si fuera un descuento (Bip Solar de Santander mostraba "54% dcto." cuando en realidad era el CAE del crédito, 1,54%). Fix: excluir la frase del CAE del texto antes de buscar + regex estricto de 1-2 dígitos no decimal.
- **Auditoría de TRAZABILIDAD de los 4 datasets (L-33):** medido el dominio de `url_fuente` por dataset (no asumido) — restaurantes (887), otros (24) y cuotas (28) → **100% oficial**; bencina-descuentos (31) era **100% agregador** (descuentosrata.com), lo que explicaba desfases que nadie había notado.
- **Bencina RE-CURADA desde fuente oficial (L-35):** Copec (15 descuentos) leído directo de `ww2.copec.cl/personas/promociones`; Aramco/Shell (16) desde medios verificados. Campo nuevo **`confianza`** por dato ("oficial" vs "secundaria") + `url_fuente` oficial por cadena. **5 errores del agregador corregidos:** Shell/Scotiabank sábado→**jueves**, Itaú Copec viernes→**martes**, BancoEstado viernes $100→**martes $50**, BCI $100/L→**7% cashback tope $7.000**, Santander Consumer lun-vie→**vie-dom**.
- **Guardia de madrugada ampliada a trazabilidad:** `revision_madrugada.py` ahora también vigila que ningún dato pierda su `confianza` ni vuelva a depender solo del agregador — alerta si reaparece.
- **Filtros DINÁMICOS de día** en `/ver` y `/ver/beneficios`: los días sin resultados según el banco se atenúan/bloquean en vez de mostrar una lista vacía sin explicación. + mensaje **"Estamos confirmando los descuentos"** cuando una sección todavía no tiene data chequeada.
- Lecciones nuevas **L-33, L-34, L-35**. Tags **`v1.9-otros-beneficios`** (apartado desplegado) y **`v2.0-otros-trazabilidad-filtros`** (trazabilidad + filtros dinámicos).

## ✅ Hecho (sesión 2026-08-03 — guardia de madrugada + apartado "Otros beneficios")

Sesión con tres frentes: blindar la vigilancia con un check determinista, cerrar el caso Falabella (local + trazabilidad) y **abrir un apartado nuevo** para los beneficios no-restaurante que se estaban botando. Todo verificado y en producción salvo la pantalla del apartado nuevo, que en este punto de la sesión seguía en curso — **se terminó y desplegó más tarde, en la parte final de esta misma sesión** (ver bloque de arriba).

- **Guardia de madrugada** (`2696af9`): `revision_madrugada.py` + workflow (cron **03:00 Chile**) convierte **cada bug conocido en un check automático** contra producción + data; manda correo **solo si algo reaparece** (fine-tuning hecho código, patrón L-07). **Decisión:** la vigilancia se hace con un **script determinista** (gratis, corre en GitHub Actions), **no con un agente cada madrugada** (caro y frágil) — un check reproducible es más confiable y auditable que un LLM revisando a ciegas.
- **Falabella — local específico + trazabilidad** (`dd62ddc`): se **preserva el mall** en el nombre (Tanta [Mallplaza] ≠ otro Tanta) y se agrega una **restricción trazable consistente** — *"Revisa los locales del beneficio. Comprueba en la página oficial."* — en las **95 ofertas**. **Decisión:** el nombre real vive en el slug del link (L-19), y como Falabella aplica **por local** (no por cadena), se **acota** el alcance y se hace **trazable** en vez de prometer algo que no se puede garantizar.
- **Tarjetas muestran condiciones + link oficial** (`b4d0925`): cada tarjeta muestra sus **condiciones (📋)** + link **"Comprobar en la página"** — el usuario ve la restricción y puede verificar en la fuente.
- **APARTADO NUEVO "Otros beneficios"** (`7ebf2cf` + pantalla en curso): Santander/Consorcio traían beneficios **no-restaurante** (farmacias, transporte, ski, hoteles, retail) que **se botaban** al filtrar solo gastronomía. Ahora se **capturan** con campo `seccion="otro"` en un **dataset SEPARADO** (`beneficios_otros.json`, **228 beneficios**), **sin tocar** `beneficios.json` ni los pisos / la red de seguridad. **Decisión clave:** dataset separado + **no tocar `/ver`** (Fernando: *"el apartado de restaurantes está perfecto, no lo toques"*) + **reusar los scrapers que ya traían el dato** en vez de duplicar lógica — cero riesgo de regresionar el apartado de restaurantes que ya está estable.
- **Respaldo:** tag **`v1.8-estable-pre-beneficios`** como **punto de retorno** antes de abrir el apartado nuevo.
- Commits: `2696af9` (guardia de madrugada) · `dd62ddc` (Falabella local + trazable) · `b4d0925` (tarjetas condiciones + link) · `7ebf2cf` (apartado Otros beneficios) · tag `v1.8-estable-pre-beneficios`.

## ✅ Hecho (sesión 2026-07-29 — auditoría ácida de filtros y búsqueda + seguridad)

Directiva de Fernando: **"Falabella + jueves no sale nada"** en el mapa → derivó en una auditoría ácida completa de los filtros y la búsqueda. Todo verificado con `py_compile` + `node --check` + health check, y desplegado en producción.

- **Bug reportado (mapa):** las ofertas **sin local fijo** (aplican en toda la cadena, ubicación vacía) no tenían pin → "Falabella + jueves" no mostraba nada. Fix: ahora se muestran como **TARJETAS debajo del mapa** en vez de desaparecer. Commit `9b3fd67`.
- **Auditoría ácida de filtros → 5 bugs del patrón "el dato existe pero no se muestra"**, todos arreglados (`9b3fd67`): (#1) el mapa escondía **277 ofertas** sin local fijo; (#2) el filtro **Modalidad** borraba **222 ofertas** con `presencial=online=False` (200 del Banco de Chile); (#3) el filtro **Zona** borraba las **277 ofertas nacionales** (ubicación vacía) al elegir región; (#4) normalización de días en `__post_init__` (preventivo); (#5) mutación de array en el render.
- **Buscador de `/ver` ahora indexa comuna + tags:** buscar "providencia" pasó de **41 → 75** resultados, "ñuñoa" de **8 → 15**. Commit `748571e`.
- **Seguridad (commit `c90eb07`):** eliminados `/scrape/ejecutar` y `/scrape/bencinas` (POST **anónimo destructivo** que borraba 12 bancos de la web); `/rag` con guard `ADMIN_TOKEN` + `max_length=1000` en la pregunta; **CORS restringido** (era `"*"` con `credentials=True`); tokens hardcodeados caducados limpiados; `buscar_beneficios` (API + bot) busca en nombre + descripción + comuna + tags. **PENDIENTE:** validación de firma Twilio en `/webhook` (requiere prueba en vivo del bot, no se aplicó a ciegas).
- **Falabella — nombres reales recuperados:** 95 nombres reales sacados del **slug del `linkUrl`** (Petit, Vapiano, Muu Grill, Tanta, Mamma Mia...) en vez de "Dcto en Restaurante" — el nombre vivía en el slug del link, no en el campo `title`. Commit `d1781d7`.
- **Fine-tuning operativo — `TUNING_PAGINAS.md`** creado: todos los errores/cambios de las páginas registrados. Commit `9b0cf31`.
- **Lección nueva L-28:** un filtro/búsqueda de UI sobre un **campo opcional** debe dejar **PASAR el vacío** ("aplica siempre"), no excluirlo en silencio.
- **Incidente operativo:** el refresco local corrió `git reset --hard origin/main` y **borró 4 fixes sin commitear** → regla reforzada: commitear pronto, no dejar trabajo sin commitear entre pasos.
- Commits: `9b3fd67` (mapa + 5 bugs de filtros) · `748571e` (buscador comuna+tags) · `c90eb07` (seguridad) · `d1781d7` (Falabella nombres) · `9b0cf31` (TUNING_PAGINAS).

## ✅ Hecho (sesión 2026-07-01 — apartado de Cuotas sin interés)

Directiva de Fernando: agregar un apartado de **cuotas sin interés del mes por banco**, desde las **fuentes oficiales** de los bancos (trazable, no copiado de Chócale), enfocado en compras de todos los medios / automotriz / educación / etc.

- **Apartado nuevo `/ver/cuotas`** (botón 💳 en la barra de las 3 páginas): campañas por **banco y categoría** (todos los comercios, automotriz, educación, supermercados, salud, contribuciones), cada una con **condiciones de uso, vigencia y link oficial**. Selector de bancos por **logo** + selector de **mes** + chips de categoría. Distingue **0% real vs tasa preferencial**. Render server-side + JS de filtros validado con `node` (L-21).
- **Datos curados** en `cuotas_sin_interes.json` (14 bancos: 12 con campaña; Ripley/Mach sin campaña tipo). Leídos de las **páginas oficiales desde Chile** con curl UA-curl (donde el WAF lo permite: Santander/Scotiabank/Lider verificadas en vivo; BICE/Itaú bloquean) + **cruce con Chócale como control** de inconsistencias. Enfoque **curado mensual + trazable** (L-24).
- **Correo diario** incluye ahora una sección de cuotas (resumen + las de 0% + botón) con **aviso automático de desfase de mes** (detección diaria del cambio de mes).
- **Scraper de beneficios (restaurantes/bencina) intacto** — las cuotas son un módulo aparte, curado (no scraper automático, porque las fuentes bloquean/son imágenes).
- **Apartado 100% dinámico:** selector de mes (jun→dic, junio como "historia", abre en el mes en curso) + logos de bancos + contadores del hero, TODO filtrado por mes desde `cuotas_sin_interes.json` (nada hardcodeado). Verificado en prod: julio → 6 bancos / 12 campañas / 6 logos; septiembre → 5 logos.
- **Barrido de fuentes oficiales (navegador desde Chile):** **BCI → jul-sep**, **Consorcio → hasta 31-dic** corregidos con dato oficial. Límite real: ~6 bancos (Banco de Chile, Santander, Itaú, BICE, Security, Tenpo) publican en imágenes/SPA no legibles → se mantienen con aviso de desfase; Fernando aporta datos puntuales trazables.
- **Itaú** bajó de 71 a ~23 restaurantes (real, no bug — su Ruta Gourmet tiene 23): piso bajado 25→15 para no bloquear el health check; sigue marcado DEGRADADO por el piso relativo.
- Commits: `a5558a0` · `528ab8c` · `33b4aad` · `ee0abad` · `0ebf168` (Itaú) · `c5b766f` (BCI) · `8399ab8`→`8441276` (selector de mes real + logos/contadores dinámicos + junio historia).

## ✅ Hecho (sesión 2026-06-23 — alineación del correo + fix JS)

- **Bug del JS de `/ver`** (aviso del mapa con comillas mal escapadas): la página cargaba pero no renderizaba nada; fix con `id` + `.onclick` en JS puro, validado con `node --check`. Commit `20d10ab`. (L-21)
- **Correo diario alineado a las 09:00 Chile** (`0 13 * * *`) y **refresco local movido a 08:30** para que no choquen los `git push` (L-22). Verificado que todo opera contra el scheduler, no de palabra (L-23).

## ✅ Hecho (sesión 2026-06-22 — auto-monitoreo + resiliencia + aprendizaje)

- Falabella restaurado (era geo-fence del cron USA, no bug — L-15). **Red de seguridad por banco** (preserva el caído en vez de borrarlo — L-16). **Chequeo experto por banco** (OK/DEGRADADO/CAÍDO/PRESERVADO con piso absoluto + relativo — L-17). **Refresco local desde Chile** (Tarea Windows). **Auditoría de credibilidad** de los 14 bancos + Consorcio 50% (L-19). **Mail diario "por sí o por no"**. **Aprendizaje** (`historial.json`, pisos adaptativos, tendencias — L-20). Cron pasado a diario. Lecciones L-15 a L-21.

## ✅ Hecho (sesión 6-cards-completas — 2026-06-02, cierre)

Directiva de Fernando: **"hibrido, termina tod"** sobre la directiva de fondo **"haz todo lo que sea necesario, para dejar operativo, sin redundancia y en su mejor estado"**. Resueltas las 6 cards sin `descuento_texto` con un enfoque **híbrido** (recuperar dato real donde existe, etiqueta genérica donde no) y shippeado (tag `v1.6-cards-completas`).

- **Opción A — Banco Security (recuperar dato real):** `ScraperBancoSecurity._parsear_item` ahora cae a `field_titulo_caluga` (= "Menú Priceless") cuando `descuento_valor == 0`. Verificado **en vivo** (L-13): Security live 86 items, **0 con texto vacío**, las cards sin % muestran "Menú Priceless". 4 cards recuperadas (Tanaka, Capogrossi, Demencia, La Campiña — todas "- Mastercard").
- **Opción B — Itaú + Falabella (etiqueta genérica):** `Beneficio.__post_init__` pone `"Beneficio exclusivo"` si el beneficio queda **sin % y sin texto**. Es un único chokepoint que corre en TODA construcción de `Beneficio` (cron + cleanup) → ninguna card puede volver a renderizar vacía. Cubre `itau_men__priceless_by_mastercard_tarjetaita` (entrada genérica de programa, sin restaurante específico) y `falabella_caoba-bar` (sin % publicado).
- **Cleanup data-at-rest (929):** aplicado sobre data **fresca de origin** (L-04) — 4 Security → "Menú Priceless", round-trip por el **dataclass real** (lossless: 0/923 no-objetivo alteradas, `__post_init__` rellena Itaú/Falabella) + CSV regenerado con `csv.DictWriter` (CRLF intacto: 932 CRLF, 0 LF-solos; diff quirúrgico de 12 líneas). (L-12)
- **Guard nuevo en `verificar_salud.py`** (patrón L-07): **falla** si reaparece cualquier beneficio con `descuento_texto=''`. Health check exit 0 con el guard verde.
- **Verificado:** health check exit 0; `/ver` vía TestClient renderiza 929 beneficios / 14 bancos, "Menú Priceless" y "Beneficio exclusivo" presentes en las cards.
- **Shipped:** commit `0f4811a`, push `dea15cc..0f4811a` en `origin/main`, tag `v1.6-cards-completas`. Render auto-redeployando.

## ✅ Hecho (sesión calidad-100 — 2026-06-02, tarde)

Directiva de Fernando: **"mejora la calidad al 100% — incluir TODO"** + **"haz todo lo que sea necesario, para dejar operativo, sin redundancia y en su mejor estado"**. Se ejecutaron los 4 tiers de hardening y se shippearon (tag `v1.5-calidad-100`).

- **Tier 1 — `verificar_salud.py` blindado**: crash-parity con los **modelos reales** (`Beneficio`/`DescuentoBencina` importados de scrapers.py, mismo `TypeError` que tumba el arranque en Render); pisos de conteo por banco (detecta colapso silencioso tipo Falabella/Santander a 0); guard de mojibake en texto de cara al usuario; **guard de ids duplicados** en beneficios + bencinas. Commit `5dacf92`.
- **Tier 2 — descarte de cards sin nombre en 6 scrapers**: aplicada la cadena `or` + `return None` (patrón L-10, generalización del fix BICE) a los 6 scrapers que podían colar un nombre vacío + fix de un `bare except`. El source se auto-cura en el cron. Commit `5172f98`.
- **Tier 3 — unicidad de ids (disambiguar, no borrar)**: helper idempotente `_asegurar_ids_unicos()` wireado en Ripley/Entel/bencinas; cleanup quirúrgico de la data ya presente (**930→929**: 1 dup exacto `entel_just_burger` dropeado, 2 colisiones Ripley reales suffixadas `_2`) + 7 tier-ids de bencina suffixados `_2/_3`. Cleanup vía **round-trip por el dataclass real** (lossless, `__post_init__` preserva `fecha_scrape`) + CSV regenerado con `csv.DictWriter` (byte-idéntico, CRLF-safe). Commit `53b7f76`. (L-11, L-12)
- **Tier 4 — Itaú + LiderBCI migrados Playwright→requests**: eliminado el browser muerto (condenado a 0 en el cron, L-01). **Verificado en vivo** antes de shippear: `ScraperItau`→68, `ScraperLiderBCI`→11 (el health check prueba data-at-rest, no el fetch, L-13). Commit `f544e75` + fix de comentario stale `dea15cc`.
- **Estado:** 14/15 bancos live (**929 beneficios, 31 bencinas**), health check exit 0, **0 ids duplicados** en ambos archivos, 0 URLs externas. Shipped `bb837b5..dea15cc`, tag `v1.5-calidad-100`, Render redeployando.

## ✅ Hecho (sesión 2026-06-02, mañana)

- **Card basura BICE eliminada (fix durable + cleanup + guard)**: la entrada `Dólares BICE Aplica` con `restaurante=""` se colaba porque `fields.get('Marca', default)` NO aplica el default cuando `Marca=''` (valor presente pero falsy, no key ausente). Fix en `ScraperBICE._parsear_entry`: cadena `or` (`fields.get('Marca') or meta.get('name') or ''`) + `return None` si queda vacío → el source se auto-cura en el próximo cron. Removida la entrada ya presente de `beneficios.json`/`.csv` (931→930, BICE 67→66). Guard nuevo en `verificar_salud.py` (extensión L-07): **falla** si reaparece cualquier beneficio con `restaurante=''`. Verificado: health check exit 0, `/ver` ya no muestra la card, otros 13 bancos sin tocar. Commit `bb837b5`, tag `v1.4-bice-cleanup`. (L-10)
- **Montos Scotiabank sábado verificados (sin cambio de data)**: confirmado contra fuente oficial Scotiabank + La Tercera/medios que el descuento Shell sábado es **hasta $200/L con Visa Crédito vía App Shell, vigente junio 2026** (promo viva, no stale). El techo $200 calza con el tier top de la data. El desglose exacto de tiers inferiores ($150/$100) está tras una SPA no parseable y ningún medio lo contradice → se mantiene `bencinas.json` como está con el caveat documentado. No se tocó producción (cambiar tiers sin fuente autoritativa sería adivinar).
- **Santander desbloqueado sin browser** (objetivo "que salgamos los 15 bancos"): el scraper usaba Playwright (condenado a 0 en el cron de Render, L-01) y aun así el WAF de Akamai bloqueaba. Descubierto que Akamai da **403 a UA de browser/python pero 200 a UA estilo `curl/8.4.0`**, sirviendo el HTML SSR completo (`li.item`). Reescrito `ScraperSantander` Playwright→`requests` reutilizando `_parsear_item` tal cual. Merge quirúrgico sobre data fresca de origin: **854 → 931** (Santander 0 → 77), **13 → 14 bancos**, sin regresionar el resto. Verificado end-to-end (health check exit 0 + `/ver`/`/estadisticas` vía TestClient con startup). Commit `f1eec1a`, tag `v1.3-santander-browserless`. (L-08)
- **BancoEstado investigado y DIFERIDO** (decisión Fernando: D): verificado exhaustivo que la URL de campaña devuelve un **soft-404 de Akamai Edge a TODO cliente, incluso con UA de browser real**, en todos los endpoints AEM (`.model.json`/`.infinity.json`/`jcr:content.json`/`.1.json`). Señal clave: no es solo anti-bot, la **campaña estacional ya no existe** en esa ruta. Opción B descartada; pagar un browser service (C) no sirve hasta que haya campaña viva. Se difiere hasta que BancoEstado relance su mes de sabores. (L-09)
- **Estado 15 bancos:** 14/15 live tras esta sesión. Único faltante: BancoEstado (campaña caída, diferido).

## ✅ Hecho (sesión 2026-06-01, tarde)

- **Fix logos de bancos para producción**: las imágenes no salían porque Wikimedia/Google bloquean hotlink (HTTP 400/403). Self-hosteados 13 logos reales (vía `Special:FilePath`) + 3 badges SVG generados (Internacional, SBPay, SPIN) en `static/logos/`. Ambos `BANK_LOGOS` repuntados a rutas locales → **0 URLs externas**. Alias `Itaú`/`Banco Itaú` agregados (renderizaban como texto en bencinas). Commit `4a281ef`. (L-05)
- **Fix descuento Scotiabank Shell sábado**: faltaba en la data (gap de datos, no bug de filtro — el filtro estaba correcto). Agregado en `scrapers.py` (source → auto-cura) + inyectado en `bencinas.json` sobre data fresca de origin (28 → 31). 3 tiers vía App Shell (ex Mi Copiloto): Singular/Premium $200/L, Signature/Platinum $150/L, Gold $100/L. Commit `07e7789`. (L-06)
- **Mecanismo de comprobación** `verificar_salud.py`: health check estático pre-deploy (logos existen + 0 URLs externas, integridad de beneficios.json + bencinas.json, guard de regresión Scotiabank sábado). Exit 0/1, wireable a CI. Commit `2b22abc`. (L-07)
- **Auditoría de tarjetas**: 13 bancos en restaurantes + 22 en bencinas, **todos con logo mapeado** tras el fix Itaú. Detectada 1 card basura (Banco BICE, "Dólares BICE Aplica", `restaurante=""`) — viene del auto-scraper, reportada (no tocada).
- **Verificación end-to-end** con servidor local: logos sirven HTTP 200 con content-type correcto y bytes exactos; simulando un sábado, `/ver/bencinas` muestra los 3 tiers Scotiabank.
- **Shipped a producción**: `42bfbd2..2b22abc` en `origin/main`, tag `v1.2-imagenes-scotiabank`, Render auto-redeployando.

### Sesión anterior (2026-06-01, mañana) — Falabella
- Reescrito `ScraperBancoFalabella` Playwright → requests/SSR (RSC Next.js). 0 → 86 beneficios. Merge quirúrgico 763 → 849. Commit `42bfbd2`, tag `v1.1-falabella-ssr`. (L-01..L-04)

## 🔄 En progreso / observación

- **Itaú en observación** (desde 1-jul): bajó de 71 a ~23 restaurantes (NO es bug — su Ruta Gourmet tiene solo 23 hoy, sin más páginas). El correo lo marca DEGRADADO correctamente. Esperar a que se estabilice: si recupera (~70) era transición de mes; si sigue en ~23, bajar su piso (25→~15) en `chequeo_bancos.py` → `PISOS_BANCOS`.
- **Cuotas → julio/agosto:** el apartado sigue mostrando meses viejos en ~6 bancos que publican en imágenes/SPA no legibles; se re-cura cuando esos bancos publiquen el mes en curso. El correo avisa el desfase automáticamente.

## ⏳ Pendiente priorizado

1. **Bencina — re-curar Shell/Aramco desde sus apps oficiales** (hoy vienen de medios verificados, no de la fuente primaria; solo Copec es 100% oficial). Objetivo: que los 2 quedan con `confianza="oficial"` como Copec.
2. ~~Extender los filtros dinámicos a región/comuna y a bencinas/cuotas~~ ✅ **HECHO (2026-08-04)**: `/ver` y `/ver/beneficios` atenúan región+comuna; `/ver/bencinas` día; `/ver/cuotas` categorías. (Opcional restante: faceteado del filtro de banco en bencinas.)
3. **Apartado "Otros beneficios" — cubrir más bancos:** hoy solo Santander/Consorcio (24 beneficios verificables mostrados, de 228 capturados). Faltan ~12 bancos: scrapear sus páginas de beneficios generales, mismo enfoque (dataset separado, `seccion="otro"`, filtro de verificabilidad L-33/L-35).
4. **Cuotas — re-curar los bancos que aún muestran meses viejos** (~6 bancos publican en imágenes/SPA no legibles): leer las oficiales desde Chile + cruce con Chócale (L-24) cuando publiquen el mes en curso. La detección de desfase ya avisa sola en el correo. Barrer SIEMPRE los 14.
5. ~~Webhook Twilio — activar la firma~~ ✅ **HECHO (2026-08-04)**: `TWILIO_AUTH_TOKEN` seteado en Render, verificado en vivo (POST Twilio→200, falso→403).

### 🔎 Hallazgos del audit de datos (2026-08-04) — pendientes
6. ~~Cuotas desactualizadas a agosto~~ ✅ **HECHO (2026-08-04)**: re-curadas vía las webs oficiales desde Chile (Chrome). **11/14 bancos vigentes o cubriendo agosto** (9 `oficial-verificada`): Santander (preciso, 1-31 ago, CAE 1,19%), Scotiabank, Banco de Chile, Falabella, Itaú, BCI (hasta sep), BICE (permanente), Security (todos los días); Lider/Consorcio/Entel ya cubrían agosto (hasta dic/permanente). **Tenpo**: campaña de junio vencida, no verificada en agosto → marcado honesto. `mes_referencia`→agosto. Verificado en `/ver/cuotas`.
7. ~~Ripley — región mal asignada~~ ✅ **HECHO (2026-08-04, `849b708`)**: la raíz era que la región salía del texto multi-sede de la card + los numerales romanos colisionaban por substring ("XIV Región"→Valparaíso). Nuevo `_region_desde_direccion()` + `_COMUNA_REGION` (16 regiones) derivan la región desde la ciudad real; 8 registros corregidos (Kunstmann→Los Ríos, etc.).
8. ~~Menores (bencina ids, Security dup)~~ ✅ **HECHO/RESUELTO**: 5 ids de bencina renombrados al día real; el "duplicado" de Security ya no existe (la data cambió). Queda menor: Santander/Contribuciones sin nº de cuotas.
9. **"Otros beneficios" — más bancos:** ✅ **5 bancos agregados (2026-08-04)**: BCI +172, Lider BCI +17, Banco de Chile +359, Entel +49, Tenpo +18 → **638 verificables** (7 bancos en total) en `/ver/beneficios`. Todos flips **L-32** (sus fuentes ya traían todo y lo botaban), con **GATE de restaurantes con IDs idénticos** en cada uno → `/ver` intacto. Filtro durable anti-financiamiento en el render (L-40/L-41). **Pendiente:** **Ripley** (su API se consulta por `idSection=restofans`; las otras secciones se cargan por JS en el SPA → hay que inspeccionar la red con navegador para hallar los `idSection`); **Falabella/Itaú/Scotiabank/Security/Mach** (su fetch está scoped a restaurante → fetch nuevo por banco). Incremental.
10. **Shell/Aramco (bencina) → oficial:** necesita las **apps** de Aramco/Shell (tu teléfono). Copec ya es oficial; los otros quedan "medios verificados". No accesible desde acá.
6. ~~Revectorización RAG~~ ✅ **HECHA (2026-08-04)**: 887 restaurantes re-vectorizados a Pinecone (verificado: 887 vectores en el namespace), costo ~US$0.002. Queda en backlog la **migración Pinecone → pgvector** (estándar del workspace).
7. **Falabella — filtrar ofertas que no son restaurantes:** excluir `app-copec`, `pronto-copec`, `novedades-cmr-puntos` (no son gastronomía).
8. **Itaú:** confirmar si el bajón a ~23 es transición o nivel nuevo; ajustar el piso si es permanente.
9. **BancoEstado** (diferido — revisar cuando relance su campaña de sabores).
10. (Backlog) Curación automática de cuotas: requiere entorno cloud con rutinas (`create_trigger` no viable en sesión local).

## 🧊 Backlog (futuro, sin fecha)

- Unificar las 2 carpetas duplicadas de docs natural (`00.Información_propia_explicación/` vs `00.Informacion_proyecto/`).
- Persistir estado conversacional del bot (`user_flow` hoy en memoria, se pierde con restart de Render).
- Wirear `verificar_salud.py` al build de Render (pre-deploy gate).

## 🐛 Issues conocidos

- ~~**Card BICE vacía**~~ ✅ RESUELTO (2026-06-02): fix durable en `ScraperBICE` (cadena `or` + `return None`, L-10) + cleanup + guard `restaurante=''` en health check.
- ~~**6 cards "vacías" de contenido**~~ ✅ RESUELTO (2026-06-02): híbrido — Security recupera `field_titulo_caluga` ("Menú Priceless", 4 cards), Itaú+Falabella reciben etiqueta genérica "Beneficio exclusivo" vía `Beneficio.__post_init__` (2 cards). Cleanup data-at-rest + guard `descuento_texto=''` en health check. Tag `v1.6-cards-completas`. (L-14)
- **BancoEstado**: la URL de campaña devuelve un soft-404 de Akamai Edge a TODO cliente (incluso UA de browser real), en todos los endpoints AEM. No es solo anti-bot: la campaña estacional ya no existe. Diferido hasta relanzamiento (L-09).
- **`.git` en Drive inestable** para operaciones de red (usar clone local — ver L-03).

## 📊 Métricas relevantes

- Beneficios de restaurantes en producción: **~887** (14 bancos; fluctúa por corrida — Itaú en observación, bajó a ~23)
- **Apartado "Otros beneficios" (DESPLEGADO):** `/ver/beneficios` muestra **638 beneficios verificables (7 bancos)** — **Banco de Chile 359 + BCI 172 + Entel 49 + Santander 21 + Lider BCI 17 + Tenpo 18 + Consorcio 2** — de `beneficios_otros.json` (`seccion="otro"`, 640 en el archivo; el render oculta los sin % real, L-40/L-41). Financiamiento/servicios/CAE/cuotas no se muestran (L-33/L-34/L-35). 5 bancos agregados hoy vía flip L-32 (fuente ya traía todo) con gate de restaurantes idénticos
- **Cuotas sin interés: 28 campañas** en `cuotas_sin_interes.json` (curado + trazable; varios bancos aún muestran meses anteriores — ver pendientes)
- **Bencinas (descuentos combustible): 31**, RE-CURADAS desde fuente oficial — Copec 100% oficial (`ww2.copec.cl`); Aramco/Shell desde medios verificados (pendiente pasar a oficial); campo `confianza` por dato
- **Trazabilidad auditada (L-33):** restaurantes, otros beneficios y cuotas → **100% fuente oficial**; bencinas → re-curada tras salir 100% agregador
- Apartados web: `/ver` (restaurantes) · `/ver/bencinas` · `/ver/cuotas` · `/ver/beneficios` (**Otros beneficios, NUEVO — desplegado**)
- Correo diario: **09:00 Chile**, estado por banco + sección de cuotas + aviso de desfase de mes
- **Guardia de madrugada: `revision_madrugada.py` + cron 03:00 Chile** — cada bug conocido = un check automático contra producción **incluida la trazabilidad** (confianza/fuente); correo solo si algo reaparece
- Horarios: guardia de madrugada **03:00** → refresco local (Chile) **08:30** → cron nube **09:00** (no chocan)
- Bancos activos: **14** / bloqueados: **1** (solo BancoEstado, diferido)
- Health check `verificar_salud.py`: **✅ exit 0** (guards: ids dup, crash-parity, pisos/banco, mojibake, `restaurante=''`, `descuento_texto=''`)
- **Buscador `/ver`:** indexa nombre + descripción + **comuna + tags** ("providencia" 41→75, "ñuñoa" 8→15)
- **Filtros dinámicos** (2026-08-04): `/ver` y `/ver/beneficios` atenúan/bloquean **día + región + comuna** sin resultados; `/ver/bencinas` día; `/ver/cuotas` categorías. El apartado "Otros beneficios" filtra a verificables (`descuento_valor>0`) **en código** (sobrevive re-scrapes)
- **Falabella:** 95 ofertas con local específico (mall preservado) + restricción trazable "Comprueba en la página oficial"
- **Seguridad:** endpoints `/scrape/*` destructivos eliminados · `/rag` con `ADMIN_TOKEN` · CORS restringido · webhook Twilio con **validación de firma opt-in** (activar con `TWILIO_AUTH_TOKEN` + probar en vivo)
- Lecciones formalizadas: **35** (L-01 a L-35)
- Deploy verificado en vivo el **2026-08-03**
- Último tag: **`v2.0-otros-trazabilidad-filtros`** (trazabilidad + filtros dinámicos) · anterior `v1.9-otros-beneficios` (apartado desplegado) · anterior `v1.8-estable-pre-beneficios` (punto de retorno)

---

## 🔧 Decisión Santander + BancoEstado — RESUELTA (2026-06-02)

Decisión de Fernando: **B + D**. Santander resuelto vía B; BancoEstado diferido vía D.

- **Santander → B (resuelto ✅):** no necesitó browser. Akamai da 403 a UA de browser/python pero **200 a UA estilo `curl/8.4.0`**, sirviendo el HTML SSR completo (`li.item`). Scraper reescrito Playwright→`requests` reutilizando `_parsear_item`, merge quirúrgico sobre data fresca de origin (854→931, 13→14 bancos, sin regresión). Shipped (`f1eec1a`, tag `v1.3-santander-browserless`). Ver L-08.
- **BancoEstado → D (diferido):** B no rinde — la URL de campaña devuelve un soft-404 de Akamai Edge a TODO cliente (incluso UA de browser real), en todos los endpoints AEM (`.model.json`/`.infinity.json`/`jcr:content.json`/`.1.json`). La campaña estacional ya no existe; no es solo anti-bot, así que ni C (browser service) ayuda hasta que haya campaña viva. Se difiere hasta que BancoEstado relance su mes de sabores. Ver L-09.

*La tabla original de opciones A/B/C/D (con tradeoffs) se conserva en el historial git de este archivo y en L-08/L-09.*

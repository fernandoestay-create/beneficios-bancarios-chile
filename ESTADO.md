# Estado del proyecto

**Última actualización:** 2026-08-04
**Estado general:** 🟢 producción

**Sesión 2026-08-04 (parte 2) — Bot WhatsApp+Telegram + firma Twilio activada + bot de 4 opciones:**
- **Firma Twilio ACTIVADA y verificada EN VIVO:** `TWILIO_AUTH_TOKEN` + `TWILIO_WEBHOOK_URL` seteados en Render (`api-beneficios-chile`). Verificado: POST de Twilio → `200`, falso sin firma → `403`.
- **⚠️ Hallazgo (L-38):** el Sandbox de Twilio apuntaba a OTRO servicio (`micartera-ttaa.onrender.com/api/webhooks/whatsapp`), no a `api-beneficios-chile/webhook` → por eso el bot "no respondía". Se re-apuntó al servicio correcto (decisión de Fernando: opción A).
- **CANAL TELEGRAM nuevo:** endpoint `/telegram` (`bdf8646`) reusa el MISMO bot (menú, datos locales, **sin OpenAI → gratis**); usuario prefijado `tg_` para no mezclar con WhatsApp; **auto-registra el webhook** en el arranque (usa `RENDER_EXTERNAL_URL`/`TELEGRAM_WEBHOOK_URL`); opt-in por `TELEGRAM_BOT_TOKEN`. Bot `@Mi_cartera_descuentos_Bot`. Verificado en vivo (logs: `Telegram de ...: hola → 200`).
- **BOT AMPLIADO A 4 OPCIONES** (`637b7bf`): 1 Restaurantes, 2 Bencinas, **3 Cuotas sin interés**, **4 Otros beneficios**. Cuotas y Otros van **solo hasta banco (sin día)**. Handler unificado `ask_banco_generico`; helpers `_generar_resultado_cuotas` / `_generar_resultado_otros`; carga de `cuotas_data` en el arranque.
- **Fixes (`79fc554`):** Scotiabank cuotas "3, 6 y 12" → **"3 y 6 cuotas"** (verificado en la web oficial, agosto 2026, CAE 1,36%; L-35); **Telegram**: se strippean `*`/`_` del formato WhatsApp (salían literales).
- **Decisión de Fernando:** **NO** agregar LLM/preguntas abiertas por ahora → el bot queda **menú-guiado, gratis**. (Opción futura: híbrido menú + RAG para preguntas abiertas de las 4 secciones.)
- **Revisión (2 agentes independientes, punto por punto):**
  - *Código:* los 4 flujos OK. Fix aplicado: `ask_banco` (restaurantes) ahora **avisa** ante un banco inválido (ej. "999") en vez de mostrar todos en silencio — consistente con `ask_banco_generico`; + docstring corregido.
  - *Datos:* se **quitó "Proyecta Energía"** (financiamiento con CAE colado como "90% dcto." en los otros — mismo patrón L-34; **otros 24→23**) y se limpió el nombre del masaje de Consorcio.
  - *Cerrados tras el audit (`849b708`):* **Ripley región** — raíz arreglada (nuevo `_region_desde_direccion()` deriva la región de la ciudad real; 8 registros corregidos, Kunstmann→Los Ríos); **5 ids de bencina** renombrados al día real; el "duplicado" de Security ya no existe.
  - *Cuotas re-curadas a AGOSTO (`c78a860`/`8524895`, 2026-08-04):* vía webs oficiales desde Chile (Chrome); **11/14 bancos vigentes/cubriendo agosto** (9 oficial-verificada; Santander preciso 1-31 ago); Tenpo marcado honesto (junio vencida). `mes_referencia`→agosto, verificado en `/ver/cuotas`.
  - *"Otros beneficios" ampliado (`ca07c4b`):* **BCI agregado 23→195 verificables** (su API traía todo y se botaba → volteado con `seccion="otro"`, L-32) + filtro durable anti-financiamiento en el render. Los demás bancos son incrementales (extender su scraper, BCI = template).
  - *Pendiente real (tu teléfono):* **Shell/Aramco** → oficial desde sus apps (Copec ya es oficial).
- Lecciones **L-38, L-39, L-40**. Commits: `9ad0e7f` firma Twilio · `d7603a3`/`680db29` vars Render · `bdf8646` Telegram · `637b7bf` bot 4 opciones · `79fc554` Scotiabank+Telegram · (+ fixes del audit en este cierre).

**Sesión 2026-08-04 — Fix pipeline bencina (desbloqueo) + doc accesible HTML + respaldo total:**
- **⚠️ Pipeline estaba BLOQUEADO y se desbloqueó (L-37):** el refresco/cron fallaban el health check porque `ScraperBencina` regeneraba `bencinas.json` desde el agregador (Shell→sábado, sin `confianza`) contra el guard `Shell=jueves` → abortaban el push → NADA se actualizaba. **Fix (`60f4e7e`):** `guardar_bencinas_json` **preserva los descuentos curados** del archivo; solo estaciones/precios CNE se actualizan; + `import os` que faltaba. Verificado: preserva 31 descuentos (Shell=jueves, `confianza` intactos), `verificar_salud.py` exit 0.
- **Doc accesible HTML actualizada** (`00.Información_propia_explicación/`): `04_api_y_web`, `05_bencinas`, `01_resumen` con apartado `/ver/beneficios`, trazabilidad y filtros dinámicos; **nav rotos (`_v02`) arreglados en los 6**; los 6 validados (tags balanceadas).
- **Respaldo total en GitHub:** docs de gestión (ESTADO/ROADMAP/LECCIONES/HISTORIAL/CLAUDE), HTML accesibles y código, todo en el repo privado (antes las de gestión vivían solo en Drive).
- Lección **L-37**. Commits: `60f4e7e` (fix bencina) · `37a88f3` (HTML) · `82c9007` (respaldo gestión) · `0164051`/`ed4b26f` (docs) · tag `v2.0-otros-trazabilidad-filtros`.

**Sesión 2026-08-04 (ronda "hazlo todo") — pendientes cerrados:**
- **#1 Filtro "Otros beneficios" ahora en CÓDIGO** (`0dfb1f9`): `_render_deals` muestra solo `descuento_valor>0` cuando `es_otros` → los 24 verificables sobreviven a un re-scrape que regenere `beneficios_otros.json` (ya no depende de curar el JSON a mano; L-37). Verificado: `/ver/beneficios`=24, `/ver`=887 intacto.
- **#3 Filtros dinámicos EXTENDIDOS** (`0dfb1f9`): `/ver` y `/ver/beneficios` ahora atenúan/bloquean **región y comuna** sin resultados (antes solo día); **bencinas** con día dinámico; **cuotas** con categorías dinámicas (atenúa las sin campañas del mes+banco). `node --check` de las 4 vistas: 0 rotos.
- **#4a Firma Twilio — ACTIVADA y VERIFICADA EN VIVO ✅** (2026-08-04): validación de `X-Twilio-Signature` en `/webhook`, opt-in por `TWILIO_AUTH_TOKEN`. Fernando pegó el token en Render (`api-beneficios-chile`) + `TWILIO_WEBHOOK_URL=https://api-beneficios-chile.onrender.com/webhook`. **Hallazgo clave:** el Sandbox de Twilio apuntaba a **OTRO servicio** (`micartera-ttaa.onrender.com/api/webhooks/whatsapp`), no a este — por eso el bot "no respondía". Se re-apuntó el webhook del Sandbox a `api-beneficios-chile/webhook` (decisión de Fernando: opción A). **Verificado en logs**: `WhatsApp de +569...: hola` → `POST /webhook 200 OK` desde IP de Twilio (firma pasó); falso sin firma → 403; el bot respondió el menú. **Bot WhatsApp 100% operativo con firma.** (L-38)
- **#2 Shell/Aramco (NO se cambió, a propósito):** la búsqueda solo devuelve **agregadores** (Chócale/medios), no fuente oficial → por L-24/L-35 no se reescribe en base a agregadores. El upgrade a `confianza=oficial` necesita las apps de Aramco/Shell (desde el teléfono). Data actual (medios, `secundaria`) intacta.
- **#4b RAG revectorización — HECHO ✅** (con tu OK tras ver el costo): `upload_pinecone.py` re-vectorizó los **887 restaurantes** (OpenAI `text-embedding-3-small` + Pinecone, borró+subió). Costo real ~US$0.002. **Verificado contra Pinecone: 887 vectores en el namespace** (L-W20 "¿insertó?"). Se corrió con las keys del `.env` de Drive (copiado temporal al clone, gitignoreado, borrado después). El bot RAG queda al día con los nombres reales de Falabella.
- **Pendiente próxima sesión:** re-curar Shell/Aramco desde apps oficiales (#2, necesita el teléfono); activar+probar firma Twilio en vivo (#4a, setear `TWILIO_AUTH_TOKEN` en Render); cubrir más bancos en "Otros beneficios"; (opcional) faceteado dinámico del filtro de banco en bencinas; (backlog) migración Pinecone→pgvector.

**Sesión 2026-08-03 (parte final) — Calidad, trazabilidad y filtros dinámicos:**
- **"Otros beneficios" filtrado a 24 verificables** (de 228): solo los con descuento % real; los 204 de financiamiento/servicios/CAE no se muestran ("si no está chequeado, no mostrar"). Bug del % del CAE corregido (Bip Solar). (L-34)
- **Auditoría de TRAZABILIDAD (4 datasets):** restaurantes (887), otros (24), cuotas (28) → 100% oficial; bencina-descuentos (31) era 100% agregador (descuentosrata). (L-33)
- **Bencina RE-CURADA:** Copec (15) desde la oficial (`ww2.copec.cl`); Aramco/Shell (16) desde medios verificados; campo `confianza` + `url_fuente` oficial por dato; 5 errores del agregador corregidos (Shell→jueves, Itaú→martes, BancoEstado→martes $50, BCI→7% cashback, Santander Consumer→vie-dom); fuente marcada en la web. (L-35)
- **Guardia de madrugada ampliada a TRAZABILIDAD** (el "agente que revisa siempre"): alerta si la data pierde `confianza` o vuelve al agregador.
- **Filtros DINÁMICOS de día** en /ver y /ver/beneficios: los días sin resultados según el banco se atenúan/bloquean. + **"Estamos confirmando"** cuando una sección no tiene data.
- Lecciones **L-33/L-34/L-35/L-36** (L-36 = filtros dinámicos). **Pendiente:** re-curar Shell/Aramco desde apps oficiales (hoy medios); extender filtros dinámicos a región/comuna y a bencinas/cuotas; los otros 12 bancos del apartado.

**Sesión 2026-08-03 — Cierre (abarcó 29-jul a 3-ago): Falabella con local + condiciones en las tarjetas + apartado "Otros beneficios" (todo verificado con py_compile + `node --check` + health check, en producción salvo donde se indica):**
Continuación del arco que arrancó el 29-jul. Lo nuevo de este cierre:

1. **Guardia de madrugada** (`2696af9`): `revision_madrugada.py` + workflow (cron 03:00 Chile) convierte CADA bug conocido en un check automático contra producción + data; manda correo SOLO si algo reaparece. _(Documentado también en el bloque del 29-jul, punto 8.)_
2. **Falabella con local específico** (`dd62ddc`): ahora **preserva el mall** en el nombre (Tanta [Mallplaza] ≠ otro Tanta, ya no se confunden) + agrega una **restricción trazable consistente** — "Revisa los locales del beneficio. Comprueba en la página oficial." — en las **95 ofertas** de Falabella. Recuperar/avisar honesto, NO inventar (L-19/L-29).
3. **Condiciones/restricciones visibles en `/ver`** (`b4d0925`): las tarjetas ahora muestran las **condiciones/restricciones (📋)** + un link **"Comprobar en la página"** para que el usuario verifique en la fuente oficial.
4. **APARTADO NUEVO "Otros beneficios"** (`7ebf2cf`): Santander y Consorcio traían beneficios **NO-restaurante** (farmacias, transporte, ski El Colorado/La Parva, hoteles, retail) que **se botaban** al filtrar solo restaurantes. Ahora se **capturan** con un campo `seccion="otro"` en un **dataset SEPARADO** (`beneficios_otros.json`, **228 beneficios**), **SIN tocar** `beneficios.json` (restaurantes) ni los pisos/red de seguridad; el orquestador los **separa** en dos flujos. La pantalla **`/ver/beneficios`** reusa la lógica de `/ver` (filtros día/categoría/tarjeta + buscar por nombre). **🔄 En progreso: Claude la está terminando en esta misma sesión.**
5. **Respaldo** (punto de retorno): tag **`v1.8-estable-pre-beneficios`** como punto seguro antes del apartado nuevo.

**Métricas de este cierre:** restaurantes = **14 bancos intactos (~885)**; otros beneficios = **228** (Santander 224 + Consorcio 4). **Pendientes:** los otros **12 bancos** para el apartado "Otros beneficios" (scrapear sus páginas de beneficios generales); **webhook Twilio** (prueba en vivo); **RAG revectorización** (costo API → requiere OK).

**Sesión 2026-07-29 — Auditoría ácida de filtros y búsqueda + fixes (todo verificado y en producción):**
Arrancó con un bug que reportó Fernando ("Falabella + jueves no sale nada" en el mapa) y terminó en una auditoría de punta a punta. Todo verificado (py_compile + `node --check` + health check) y desplegado:

1. **Bug del mapa (el reportado):** las ofertas sin local fijo (aplican en toda la cadena, sin dirección) no tenían pin → mapa vacío. Ahora se muestran como **tarjetas debajo del mapa** (`dealCardHTML` + `#mapCards`). Commit `9b3fd67`.
2. **5 bugs de filtros del patrón "el dato existe pero no se muestra"** (L-28): mapa (277 sin local fijo), **Modalidad** (222 ofertas invisibles bajo Presencial/Online, 200 del Banco de Chile), **Zona** (277 nacionales borradas al filtrar región), normalización de días (preventivo), mutación de array. `9b3fd67`.
3. **Buscador indexa comuna + tags:** buscar "providencia" 41→75, "ñuñoa" 8→15. Commit `748571e`.
4. **Seguridad** (`c90eb07`): eliminados `/scrape/ejecutar` y `/scrape/bencinas` (POST anónimo destructivo que borraba 12 bancos); `/rag` con guard `ADMIN_TOKEN` + `max_length=1000`; CORS restringido (era `*` + credentials); tokens hardcodeados caducados limpiados; `buscar_beneficios` (API+bot) busca en nombre+descripción+comuna+tags. **⚠️ PENDIENTE: firma Twilio en `/webhook`** — requiere prueba en vivo del bot, no se aplicó a ciegas.
5. **Falabella nombres reales** (`d1781d7`): 95 nombres recuperados del slug del link (Petit, Vapiano, Muu Grill, Tanta, Mamma Mia…) en vez de "Dcto en Restaurante". El nombre vivía en el `linkUrl`, no en `title` (L-29).
6. **`TUNING_PAGINAS.md`** (`9b0cf31`): fine-tuning operativo — todos los errores/cambios de las páginas (síntoma→causa→fix→evitar).
7. **Incidente (L-30):** el refresco local corrió `git reset --hard` y borró 4 fixes sin commitear → regla: commitear pronto cada bloque verificado. Se re-aplicaron y commitearon.
8. **Guardia de madrugada** (`2696af9`): `revision_madrugada.py` + workflow (cron 03:00 Chile) convierte CADA bug conocido en un check automático contra producción + data (fine-tuning hecho código, L-07); manda correo SOLO si algo reaparece. Verificado en vivo: 897 beneficios, TODO OK. Se corre a mano con `workflow_dispatch`.

Lecciones nuevas **L-28/L-29/L-30**. **Pendientes:** webhook Twilio (prueba en vivo), RAG Pinecone revectorización (costo API → requiere OK), filtrar de Falabella lo que no es restaurante (app-copec, pronto-copec, novedades-cmr-puntos).

**Incidente 2026-07-10 — "Render caído" (RESUELTO, se auto-recuperó):** Fernando recibió el correo de Render "deploy failed for api-beneficios-chile". Diagnóstico: el deploy que falló fue el del commit **de datos del refresco de la mañana** (`0386249` "🔄 Actualizar beneficios…"), ~11:45 Chile — **NO** fue código (`api.py` solo importa de `scrapers.py`; no importa `aprendizaje.py`/`chequeo_bancos.py`, así que los cambios de monitoreo de hoy no pudieron romper el deploy). Fue un **fallo transitorio de build del free-tier de Render** sobre un commit solo-datos cuya data es válida (el health check del refresco pasó; boot local con los datos de hoy = 865 beneficios OK). **Se auto-recuperó**: los pushes posteriores de la sesión (que llevan la misma data) dispararon un deploy exitoso. **Verificado sano:** `/estadisticas` 200 (865/14), `/ver` 200 con 865 beneficios embebidos + `<script>` válido (`node --check`, guard L-21). El 503 que se vio al probar fue **cold-start** del free-tier (duerme por inactividad, ~40s en despertar) — la molestia recurrente de siempre (ver keepalive `c5099fa`). **Pendiente/decisión de Fernando:** para 24/7 sólido sin sleep ni build flaky → Render pago (~US$7/mes) o UptimeRobot; hoy el sitio se cura solo pero puede aparecer 503 unos segundos si estaba dormido.

**Sesión 2026-07-10 — Auto-diagnóstico "aprender de los errores" + Banco Security resuelto:**
El sistema ahora **se auto-gestiona de verdad, no solo avisa** (pedido de Fernando: "debe ser auto gestionado y arreglarlo automáticamente si hay un banco caído… para eso aprendemos de los errores"). Tres capas nuevas sobre el correo, **sin tocar los scrapers de beneficios** (todo va en la capa de monitoreo: `aprendizaje.py` + `chequeo_bancos.py`):

1. **Auto-diagnóstico por incidente (`clasificar_incidente`):** cuando un banco queda DEGRADADO/CAÍDO, el sistema mira su **propio histórico** y decide si **se resuelve solo** (`auto`) o **requiere tu acción** (`revisar`): CAÍDO que ya cayó a 0 antes y volvió → `auto` (geo-fence/transitorio, el refresco desde Chile lo recupera); CAÍDO por primera vez → `revisar` (posible cambio de la página → arreglar scraper); DEGRADADO estable ≥3 días en el mismo nivel → `auto` (nuevo nivel por renovación de campaña, el piso se recalibra solo); DEGRADADO aún cayendo → `revisar`. El **correo separa** 🔵 "se resuelven solos" (informativo) de 🔴 "requieren tu acción", y el **asunto** solo dice ⚠️ REVISAR si hay algo `revisar` real. (amplía **L-26**)
2. **Aprender de la revisión humana (`confirmar_nivel` + `niveles_confirmados.json`):** cuando **reviso** una baja y confirmo que es **real** (el banco recortó su oferta, no es bug), `confirmar_nivel(banco, nivel, motivo, fecha)` lo registra; el sistema **deja de alarmar** mientras el banco se mantenga en ~ese nivel (≥85%) pero **re-alarma si cae aún más** (caída nueva distinta). Cierra el loop: mi revisión le enseña al sistema. (**L-27** nueva)
3. **Asunto coherente:** un banco DEGRADADO pero auto-gestionado ya no resta del conteo verde → "✅ TODO OK · 14/14 (1 gestionado)" en vez de "13/14".

**✅ Banco Security — RESUELTO (10-jul):** el correo lo marcaba ⚠️ REVISAR. Diagnóstico en vivo: Security bajó de **108 → 70** restaurantes. **NO es bug del scraper** — verificado contra su API (`personas.bancosecurity.cl/jsonapi/node/beneficio`, revisadas las 12 categorías): las categorías Restaurantes y Comida Rápida se **vaciaron** (quedó Gourmet 68 + 1 + 1); el scraper lee bien los 3 tids de comida. Es un **recorte real de oferta** del banco, mismo patrón que Itaú pero de solo ~2 días (por eso el auto-diagnóstico lo marcaba `revisar` correctamente — aún no se estabilizaba). Como lo **revisé y confirmé real**, ejecuté `confirmar_nivel('Banco Security', 70, …)` → correo **verde** (Security = `auto`); si cae bajo ~60 vuelve a alarmar. Commits `7ac8d6c` (confirmar_nivel) · `3a40d63` (asunto). El asunto quedó "✅ TODO OK · 14/14 (1 gestionado) · 865 beneficios".

**Sesión 2026-07-01:** se agregó un **apartado nuevo de Cuotas sin interés** (`/ver/cuotas`, botón 💳 en la barra de las 3 páginas): campañas por banco y categoría (todos los comercios, automotriz, educación, supermercados, salud, contribuciones), curadas desde las **páginas oficiales de cada banco** (leídas desde Chile con `curl` UA-curl donde el WAF lo permitió — Santander/Scotiabank/Lider BCI verificadas en vivo; BICE/Itaú siguen bloqueando incluso desde Chile), con **condiciones de uso, vigencia y link oficial por campaña**, distinguiendo **0% real vs tasa preferencial**, y con **cruce contra Chócale** para marcar inconsistencias (control de calidad, no fuente). Datos en `cuotas_sin_interes.json` (14 bancos: 12 con campaña, Ripley/Mach sin campaña tipo). Enfoque **curado mensual + trazable** (decisión de Fernando). Foto al 1-jul (transición de mes: la mayoría aún muestra junio, Scotiabank ya rotó a julio). Commit `a5558a0`. **Además, misma jornada:** (a) selector de bancos por **logo** + selector de **mes** en el apartado (`528ab8c`); (b) el **correo diario incluye una sección de cuotas** (resumen + las de 0% + botón, `33b4aad`) con **aviso automático de desfase de mes** — si `cuotas_sin_interes.json` quedó en un mes anterior al actual, el correo avisa "Ya es X, cuotas de Y — actualizar" (detección diaria del cambio de mes, `ee0abad`); (c) revisión de qué bancos rotaron a julio: **solo Scotiabank al 1-jul** (el resto sigue junio o publica en SPA/imágenes no legibles; Chócale aún no publica julio). **Nota:** la rutina en la nube que me despierte para curar NO es viable en este entorno (`create_trigger` da 404, es sesión local sin infra de rutinas cloud); la **detección** de cuotas desfasadas es automática (en el correo), la **curación** la hago yo cuando el correo avisa o Fernando lo pide. Detalle: lección **L-24**.

**✅ Itaú — RESUELTO (6-jul):** Banco **Itaú** bajó de 71 a ~23-30 restaurantes. Verificado en vivo: NO es bug del scraper — su Ruta Gourmet (`itaubeneficios.cl/.../ruta-gourmet/`) hoy tiene solo 23 restaurantes, sin más páginas (probada la paginación: siempre las mismas 23). El correo lo marca **DEGRADADO** correctamente (detección real, no falla). Probable renovación de campaña de inicio de mes. **Decisión (Fernando, 1-jul): esperar 2-3 días** — si recupera (~70) era transición y se resuelve solo; si se queda en ~23, bajar el piso de Itaú (de 25 a ~15 en `chequeo_bancos.py` → `PISOS_BANCOS`) para que el correo deje de marcarlo. El seguimiento es automático: el correo diario muestra la evolución de Itaú. **→ Ejecutado 1-jul (tarde):** Itaú=23 hacía **fallar el health check** (gate del refresco) → se bajó el piso a 15 (`chequeo_bancos.py`, commit `0ebf168`); el correo lo seguía marcando DEGRADADO por el piso relativo (60% del histórico). **→ RESUELTO 6-jul (commit `6b46054`):** tras 6 días estable en 23, la causa era que el *nivel normal* usaba la mediana de las últimas **12** corridas, que aún cargaba los 71 de junio (piso = 60% de ~71 = 42, sobre los 23 reales). Se bajó la ventana de aprendizaje de 12 a **7 días** en `aprendizaje.py` (`N_VENTANA`): ahora nivel normal Itaú=23, piso=15, estado **OK**, asunto verde **14/14**. Verificado: 0 bancos con problema, ningún otro afectado. El sistema ahora reconoce cambios de nivel sostenidos en ~1 semana (útil para renovaciones de campaña mensuales). Si Itaú recupera a ~70, el piso sube solo.

**Revisión de cuotas (1-jul, barrido de los 12 bancos con navegador desde Chile):** **BCI → hasta septiembre 2026** (dato confirmado por Fernando; la web pública de BCI mostraba ene-jun al 1-jul, con nota honesta), **Consorcio → hasta 31/12/2026** (leído en su web oficial), Scotiabank → julio. **Límite real hallado:** 8 de 12 bancos (Banco de Chile, Santander, Itaú, BICE, Security, Lider, Tenpo, Entel) publican las cuotas en **imágenes/SPA que ni el navegador extrae como texto** — para esos se mantiene lo curado + link oficial, y Fernando aporta datos puntuales que conoce. Regla (memoria): al revisar cuotas, barrer SIEMPRE los 14 bancos yo, sin pedirle links a Fernando.

**Apartado de cuotas quedó 100% DINÁMICO** (commit `8441276`): selector de mes (jun→dic, junio como "historia", abre en el mes en curso) + logos de bancos filtrados por mes + contadores del hero recalculados por mes + categorías — todo generado de `cuotas_sin_interes.json`, nada hardcodeado. Verificado en prod: julio → 6 bancos / 12 campañas / 6 logos; septiembre → 5 logos.

**➡️ PRÓXIMA SESIÓN (pendientes):**
1. **Cuotas a julio/agosto:** re-curar los ~6 bancos que siguen mostrando junio (Banco de Chile, Santander, Itaú, BICE, Security, Tenpo — publican en imágenes/SPA no legibles con navegador) cuando publiquen julio; armar agosto. El correo diario ya avisa el desfase automáticamente. Barrer SIEMPRE los 14 (memoria).
2. **Itaú:** ver la evolución en el correo — si recupera (~70) subir el piso de nuevo (hoy en 15); si sigue en ~23, quedó bien.
3. Cuando Fernando aporte un dato puntual de un banco (como BCI jul-sep / Consorcio dic), actualizarlo trazable.

**Sesión 2026-06-23 (continuación):** se arregló el bug del JS de `/ver` (mapNote, L-21), se **alineó el correo diario a las 09:00 Chile** (cron `0 13 * * *`) y se movió el refresco local a las 08:30 (no chocan; L-22), se verificó en vivo que todo opera (workflows `active` + tarea `Ready`; L-23), y se documentó todo (L-22/L-23 local, L-W44 workspace, COMO_FUNCIONA + memoria). Detalle en los puntos 12-13. _(Resumen de la sesión grande del 2026-06-22, abajo.)_

**Sesión 2026-06-22:** sesión grande que arrancó con "faltan descuentos de Falabella" y terminó con el sistema **auto-monitoreado, auto-resiliente y con aprendizaje**. Lo hecho:
1. **Falabella restaurado** — era geo-fence del cron (corre en USA), no un bug; se restauró desde Chile.
2. **Red de seguridad**: preserva cualquier banco que caiga a 0 (ya no desaparece en silencio).
3. **Chequeo experto por banco** (OK / DEGRADADO / CAÍDO / PRESERVADO) + reintentos automáticos.
4. **Refresco local diario desde Chile** (Tarea Windows `MiCartera-Refresco`) que mantiene frescos los bancos geo-fenceados.
5. **Auditoría de credibilidad de los 14 bancos**: Santander/Consorcio sin % → etiqueta honesta; **Consorcio 50% Casacostanera** capturado; mapa con aviso de ofertas sin local fijo.
6. **Mail diario detallado** "por sí o por no" desde el cron (asunto `✅ TODO OK` / `⚠️ REVISAR`) — **verificado: a Fernando le llegó**.
7. **Aprendizaje** (`historial.json`): nivel normal por banco, pisos adaptativos, alerta de tendencia.
8. **Cron pasado a diario** + documentación completa.

Estado: **954 beneficios, 14 bancos, todo verde, andando solo**. Lecciones nuevas **L-15 a L-20**. **Cómo funciona el sistema completo → [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md).** _(Sesiones previas v1.3–v1.6 del 06-02 y anteriores: más abajo.)_

---

## 📍 Dónde quedé

**El sistema quedó andando solo y documentado.** Arrancó con "faltan descuentos de Falabella" (era geo-fence del cron USA, no un bug). Estado actual: **14/15 bancos live, 954 beneficios, 31 bencinas, 0 ids duplicados, health check exit 0, mail diario funcionando** (verificado por Fernando). Único banco faltante: BancoEstado (campaña caída, diferida). **La guía completa de cómo funciona está en [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md).** El detalle de cada cambio de esta sesión, abajo (puntos 0–10).

### ⚡ Sesión 2026-06-22 — Falabella restaurado + cron blindado (RESUELTO + shipped)

**Diagnóstico (cómo se llegó):**
- Producción servía 858 beneficios / 13 bancos, **sin Falabella**. El cron (GitHub Actions "Scraping Mensual", `.github/workflows/scraper.yml`) corría con "success" e incluso mandaba email exitoso.
- El `ultimo_scrape` de la API es **engañoso**: es `datetime.now()` al arrancar la app ([api.py:150](beneficios-bancarios-chile/api.py:150)), no la fecha real del scrape. La data real venía del commit del bot del 06-20.
- Historial del JSON (commits del bot): Falabella estaba en **97 el 06-18** y cayó a **0 el 06-20**. El scraper no cambia desde el 06-02 → **no es el código**.
- **Causa raíz: geo-fencing.** Falabella sirve su página `/descuentos/restaurantes` **vacía** a IPs no chilenas. El scraper trae **95 desde la IP de Fernando (Chile)**, pero `WebFetch` (infra datacenter) trae la página vacía. El runner de Actions (USA) recibe 0 → el scraper devuelve `[]` sin excepción → el commit del bot borró Falabella en silencio. (L-15)

**Fix shipped:**
1. **Restaurar (commit `bdc61bc`):** Falabella scrapeado desde Chile (95), normalizado (`_normalizar_todos`), inyectado sobre la data fresca del repo (858) con merge quirúrgico (L-04) + ids únicos (L-11) → **953, 14 bancos**. Diff = puras inserciones (0 borrados, los otros 13 bancos intactos). Health check exit 0.
2. **Blindar el cron (commit `c4b66d9`):** `OrquestadorScrapers.preservar_bancos_caidos()` — si un banco trae 0 teniendo datos previos, **reinyecta los previos** (stale pero presentes) en vez de borrarlos; `escribir_status()` + `scraper.yml` hacen que el email **ALERTE** (asunto + banner) cuando un banco cae, en vez de reportar "success" liso. Testeado (caso caído reinyecta 95 + alerta; caso sano no toca nada). (L-16)
3. **Chequeo experto para los 15 bancos (commit `0f72571`):** nuevo módulo `chequeo_bancos.py` (fuente única de pisos). Cada corrida del cron clasifica cada banco **OK / DEGRADADO / CAÍDO** (piso efectivo = max del piso absoluto y 60% del conteo previo), **reintenta** 3× las fallas transitorias (`_scrapear_con_reintentos`, backoff), **preserva** los caídos y manda un **email con el estado de CADA banco** (tabla coloreada; asunto verde "14/14 OK" o "⚠️ ALERTA" con los nombres). `verificar_salud.py` importa los pisos de ahí (fuente única). Testeado: sano (14/14 OK), Falabella caído (CAÍDO+preservado+alerta), BCI 129→20 (DEGRADADO sin preservar). (L-17)
- **Verificado en prod**: `/estadisticas` y `/bancos` → 14 bancos, Falabella presente, otros bancos intactos.

4. **Refresco local automático desde Chile (commit `7472793`):** `refrescar_local.ps1` + Tarea Programada de Windows `MiCartera-Refresco` (diaria 9:00, `StartWhenAvailable`, $0). Scrapea los 15 bancos desde la IP local (Chile, **SIN geo-fence**), corre el chequeo + health check y pushea → Render. Resuelve automáticamente geo-fence + transitorios para TODOS los bancos, sin depender del runner USA. `diagnosticar.py` guarda el HTML crudo de los bancos caídos para arreglo rápido. **Flujo ante un banco caído (decisión de Fernando "aviso + arreglo rápido"):** transitorio/geo-fence → auto; cambio de estructura del sitio → mail avisa + Fernando pide el arreglo a Claude.
- **✅ VALIDADO EN VIVO:** el cron de GitHub Actions corrió hoy 17:44 UTC con el código nuevo, trajo Falabella en 0 (geo-fence) y **la red de seguridad lo preservó solo en 95** → producción **954/14**, Falabella presente, sin intervención. (L-15/L-16/L-17)
- **Revisión en vivo de los 15 (desde Chile):** 14 bancos activos OK (Falabella=95); BancoEstado 0 (diferido + sin playwright local, esperado).

5. **Refresco local validado end-to-end + 2 fixes (commits `69b6cf1`, `4c87770`):** al correr el refresco en Windows, el health check (gate) atrapó 2 bugs latentes que el cron Linux ocultaba: `santander_ac-kitchen` **duplicado** (Santander no estaba wireado a `_asegurar_ids_unicos`) y 24 restaurantes BICE con **mojibake** (`response.text` adivina mal el encoding en Windows/cp1252). Fixes: `_asegurar_ids_unicos` **global** en el orquestador (protege a TODOS los bancos) + `response.encoding='utf-8'` en BICE. Re-validado: el refresco corre limpio (954, health check ✅ TODO OK) y **pushea a producción**. Producción NO tenía estos bugs (cron Linux); son preventivos. (L-18)

6. **Auditoría minuciosa de los 14 bancos (credibilidad + trazabilidad, commits `3e94879`/`22a0fe5`):** pedido de Fernando tras "no salen las ofertas de Falabella para el lunes". Hallazgos: (a) **el dato de Falabella está OK** (34 ofertas el lunes, todas con días bien) — el problema era el **MAPA**, que excluye 222 ofertas de 6 bancos sin local fijo (Falabella, Entel, Lider BCI, Mach, Tenpo, Santander); se ven en la Lista pero no en el mapa. (b) **Santander (72/77) y Consorcio (8/8) sin % real** — verificado que el % NO existe en la fuente (ni listado, ni detalle, ni API; en Consorcio vive dentro de la imagen): son beneficios de acceso. **Fixes:** Santander/Consorcio → etiqueta honesta "Beneficio exclusivo" + tipo de cocina (no "0%" ni texto crudo); mapa → aviso que cuenta las ofertas sin local fijo y linkea a la Lista (sin inventar ubicaciones). Los otros 8 bancos: auditados OK. Re-scrapeado y pusheado vía refresco local; health check ✅. (L-19)

7. **Consorcio corregido — SÍ tenía % (commit `82b6951`):** Fernando aportó la captura: Casacostanera = **50% devolución, tope $40.000/mes, hasta 31/07/2026**. Mi conclusión previa ("sin %") era incompleta: el % no está en las cards (`tab-card-credit-card`) sino en un **type hermano** (`tab-beneficios-items`, promo Casacostanera). El scraper ahora lee esa promo y aplica el 50% + tope + vigencia a sus restaurantes (trazable, no hardcoded). Lección: "investigar a fondo" debe agotar los types/endpoints hermanos antes de concluir "no existe". (amplía L-19)
8. **Mail del refresco "por sí o por no" (commit `82b6951`):** `refrescar_local.ps1` ahora manda un correo en CADA corrida (verde "14/14 OK" o rojo si falla el scrape/health check), no solo el cron. Requiere configurar `GMAIL_USER` + `GMAIL_APP_PASSWORD` (mismo app password del cron) como variables de entorno — ver `INSTALAR_MAIL` en el script.

9. **Mail detallado + asunto claro + APRENDIZAJE (commits `02cc9f1`, `1d8622d`):**
   - **Mail detallado:** cards de resumen + estado de cada banco (trajo vs piso, coloreado) + sección "Cómo funciona" (capas, reintentos, red de seguridad, qué significa cada estado).
   - **Asunto** arranca con `✅ TODO OK · MiCartera 14/14 bancos · …` o `⚠️ REVISAR · …` para marcarlo de un vistazo sin abrir.
   - **Aprendizaje** (`aprendizaje.py` + `historial.json`, sembrado en `5e630aa`): cada corrida deja un snapshot; el sistema calcula el **nivel normal** de cada banco (mediana de las últimas 12 corridas), **ajusta el piso solo** a ese nivel, y detecta **tendencias** (un banco que cae bajo el 70% de su normal → DEGRADADO, alerta temprana antes del 0). NO es ML neuronal: estadística honesta sobre el propio histórico. El cron y el refresco commitean `historial.json` para que la memoria persista. (L-20)

10. **Mail diario desde la nube + estado PRESERVADO (commit `0e933e3`):** para que el mail "por sí o por no" llegue **sin que Fernando configure el app password local**, el cron de GitHub Actions ahora corre **diario** (`0 11 * * *` ≈ 07:00 Chile) y manda el mail con los secrets de Gmail **que ya están en GitHub**. Como el cron corre en USA y geo-fencea Falabella, se agregó el estado **PRESERVADO** (azul, informativo): un banco que trae 0 pero conserva datos previos NO es alarma roja → el asunto sigue verde "✅ TODO OK · 14/14 (1 preservado)". Solo es "⚠️ REVISAR" si hay un caído real (sin datos previos) o un degradado. El refresco local (Chile) sigue refrescando Falabella; el cron manda el mail. _(Nota: si Fernando configura `GMAIL_*` local, el refresco también manda mail; pero ya no es necesario.)_

11. **Keep-alive de la web (commit `c5099fa`):** Fernando reportó "el link del mail me lleva a nada". La web estaba OK — era **Render free durmiendo** (suspende tras ~15 min sin visitas; primera carga ~40s en blanco). `keepalive.yml` pinguea `/estadisticas` + `/ver` cada 10 min en horario de uso (~06–19 Chile) para mantenerla despierta. De madrugada puede dormir (no se usa). Para 24/7 garantizado: UptimeRobot o Render pago.

12. **Bug del JS de `/ver` — regresión propia, arreglada (commit `20d10ab`):** Fernando reportó "no se ven los beneficios de restaurantes". Causa: el aviso del mapa que agregué en `0e933e3` (`mapNote`) tenía un `onclick` inline cuyas comillas simples cerraban el string `innerHTML='...'` → error de sintaxis que **rompía TODO el `<script>` de `/ver`** → la página cargaba (HTTP 200) pero no renderizaba nada. Fix: `id` + `.onclick` en JS puro (sin comillas anidadas). Validado con `node --check`; **verificado en prod** (JS OK tras el deploy). El health check de datos no lo detecta → lección **L-21**: tras tocar el HTML/JS de `api.py`, validar el `<script>` con node.

13. **Cron del correo movido a las 09:00 Chile (commit `0a1e8e4`):** Fernando pidió alinear el correo diario de MiCartera con sus otros reportes diarios (Socio Estratégico llega ~09:00 AM; verificado mirando su Gmail). El cron pasó de `0 11 * * *` (07:00) a `0 13 * * *` (**09:00 Chile = 13:00 UTC**) en `scraper.yml`. Solo cambió la hora del envío. **Además**, el refresco local (Tarea Windows `MiCartera-Refresco`) se movió de 09:00 a **08:30** (vía `Set-ScheduledTask`, sin tocar credenciales — la tarea es LogonType Interactive, sin password guardada) para que refresque **los 15 bancos** desde Chile ANTES del cron de las 9 y no choquen los `git push`. (El refresco corre `scrapers.py` completo — los 15 bancos, no solo Falabella; Falabella es únicamente el caso especial que el cron USA no puede ver por geo-fence.) Flujo: **08:30 refresco (Chile, los 15 bancos frescos) → 09:00 cron (USA, revisa los 15 otra vez + manda el mail)**. **Decisión de Fernando: "estamos en MiCartera, no te metas con otros"** → el reporte diario del agente EIA (`11.Agente revision EIA`) NO se tocó; se hará en su propia sesión.

---

> _**Lo que sigue abajo es la sesión anterior (2026-06-02, v1.3–v1.6).**_

### 0. 6 cards sin `descuento_texto` — híbrido shipped (RESUELTO + shipped) — `v1.6-cards-completas`

- **Opción A (recuperar dato real) — Banco Security:** `ScraperBancoSecurity._parsear_item` ahora cae a `attrs.get('field_titulo_caluga')` (= "Menú Priceless") cuando `descuento_valor == 0`. Toca **solo la clase del banco afectado**. Verificado **en vivo** (L-13): Security live 86 items, **0 con texto vacío**. 4 cards recuperadas (Tanaka, Capogrossi, Demencia, La Campiña — "- Mastercard").
- **Opción B (red de seguridad genérica) — Itaú + Falabella:** `Beneficio.__post_init__` pone `"Beneficio exclusivo"` si el beneficio queda sin `%` ni texto. Es el **único chokepoint que corre en TODA construcción** de `Beneficio` (cron + cleanup) → ninguna card puede volver a renderizar vacía. Corre **después** del parser de Security, así que no pisa el "Menú Priceless". Cubre `itau_men__priceless_by_mastercard_tarjetaita` y `falabella_caoba-bar`.
- **Cleanup data-at-rest (929):** sobre data **fresca de origin** (L-04) — 4 Security → "Menú Priceless", round-trip por el **dataclass real** (lossless: 0/923 no-objetivo alteradas) + CSV regenerado con `csv.DictWriter` (CRLF intacto: 932 CRLF, 0 LF-solos; diff quirúrgico de 12 líneas). (L-12)
- **Guard nuevo en `verificar_salud.py`** (patrón L-07): **falla** si reaparece `descuento_texto=''`. Health check exit 0 con el guard verde.
- **Verificado:** health check exit 0; `/ver` vía TestClient → 929 beneficios / 14 bancos, "Menú Priceless" y "Beneficio exclusivo" presentes.
- **Shipped:** commit `0f4811a`, push `dea15cc..0f4811a` en `origin/main`, tag `v1.6-cards-completas`. Render auto-redeployando. (L-14)

### 1. Calidad 100% — 4 tiers shipped (RESUELTO + shipped) — `v1.5-calidad-100`

- **Tier 1 (`verificar_salud.py` blindado, commit `5dacf92`):** crash-parity importando los **modelos reales** `Beneficio`/`DescuentoBencina` (mismo `TypeError` que tumbaría el arranque en Render), pisos de conteo por banco (atrapa colapso a 0 tipo Falabella/Santander), guard de mojibake en texto de cara al usuario, **guard de ids duplicados** en beneficios + bencinas.
- **Tier 2 (descarte cards sin nombre, commit `5172f98`):** cadena `or` + `return None` (patrón L-10, generaliza el fix BICE) en los 6 scrapers que podían colar nombre vacío + fix de un `bare except`. Auto-cura en el cron.
- **Tier 3 (unicidad de ids, commit `53b7f76`):** helper idempotente `_asegurar_ids_unicos()` en Ripley/Entel/bencinas. Cleanup quirúrgico **930→929** (1 dup exacto `entel_just_burger` dropeado; 2 colisiones Ripley reales suffixadas `_2`) + 7 tier-ids de bencina suffixados `_2/_3`. Hecho vía **round-trip por el dataclass real** (lossless, `__post_init__` preserva `fecha_scrape`: 0/930 y 0/31 cambiados en round-trip de control) + CSV regenerado con `csv.DictWriter` byte-idéntico (CRLF-safe). (L-11, L-12)
- **Tier 4 (Itaú+LiderBCI browserless, commit `f544e75` + comentario `dea15cc`):** eliminado el Playwright muerto (condenado a 0 en el cron, L-01). **Verificado en vivo** antes del push: `ScraperItau`→68, `ScraperLiderBCI`→11 (el health check prueba data-at-rest, no el fetch — L-13).
- **Shipped:** `bb837b5..dea15cc` en `origin/main`, tag `v1.5-calidad-100`. Render redeployando.
- **ⓘ `ScraperBancoEstado` sigue en Playwright a propósito** (banco diferido, dormido, retorna 0; se retoma cuando relance campaña — L-09).

### 2. Card basura BICE eliminada (RESUELTO + shipped) — fix durable + cleanup + guard

**Causa raíz:** la entrada `Dólares BICE Aplica` con `restaurante=""` se colaba porque `fields.get('Marca', default)` **NO aplica el default cuando `Marca=''`** (valor presente pero falsy, no key ausente) → el default `meta.name` nunca se usaba y quedaba un nombre vacío. (L-10)

**Fix durable** (en `ScraperBICE._parsear_entry`): cadena `or` en vez de `.get` con default —
`nombre = (fields.get('Marca') or meta.get('name') or '').strip()` + `return None` si queda vacío. El source se auto-cura en el próximo cron.

**Cleanup quirúrgico** (L-04): removida la entrada ya presente de `beneficios.json` (931→930, BICE 67→66) y de `beneficios.csv` (en **binary mode** para no convertir CRLF→LF y ensuciar el diff: "1 file changed, 1 deletion(-)").

**Guard nuevo** (L-07): `verificar_salud.py` ahora **falla** si reaparece cualquier beneficio con `restaurante=''`.

**Verificado:** health check exit 0, 930/14, "OK: 0 beneficios con restaurante vacío", `/ver` ya no muestra la card, otros 13 bancos sin tocar. **Shipped:** commit `bb837b5`, tag `v1.4-bice-cleanup`. Render auto-redeployando.

### 3. Montos Scotiabank sábado verificados (RESUELTO — sin cambio de data)

Confirmado contra **fuente oficial Scotiabank + La Tercera/medios**: el descuento Shell sábado es **hasta $200/L con Visa Crédito vía App Shell, vigente junio 2026** (promo viva, no stale). El techo $200 calza con el tier top de la data. El desglose exacto de los tiers inferiores ($150/$100) está tras una SPA no parseable y **ningún medio lo contradice** → se mantiene `bencinas.json` como está, con el caveat documentado. No se tocó producción (cambiar tiers sin fuente autoritativa sería adivinar).

### 4. Santander desbloqueado sin browser (RESUELTO + shipped) — Opción B

**Causa raíz:** el scraper usaba Playwright (condenado a 0 en el cron de Render, L-01) y encima el WAF de Akamai bloqueaba. Descubrí que **Akamai da 403 a User-Agents de browser/python-requests, pero responde 200 a un UA estilo `curl/8.4.0`**, sirviendo el HTML SSR completo (`li.item`).

**Fix:** reescribí `ScraperSantander` de Playwright → `requests` con `User-Agent: curl/8.4.0`, **reutilizando `_parsear_item` tal cual** (sin tocar la lógica de parseo). Corre idéntico en local y en Render/cron.

**Merge quirúrgico** (patrón Falabella, L-04): tomé `beneficios.json` fresco de origin (854), quité los Santander viejos (0), inyecté los 77 frescos → **931 beneficios, 13 → 14 bancos**. Verifiqué que los otros 13 bancos no regresionaran (assertion `otros_ok` pasó).

**Verificado end-to-end:** health check `verificar_salud.py` exit 0; `/estadisticas` y `/ver` vía TestClient (con `with TestClient(app) as client:` para que dispare el startup) → 931/14, Santander renderiza con su logo, 0 URLs externas.

**Shipped:** commit `f1eec1a`, push `259dbb0..f1eec1a` en `origin/main`, tag `v1.3-santander-browserless`. Render auto-redeployando.

### 5. BancoEstado investigado y DIFERIDO (decisión D)

**Causa raíz:** la URL de campaña devuelve un **soft-404 de Akamai Edge a TODO cliente, incluso con UA de browser real** (no solo anti-bot). Verifiqué todos los endpoints AEM (`.model.json` / `.infinity.json` / `jcr:content.json` / `.1.json`): todos dan el mismo soft-404 (`<title>BancoEstado | Página no encontrada</title>`). Señal clave: la **campaña estacional ("mes de sabores") ya no existe** en esa ruta.

**Por qué se difiere:** la Opción B (endpoint sin browser) no rinde porque no hay datos que extraer. Pagar un browser service (Opción C) tampoco sirve hasta que haya una campaña viva. **D (diferir) no regresiona** porque BancoEstado ya estaba en 0.

**Cuándo retomar:** cuando BancoEstado relance su mes de sabores. Recién ahí, si aparece anti-bot real, evaluar C.

---

## ⚠️ Pendiente de DECISIÓN de Fernando (0 decisiones abiertas)

> Sin decisiones pendientes. Todo lo que esperaba tu OK ya se resolvió esta jornada.

> **Resueltos esta jornada (ya no esperan decisión):** ~~Caches de disco~~ → limpieza del **tier seguro** ejecutada con tu OK: **~5.7 GB liberados** (npm 2.8G, uv 1.5G, puppeteer 535M, ms-playwright 520M, pip 265M). **HuggingFace (5.3G) y Docker (2.2G) NO se tocaron** por decisión explícita ("sin HuggingFace"): HuggingFace son modelos vivos de los RAG 04/05; Docker necesita el daemon prendido para `docker system prune` seguro. ~~6 cards sin `descuento_texto`~~ → híbrido shipped (`v1.6-cards-completas`): Security recupera dato real + Itaú/Falabella etiqueta genérica. ~~calidad 100% (4 tiers)~~ → shipped (`v1.5-calidad-100`). ~~montos Scotiabank sábado~~ → verificados, $200/L confirmado vs fuente oficial. ~~Card basura BICE~~ → fix durable + cleanup + guard (`v1.4-bice-cleanup`).

---

## ✅ Lo siguiente (prioridades de la próxima sesión)

- [ ] **Verificar en producción real** (tras redeploy de `v1.6`) que `/ver` muestra los 929 beneficios + Santander con logo, las 4 cards Security con "Menú Priceless" e Itaú/Falabella con "Beneficio exclusivo" (ya **ninguna** card vacía), `/ver/bencinas` el Scotiabank sábado, y `/beneficios/{id}` no devuelve cruzados (0 ids duplicados).
- [x] ~~Limpiar caches de disco~~ → hecho (tier seguro, ~5.7 GB liberados; HuggingFace + Docker intactos por decisión). Si en el futuro hace falta más espacio: Docker (2.2G) prendiendo el daemon + `docker system prune`.
- [ ] **BancoEstado**: monitorear relanzamiento de campaña (único banco faltante para los 15).
- [ ] (Backlog) Wirear `verificar_salud.py` al build de Render como pre-deploy gate.
- [ ] (Backlog) Migración Pinecone → pgvector; unificar las 2 carpetas de docs natural duplicadas.
- [ ] (Backlog) Persistir `user_flow` (estado conversacional del bot) — hoy en memoria, se pierde con restart de Render.

> ✅ Cerrado esta jornada: 6 cards sin `descuento_texto` resueltas (híbrido, `v1.6-cards-completas`) — lección **L-14** (recuperar dato adyacente + red de seguridad genérica en `__post_init__`). Antes: 4 tiers de calidad-100 shipped (`v1.5`); lecciones **L-11** (unicidad de ids / disambiguar-no-borrar), **L-12** (cleanup vía round-trip del dataclass + `csv.DictWriter` CRLF-safe) y **L-13** (verificar migración scraper en vivo) documentadas. L-08 promovida a workspace (L-W14), L-10 documentada.

---

## 🚧 Bloqueado por

**Solo BancoEstado**, y no por causa técnica resoluble: su campaña estacional no existe en el sitio. Diferido hasta relanzamiento. Todo lo demás (14 bancos) está live.

---

## 💡 Decisiones tomadas en esta sesión

- **Unicidad de ids: disambiguar, no borrar.** Un id colisionado puede ser dup exacto (mismo objeto) o dos ofertas distintas con mismo slug. Borrar perdería una oferta real → solo se dropea el dup **exacto** (firma idéntica salvo `fecha_scrape`); las colisiones reales se suffijan `_2/_3` preservando la 1ra ocurrencia. (L-11)
- **Cleanup por round-trip del dataclass real, no edición a mano.** Para tener paridad con el cron, el cleanup se hizo reconstruyendo `Beneficio(**d)`/`DescuentoBencina(**d)` (lossless: `__post_init__` preserva `fecha_scrape`, verificado 0 cambios en round-trip de control) y regenerando el CSV con `csv.DictWriter` (byte-idéntico, CRLF-safe). El bloat CRLF de L-10 era del text-mode manual, NO del módulo `csv`. (L-12)
- **Verificar la migración scraper EN VIVO antes de shippear.** El health check prueba data-at-rest, no que el fetch reescrito traiga datos; corrí `ScraperItau`→68 y `ScraperLiderBCI`→11 contra el sitio real antes del push (el modo de falla L-01 es silent 0 en el cron, invisible para un check de archivo). (L-13)
- **BancoEstado se deja en Playwright a propósito:** banco diferido (campaña caída, L-09), dormido, retorna 0; migrarlo ahora sería trabajo sobre un scraper sin datos. Se retoma cuando relance campaña.
- **6 cards sin `descuento_texto`: resolución híbrida (recuperar dato real donde existe, etiqueta genérica donde no).** Para Security, la fuente SÍ trae el texto en un campo adyacente (`field_titulo_caluga` = "Menú Priceless") → se recupera el dato real (Opción A, toca solo la clase del banco). Para Itaú+Falabella no hay dato recuperable → red de seguridad genérica "Beneficio exclusivo" en `Beneficio.__post_init__`, el **único chokepoint que corre en TODA construcción** (cron + cleanup) → ninguna card —presente o futura, de cualquier banco— puede renderizar vacía. El fallback corre **después** del parser de Security, así que no pisa el dato real. Borrar cards reales se descartó (tienen restaurante, no son basura fantasma como BICE). (L-14)
- **BICE: fix en el source + cleanup quirúrgico + guard, no parche:** la raíz era `dict.get` con default falsy, así que se arregló en la clase scraper (auto-cura) en vez de solo borrar la card. El cleanup del JSON/CSV fue quirúrgico (L-04) y el CSV se editó en binary mode para no romper los CRLF. Cada fix que "se puede volver a romper" se convierte en aserción del health check (L-07/L-10).
- **Scotiabank sábado: NO tocar la data sin fuente autoritativa.** Verifiqué el techo $200/L contra fuente oficial; los tiers inferiores no los contradice ningún medio y están tras una SPA. Cambiarlos a ciegas sería adivinar y podría empeorar el dato → se mantiene con caveat documentado.
- **Santander vía B (browserless), no A ni C:** antes de montar Chromium en Render o pagar un browser service, probé la matriz de User-Agents y encontré que `curl/8.4.0` pasa el WAF de Akamai. $0, robusto, consistente con Falabella. (L-08)
- **Reutilizar `_parsear_item` sin tocarlo:** solo reescribí el método `scrapear()` (Playwright → requests); la lógica de parseo ya era correcta. Cambio mínimo, regla del proyecto (tocar solo lo necesario).
- **Merge quirúrgico sobre data fresca de origin**, no pushear mi copia completa — evita regresionar los otros 13 bancos (L-04).
- **BancoEstado: diferir (D), no insistir:** test discriminante (UA de browser real → sigue soft-404) probó que NO es anti-bot sino campaña caída. Ningún browser service lo resuelve hasta que haya datos. (L-09)

---

## 📝 Notas sueltas de esta sesión

- **Akamai UA matrix:** `banco.santander.cl` da 403 a UA de browser/python pero **200 a `curl/8.4.0`**. Probar la matriz de UAs (python-requests → UA vacío → curl → Chrome) ANTES de reachear por un browser. (L-08)
- **TestClient no dispara startup** salvo que lo uses como context manager (`with TestClient(app) as client:`). Mi primer test dio /beneficios=0 por esto, NO por la data — era bug del test.
- **`/beneficios` capa `limit` en `le=100`** → verifiqué los 931 vía `/estadisticas` (agrega todo) y `/ver` (render completo server-side).
- **Mojibake en el soft-404 de BancoEstado** (`PÃ¡gina no encontrada`, doble-encoding) me dio un falso negativo en un probe; confirmé leyendo el `.html` crudo.
- El `.git` del proyecto en Drive sigue poco confiable para red — usé el clone `/tmp/micartera-clone` para commit/push/tag.
- **`beneficios.csv` usa CRLF.** Editarlo en text-mode de Python convierte CRLF→LF en todo el archivo y ensucia el diff (945/968 líneas falsas). Para remover 1 fila: leer bytes, `split(b'\r\n')`, filtrar, `join`, escribir en binary mode → diff limpio "1 file changed, 1 deletion(-)". (L-10)
- **`dict.get(k, default)` NO aplica el default si la key existe con valor falsy (`''`)** — la raíz del bug BICE. Usar cadena `a or b or c` cuando el valor puede venir presente-pero-vacío. (L-10)

---

## 📊 Métricas actuales del sistema

| Métrica | Valor | Fecha |
|---------|-------|-------|
| Beneficios en producción | **954** (14 bancos); Falabella preservado por la red de seguridad en la corrida del cron de hoy | 2026-06-22 |
| Banco Falabella | **95** (geo-fence del cron; restaurado desde Chile + red de seguridad) | 2026-06-22 |
| Bencinas (descuentos combustible) | 31 (no afectado) | 2026-06-22 |
| IDs duplicados | **0** en beneficios.json y bencinas.json | 2026-06-22 |
| Logos referenciados | 31, 100% self-hosted, 0 URLs externas | 2026-06-01 |
| Bancos activos / bloqueados | 14 / 1 (solo BancoEstado, diferido) | 2026-06-22 |
| Chequeo experto del cron | ✅ `chequeo_bancos.py`: clasifica por banco (OK/DEGRADADO/CAÍDO) + reintentos + preservar caídos + **email con estado por banco** (L-16/L-17) | 2026-06-22 |
| Health check `verificar_salud.py` | ✅ exit 0 (pisos centralizados en `chequeo_bancos`; guards: ids dup, crash-parity, pisos/banco, mojibake, `restaurante=''`, `descuento_texto=''`) | 2026-06-22 |
| URL producción | api-beneficios-chile.onrender.com | activa |
| Refresco local (Chile) | ✅ `refrescar_local.ps1` + Tarea Windows `MiCartera-Refresco` (diaria 9:00). Scrapea los 15 desde Chile sin geo-fence → push. `diagnosticar.py` guarda HTML de caídos | 2026-06-22 |
| Auditoría credibilidad 14 bancos | ✅ 8 OK · 5 sin-mapa (datos buenos, aviso agregado) · Santander/Consorcio → "Beneficio exclusivo" honesto (L-19) | 2026-06-22 |
| Banco Consorcio | **50% devolución** (Casacostanera, tope $40.000, hasta 31/07/2026) — leído de la promo, trazable | 2026-06-22 |
| Mail del refresco local | ✅ "por sí o por no" diario + detallado + asunto "TODO OK"/"REVISAR" (requiere GMAIL_USER + GMAIL_APP_PASSWORD locales) | 2026-06-22 |
| Aprendizaje del sistema | ✅ `aprendizaje.py` + `historial.json`: nivel normal por banco, pisos adaptativos, alerta de tendencia (estadística sobre el histórico, no ML neuronal) (L-20) | 2026-06-22 |
| Último commit shipped | **1d8622d** (aprendizaje) · `02cc9f1` (mail detallado) · `82b6951` (Consorcio 50%) · `3e94879` | 2026-06-22 |

---

**Cómo mantener este archivo:**

Al final de cada sesión con Claude Code, pídele:

> "Antes de cerrar, actualízame el ESTADO.md con lo que avanzamos hoy y qué sigue."

Al inicio de cada sesión, abrir este archivo PRIMERO.

# Proyecto MiCartera — Scrapers de beneficios bancarios + Bot WhatsApp

@../CLAUDE.md
@../LECCIONES.md
@./LECCIONES_APRENDIDAS.md
@./ESTADO.md

---

## 🎯 Contexto del proyecto

Sistema que scrapea descuentos bancarios en restaurantes de Chile (15 bancos) y los expone vía página web interactiva, un **bot de menú por WhatsApp + Telegram** y API REST. Es el producto **MiCartera** del workspace de Fernando.

**Producto/Cliente:** MiCartera (producto propio)
**Estado:** 🟢 producción (según INDEX del workspace)
**Vinculado al workspace `Claude_code`:** sí

---

## ⚙️ Stack específico de este proyecto

Stack canónico del workspace con variaciones:

- **Backend:** Python 3.9+ con FastAPI + Uvicorn (también un `whatsapp_bot.py` legacy en Flask)
- **Scraping:** `requests` + `beautifulsoup4` + `lxml` (Playwright disponible pero no usado)
- **Embeddings + RAG:** OpenAI `text-embedding-3-small` + **Pinecone** (excepción legacy al estándar workspace que usa pgvector — heredado de versión inicial)
- **LLM:** GPT-4o-mini (OpenAI) SOLO para el buscador IA de la web (`/rag`). ⚠️ **El bot de mensajería NO usa IA** — es **menú guiado** (gratis, sin OpenAI). Decisión de Fernando (2026-08-04): sin LLM por ahora. Opción futura: híbrido menú + RAG para preguntas abiertas.
- **Bot:** Twilio + **WhatsApp + Telegram** — el MISMO bot de menú en ambos canales (endpoints `/webhook` y `/telegram`); **4 opciones**: 1 restaurantes (día→banco), 2 bencinas (día), 3 cuotas sin interés (banco), 4 otros beneficios (banco). Bot Telegram: `@Mi_cartera_descuentos_Bot`. Firma Twilio opt-in por `TWILIO_AUTH_TOKEN`; Telegram opt-in por `TELEGRAM_BOT_TOKEN`.
- **Deploy:** Render (`render.yaml` con 2 servicios)
- **Storage:** archivos planos — `beneficios.json` (~885 beneficios de restaurantes, la fuente de verdad de `/ver`) + `beneficios.csv` + `beneficios_otros.json` (beneficios de tarjeta NO-restaurante, dataset SEPARADO; ~24 verificables mostrados en `/ver/beneficios`, filtrados de 228 candidatos) + `bencinas.json` (con `confianza` + `url_fuente` por dato, re-curado desde fuente oficial) + `cuotas_sin_interes.json`

---

## 🚫 Reglas específicas de este proyecto

- **Pinecone es legacy aquí** — no replicar en proyectos nuevos. El estándar del workspace es pgvector con HNSW.
- **15 clases scraper** en `beneficios-bancarios-chile/scrapers.py` (~3800 líneas). Si un banco cambia su sitio, tocar solo la clase específica del banco afectado, no el orquestador.
- **`api.py` mezcla 3 responsabilidades** (~3200 líneas: API + páginas web HTML embebidas `/ver` (restaurantes), `/ver/beneficios` (otros), `/ver/bencinas`, `/ver/cuotas` + webhook WhatsApp). No "limpiar" / refactorizar sin avisar — el monolito es intencional para deploy simple. Las vistas comparten `_render_deals()` (endpoints finos por vista).
- **Sección "otro" (beneficios NO-restaurante) — apartado `/ver/beneficios` DESPLEGADO:** el modelo `Beneficio` tiene un campo **`seccion`** (`"restaurante"` por defecto | `"otro"`). Santander y Consorcio marcan como `"otro"` sus beneficios que no son restaurante (retail, viajes, salud, entretención); el orquestador los separa y los guarda en **`beneficios_otros.json`** (dataset aparte, NO entran a `beneficios.json` ni afectan pisos/red de seguridad). El apartado web **`/ver/beneficios` YA EXISTE y está en producción** (misma lógica filtrable que `/ver`); muestra los **~24 verificables** (con % real), filtrados de 228 candidatos ("si no está chequeado, mejor no mostrar"). ⚠️ **NUNCA tocar `/ver` (restaurantes) al trabajar en `/ver/beneficios`** — son datasets y endpoints separados a propósito ("lo que ya tenemos está perfecto", Fernando).
- **Trazabilidad + filtros dinámicos (ago-2026):** cada dato de bencina lleva `confianza` + `url_fuente` (re-curado desde fuente oficial; agregador ≠ fuente). Los filtros de día en `/ver` y `/ver/beneficios` son **dinámicos** (atenúan/bloquean los días sin resultados). Sin data para una sección → "estamos confirmando descuentos". La **guardia de madrugada** vigila ambos (trazabilidad + bugs de página).
- **El código vive en sub-carpeta `beneficios-bancarios-chile/`**, no en la raíz. La raíz solo tiene documentación y archivos exportados.
- **NO regenerar `beneficios.json`** sin avisar — el scrape completo de 15 bancos tarda y puede romper si algún banco está caído.
- **⚠️ DESPLEGAR NO ES PUSHEAR (L-44/L-46) — la regla que más caro sale olvidar.** La app carga
  `beneficios.json`, `beneficios_otros.json`, `bencinas.json` y las cuotas **en MEMORIA al bootear**.
  Un `git pull` en el VPS **no despliega nada** si el servicio no reinicia: el 2026-09-02 producción
  llevaba **3 días** sirviendo datos del 30-ago con el repo ya en el 1-sep. Para desplegar se corre
  **`deploy_vps.sh`** (pull + restart + verificación de que lo servido quedó al día). Para saber qué
  está sirviendo producción: `curl -s https://datalab-api.duckdns.org/estadisticas` →
  **`fecha_datos`** (de cuándo es el dato) y **`version_commit`** (qué commit corre). ⚠️ `ultimo_scrape`
  NO es la fecha del scrape, es la hora de ARRANQUE de la app (trampa vieja, L-15). El guard
  **ACID-DEPLOY** de la guardia avisa si producción se queda >2 días atrás del repo.
- **`revision_madrugada.py` (guardia de madrugada):** convierte cada bug conocido en un check automático contra producción + datos; corre en `revision_madrugada.yml` (~03:00 Chile) y avisa por mail solo si algo reaparece. El catálogo de bugs de página vive en **`TUNING_PAGINAS.md`** (fine-tuning operativo); al agregar un bug ahí, agregar también su guard en `revision_madrugada.py`.

---

## 📂 Estructura del proyecto

```
01.Scraping y bot descuentos/   ← raíz del proyecto (nombre legacy con espacios)
├── CLAUDE.md                   ← este archivo
├── README.md
├── ESTADO.md
├── LECCIONES_APRENDIDAS.md
├── HISTORIAL_CONSTRUCCION.md
├── ENTREGA_FINAL.md
│
├── 00.Información_propia_explicación/   ← docs HTML lenguaje natural (ya existían pre-migración)
│   ├── 01_resumen_proyecto.html
│   ├── 02_arquitectura_sistema.html
│   ├── 03_scrapers_detalle.html
│   ├── 04_api_y_web.html
│   ├── 05_bot_whatsapp_y_bencinas.html
│   ├── 06_precios_combustible.html
│   ├── Memoria_Beneficios_Bancarios.docx
│   └── Memoria_Beneficios_Bancarios.pdf
│
├── 00.Informacion_proyecto/    ← duplicado legacy (subset de la anterior)
│
├── docs/                       ← docs técnica (creada en migración)
│   ├── 01_contexto.md
│   ├── 02_arquitectura.md
│   ├── 03_decisiones.md
│   └── 04_runbook.md
│
├── beneficios-bancarios-chile/ ← código real del sistema (sub-proyecto)
│   ├── api.py                  ← FastAPI: API + web + bot WhatsApp
│   ├── scrapers.py             ← 15 clases scraper + orquestador + red de seguridad
│   ├── chequeo_bancos.py       ← pisos + estado por banco + generador del mail (2026-06)
│   ├── aprendizaje.py          ← memoria + pisos adaptativos + tendencias (2026-06)
│   ├── verificar_salud.py      ← health check (gate de calidad pre-publicación)
│   ├── diagnosticar.py         ← guarda el HTML de bancos caídos (2026-06)
│   ├── refrescar_local.ps1     ← refresco diario desde Chile, Tarea Windows (2026-06)
│   ├── revision_madrugada.py   ← guardia de madrugada: re-chequea bugs conocidos vs prod (2026-07)
│   ├── deploy_vps.sh           ← DESPLIEGUE: pull + restart + verifica lo servido (2026-09)
│   ├── whatsapp_bot.py         ← bot legacy Flask (sin IA)
│   ├── upload_pinecone.py      ← vectorización a Pinecone
│   ├── beneficios.json         ← ~885 beneficios de restaurantes (fuente de verdad de /ver)
│   ├── beneficios_otros.json   ← dataset SEPARADO de /ver/beneficios: tarjeta NO-restaurante (seccion="otro"); ~24 verificables mostrados (de 228 candidatos), Santander+Consorcio
│   ├── beneficios.csv          ← export CSV
│   ├── bencinas.json           ← data extra: precios combustibles
│   ├── cuotas_sin_interes.json ← campañas de cuotas sin interés del mes (curado mensual)
│   ├── historial.json          ← MEMORIA del aprendizaje, 1 snapshot/corrida (2026-06)
│   ├── TUNING_PAGINAS.md        ← fine-tuning operativo de las páginas (síntoma→causa→fix)
│   ├── COMO_FUNCIONA.md         ← guía en lenguaje natural de cómo funciona todo el sistema
│   ├── .github/workflows/       ← scraper.yml (CRON DIARIO scrape+chequeo+mail) · revision_madrugada.yml (guardia ~03:00) · keepalive.yml (ping anti-sleep)
│   ├── render.yaml · requirements.txt · README.md · ARCHITECTURE.md · SETUP_GUIDE.md
│   └── static/logos/           ← logos bancos
│
├── Archivo.zip                 ← backup
└── beneficios.json             ← copia raíz (legacy)
```

---

## 🚀 Cómo correr

```bash
# Setup local (Windows, venv local NO en Drive)
cd "G:\Mi unidad\Programación\Claude_code\01.Scraping y bot descuentos\beneficios-bancarios-chile"
python -m venv %USERPROFILE%\.venvs\micartera_win
%USERPROFILE%\.venvs\micartera_win\Scripts\activate
pip install -r requirements.txt

# Correr API + web + webhook local
uvicorn api:app --reload --port 8000

# Re-scrapear bancos (cuidado: tarda y depende de sitios externos)
python scrapers.py

# Re-vectorizar para RAG (después de scrape)
python upload_pinecone.py
```

---

## 🌐 Recursos externos

- **URL en producción:** **https://datalab-api.duckdns.org/ver** (VPS propio; Render quedó suspendido — ver sección "MUDÓ AL VPS" abajo)
- **Repo Git:** https://github.com/fernandoestay-create/beneficios-bancarios-chile
- **Cliente:** Fernando Estay (producto MiCartera propio)
- **Servicios externos:** VPS Contabo (hosting, systemd `cartera.service` tras Caddy), Pinecone (vector DB), OpenAI (embeddings + GPT-4o-mini), Twilio (WhatsApp), Telegram

---

## 📋 Para el próximo Claude que abra este proyecto

Antes de empezar a trabajar:

1. ✅ Leer `ESTADO.md` para saber dónde quedó la última sesión
2. ✅ Leer `LECCIONES_APRENDIDAS.md` para no repetir errores
3. ✅ Revisar `beneficios-bancarios-chile/README.md` para entender el sistema técnico
4. ✅ Recordar: este proyecto usa Pinecone (legacy), no pgvector. No replicar en proyectos nuevos.
5. ✅ Si vas a hacer un cambio significativo, actualizar `HISTORIAL_CONSTRUCCION.md` al cerrar

---

## 📝 Notas de migración al workspace (2026-05-26)

- El proyecto tiene **2 carpetas de documentación natural** que coexisten:
  - `00.Información_propia_explicación/` (con tildes, canónica del workspace) — contiene 6 HTML + DOCX + PDF
  - `00.Informacion_proyecto/` (sin tildes, legacy) — subset de la anterior
  - **No se borró ninguna** en la migración. Decisión humana pendiente: unificar o mantener.
- No se creó `00.Información_propia_explicación/index.md` ni `build_html.py` porque la docs natural ya está en HTML estático. Convertir a flujo `.md → .html` queda como tarea futura si Fernando quiere editar la docs natural en `.md`.
- El código real vive en `beneficios-bancarios-chile/`. La docs técnica ahí (`README.md`, `ARCHITECTURE.md`, etc.) NO se modificó.

**Última actualización:** 2026-09-02 (producción llevaba **3 días congelada**: el VPS servía datos del 30-ago porque el `git pull` no reinicia el servicio y la app carga los JSON en memoria al bootear. Fix: `/estadisticas` ahora expone **`fecha_datos`** y **`version_commit`**, guard **ACID-DEPLOY** en la guardia, y **`deploy_vps.sh`** en el repo (pull + restart + verificación). Además: cuotas curadas a **septiembre 2026** (12 bancos / 32 campañas; Santander y BCI marcados honestos porque aún no rotan), refresco corrido a mano → **936 beneficios**, Itaú recuperado a 48 (falsa alarma, rotación de campaña), aviso de corrida incompleta en el refresco local, y **L-46**. ⚠️ **PENDIENTE: correr `deploy_vps.sh` en el VPS** — hasta que eso pase, nada de esto está en producción; no hay SSH desde el PC de Fernando)
_(Anterior 2026-08-31: auditoría ácida + fixes A+B, commit `17b6a6d`.)_
_(Anterior 2026-08-04, v2.1: bot multicanal WhatsApp+Telegram de 4 opciones, firma Twilio, pipeline bencina desbloqueado L-37, apartado "Otros beneficios", filtros dinámicos, RAG revectorizado, L-31→L-40.)_

---

## ⚠️ MICARTERA SE MUDÓ DE RENDER AL VPS PROPIO (2026-08-23)

| | Antes | Ahora |
|---|---|---|
| **URL** | `api-beneficios-chile.onrender.com` | **`https://datalab-api.duckdns.org`** |
| **Dónde** | Render free (Oregon) | VPS Contabo `169.58.222.109` |
| **Cómo** | plan free, dormía | servicio systemd `cartera.service` tras Caddy |
| **Respuesta** | **32 s** dormido | **2,0 s** |
| **HTTPS** | de Render | Let's Encrypt vía Caddy, renovación automática |

- **Código:** `~/servicios/beneficios-bancarios-chile` · **entorno:** `~/.venvs/cartera`
- **Secretos:** `~/servicios/cartera.env`, permisos 600, fuera de git
- **Registros:** `journalctl --user -u cartera`

⚠️ **El webhook de Telegram se registró a mano.** La app lo hace al arrancar, pero no lo
hizo; se forzó con `setWebhook`. Verificado: apunta a `/telegram` y sin errores. Si algún
día el bot deja de responder, **eso es lo primero que hay que mirar** —
`getWebhookInfo` — no los registros del servicio.

🔴 **PENDIENTE: reapuntar el Sandbox de Twilio** a
`https://datalab-api.duckdns.org/webhook`. Hasta que se haga, **el bot de WhatsApp no
responde**. *(L-38: ya pasó una vez que el Sandbox apuntaba al servicio equivocado y el
síntoma fue exactamente ese. Verificar con un mensaje real, no mirando la configuración.)*

🔴 **PENDIENTE: rotar el token del bot de Telegram.** Quedó visible en pantalla durante la
migración. BotFather → `/revoke`.

**Render quedó SUSPENDIDO, no borrado.** El `render.yaml` sigue en git: volver exige solo
repegar los secretos `sync:false`.

📋 **Registro único de tareas:** `~/.claude/CLAUDE.md`.

---

## 📱 WhatsApp — el Sandbox de Twilio caduca cada 72 horas

**Si el bot deja de responder y el síntoma es este mensaje:**

> ⚠️ Your number `whatsapp:+569…` is not connected to a Sandbox.

**no está roto: caducó la membresía.** Se renueva mandando un WhatsApp

| | |
|---|---|
| **al número** | `+1 415 523 8886` |
| **con el texto** | `join matter-color` |

Dura **72 horas** y se puede repetir sin límite. *(Anotado el 2026-08-24 porque no estaba
escrito en ninguna parte y hubo que ir a buscarlo a la consola de Twilio.)*

**Antes de culpar al Sandbox**, comprobar que el webhook sigue bien apuntado — son fallos
distintos con el mismo síntoma:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://datalab-api.duckdns.org/webhook
```

Debe dar **403** (rechaza lo no firmado). Un **200** ahí significa que la validación de firma
está apagada, no que todo esté bien (L-21 de Hermes: una variable vacía la apaga en silencio).

⚠️ El Sandbox es para pruebas. Para uso real sin caducidad hay que solicitar un **número de
WhatsApp Business** propio en Twilio.

# Cómo funciona MiCartera — guía completa

> **Para qué es este documento:** explicar, en lenguaje claro, cómo funciona todo el
> sistema tal como quedó al 2026-06-22. Si abrís esto dentro de 6 meses y no te
> acordás de nada, acá está todo.
> **Última actualización:** 2026-06-22

---

## 1. Qué es MiCartera

Un sistema que **scrapea descuentos bancarios de restaurantes en Chile** (15 bancos),
los limpia, y los muestra en una web pública + un bot de WhatsApp con IA. También
trae **precios y descuentos de bencina**.

- **Web pública:** https://api-beneficios-chile.onrender.com/ver (restaurantes) y `/ver/bencinas`.
- **Datos:** ~950 beneficios de 14 bancos activos + 31 descuentos de bencina.
- **Costo de operación:** ~$0 (todo en planes gratuitos: GitHub Actions, Render, tu PC).

---

## 2. Las piezas del sistema

| Pieza | Dónde corre | Qué hace |
|-------|-------------|----------|
| **`scrapers.py`** | — | 15 clases scraper (una por banco) + el orquestador que las corre |
| **`chequeo_bancos.py`** | — | Define el piso de cada banco, clasifica el estado (OK/degradado/caído/preservado), arma el mail |
| **`aprendizaje.py`** | — | Memoria del sistema: guarda el histórico y calibra los pisos solo |
| **`verificar_salud.py`** | — | Chequeo de calidad: si algo está mal, NO se publica |
| **`api.py`** | Render (nube) | La web + la API + el bot de WhatsApp (todo junto) |
| **Cron** (`.github/workflows/scraper.yml`) | GitHub Actions (nube, USA) | Corre diario: scrapea, chequea, **manda el mail**, publica |
| **Refresco local** (`refrescar_local.ps1`) | Tu PC (Chile) | Corre diario: trae los bancos geo-fenceados frescos (ej. Falabella) |

---

## 3. Cómo se actualizan los datos (hay DOS fuentes)

El sistema tiene **dos procesos** que actualizan los datos, y se complementan:

### A. El cron en la nube (GitHub Actions) — corre diario ~07:00 Chile
1. Scrapea los 15 bancos **desde un servidor en USA**.
2. Corre el chequeo experto por banco.
3. Sube los datos al buscador con IA (Pinecone) para el bot.
4. Publica (`git push` → Render actualiza la web).
5. **Te manda el mail diario** con el estado de cada banco.

**Limitación:** algunos bancos (ej. **Banco Falabella**) sólo muestran sus descuentos
a IPs chilenas (*geo-fencing*). Desde USA, el cron los ve en 0. Por eso existe la
segunda fuente ↓

### B. El refresco local (tu PC) — corre diario 09:00
1. Scrapea los 15 bancos **desde tu IP chilena** (donde NO hay geo-fence).
2. Mismo chequeo + publica.
3. Así **Falabella y cualquier banco geo-fenceado quedan frescos**.
4. NO manda mail (de eso se encarga el cron).

> **En criollo:** el cron hace el trabajo pesado y te avisa por mail; tu PC sólo
> rellena lo que el cron no puede ver desde afuera de Chile.

---

## 4. El chequeo experto por banco

En cada corrida, **cada banco se compara con su "piso"** (el mínimo esperado de
ofertas) y se clasifica:

| Estado | Qué significa | En el mail |
|--------|---------------|------------|
| ✅ **OK** | Trajo lo normal o más | verde |
| ⚠️ **DEGRADADO** | Trajo menos del piso, o cayó respecto a su histórico | ámbar — REVISAR |
| 🔴 **CAÍDO** | Trajo 0 y **no** había datos previos que conservar | rojo — REVISAR |
| 🔵 **PRESERVADO** | Trajo 0 pero **sí** había datos previos (geo-fence/caída) → se conservan | azul, informativo, NO es alarma |

**El piso no es fijo: se aprende.** Ver sección 6.

---

## 5. La red de seguridad (lo más importante)

**Regla de oro del sistema: ningún banco puede desaparecer de la web en silencio.**

Si un banco trae 0 en una corrida pero tenía datos antes, el sistema **conserva los
datos previos** (no los borra) y lo marca como **PRESERVADO**. La web sigue mostrando
ese banco; el usuario no nota nada. Y el mail te informa.

Esto nació de un incidente real: el 2026-06-20, Falabella desapareció de la web porque
el cron (USA) lo vio geo-fenceado y borró sus 97 descuentos sin avisar. Ahora eso **no
puede volver a pasar**.

---

## 6. El aprendizaje (cómo se vuelve más inteligente)

Cada corrida deja un "snapshot" en **`historial.json`** (cuántas ofertas trajo cada
banco). Con ese histórico, el sistema:

- **Aprende el nivel normal** de cada banco (mediana de las últimas 12 corridas).
- **Ajusta el piso solo**: si BCI crece de 60 a 130 ofertas, su piso sube solo.
- **Detecta tendencias**: si un banco cae bajo el 70% de su nivel habitual, te avisa
  **aunque todavía no llegue a 0** (alerta temprana).

> **Importante / honesto:** esto NO es una "inteligencia artificial que se entrena
> sola". Es estadística simple sobre tu propio histórico — verificable, sin caja negra.
> Cuantas más corridas acumula, mejor calibra. No reescribe scrapers solo (eso es
> peligroso); para eso te avisa y lo arregla un humano.

---

## 7. El mail diario "por sí o por no"

Te llega **todos los días**, haya o no problemas, para confirmarte que el sistema corrió.

- **Asunto:** arranca con `✅ TODO OK · MiCartera 14/14 bancos · …` (verde) o
  `⚠️ REVISAR · MiCartera — …` (rojo). Lo marcás de un vistazo.
- **Cuerpo:** tarjetas de resumen + el estado de cada banco (trajo vs piso) + una
  sección "cómo funciona".
- **Quién lo manda:** el cron, con las credenciales de Gmail que están guardadas
  cifradas en GitHub (Secrets). No necesitás configurar nada.

---

## 8. ¿Qué pasa si un banco se cae? (tu única intervención posible)

| Causa | ¿Se arregla solo? | ¿Qué hacés vos? |
|-------|-------------------|-----------------|
| **Transitorio** (timeout, sitio lento) | ✅ Sí — 3 reintentos automáticos | Nada |
| **Geo-fence / bloqueo por IP** | ✅ Sí — el refresco desde Chile lo trae | Nada |
| **El banco rediseñó su web** | ❌ No — hay que tocar el código del scraper | El mail te avisa → me decís "arreglá el scraper de X" → lo arreglo en minutos |

En los 3 casos **la web no se cae** (datos preservados) y **el mail te avisa**. El
sistema guarda el HTML del banco caído en `diagnostico/` para acelerar el arreglo.

---

## 9. Cómo mantenerlo / comandos útiles

**La tarea programada de Windows** (refresco local diario):
```powershell
schtasks /Query  /TN "MiCartera-Refresco"    # ver
schtasks /Run    /TN "MiCartera-Refresco"    # correr ahora
schtasks /Delete /TN "MiCartera-Refresco" /F # quitar
```

**Correr el scrape a mano** (desde el clone en disco local, no desde Drive):
```powershell
& "$env:USERPROFILE\micartera-clone\refrescar_local.ps1"
```

**Disparar el cron de la nube a mano:** GitHub → Actions → "Scraping Diario" → Run workflow.

> ⚠️ **Regla de oro de git:** el `.git` en Google Drive es inestable. Para push/pull
> siempre se usa el clone en disco local (`%USERPROFILE%\micartera-clone`), nunca el
> de Drive. (Lección L-03.)

---

## 10. Los archivos clave (mapa rápido)

```
beneficios-bancarios-chile/
├── api.py                 # web + API + bot WhatsApp (monolito intencional)
├── scrapers.py            # 15 scrapers + orquestador + red de seguridad
├── chequeo_bancos.py      # pisos, estados por banco, generador del mail
├── aprendizaje.py         # memoria + pisos adaptativos + tendencias
├── verificar_salud.py     # chequeo de calidad (gate antes de publicar)
├── diagnosticar.py        # guarda el HTML de bancos caídos
├── refrescar_local.ps1    # refresco diario desde Chile (tu PC)
├── beneficios.json        # los ~950 descuentos (la fuente de verdad de la web)
├── bencinas.json          # descuentos + precios de combustible
├── historial.json         # la MEMORIA del aprendizaje (1 snapshot por corrida)
└── .github/workflows/
    └── scraper.yml        # el cron diario (scrape + chequeo + mail)
```

---

## 11. Servicios externos

| Servicio | Para qué | Plan |
|----------|----------|------|
| **GitHub Actions** | El cron diario | Gratis (repo público) |
| **Render** | Hosting de la web/API | Gratis |
| **Pinecone** | Buscador con IA del bot (RAG) | Legacy del proyecto |
| **OpenAI** | Embeddings + GPT-4o-mini del bot | Pago por uso (centavos) |
| **Twilio** | WhatsApp del bot | Pago por uso |
| **Gmail** | El mail diario (vía SMTP, secret en GitHub) | Gratis |

---

## 12. Una línea para recordar

> **El cron te manda el mail diario y publica; tu PC mantiene Falabella fresco; la red
> de seguridad evita que algo desaparezca; el aprendizaje calibra los pisos solo. Tu
> única tarea es leer el mail — y avisarme sólo si un banco cambió su web.**

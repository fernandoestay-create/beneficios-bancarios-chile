# Cómo funciona MiCartera — guía completa

> **Para qué es este documento:** explicar, en lenguaje claro, cómo funciona todo el
> sistema tal como quedó al 2026-06-22. Si abrís esto dentro de 6 meses y no te
> acordás de nada, acá está todo.
> **Última actualización:** 2026-07-01

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

### A. El cron en la nube (GitHub Actions) — corre diario 09:00 Chile
1. Scrapea los 15 bancos **desde un servidor en USA**.
2. Corre el chequeo experto por banco.
3. Sube los datos al buscador con IA (Pinecone) para el bot.
4. Publica (`git push` → Render actualiza la web).
5. **Te manda el mail diario** con el estado de cada banco.

**Limitación:** algunos bancos (ej. **Banco Falabella**) sólo muestran sus descuentos
a IPs chilenas (*geo-fencing*). Desde USA, el cron los ve en 0. Por eso existe la
segunda fuente ↓

### B. El refresco local (tu PC) — corre diario 08:30 (antes del cron, para no chocar)
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
| ⚠️ **DEGRADADO** | Trajo menos del piso, o cayó respecto a su histórico | ámbar |
| 🔴 **CAÍDO** | Trajo 0 y **no** había datos previos que conservar | rojo |
| 🔵 **PRESERVADO** | Trajo 0 pero **sí** había datos previos (geo-fence/caída) → se conservan | azul, informativo, NO es alarma |

**El piso no es fijo: se aprende (sección 6).** Además, cada DEGRADADO/CAÍDO se
**auto-diagnostica**: el sistema mira el histórico y decide si **se resuelve solo**
(🔵 informativo — geo-fence, transitorio, o un recorte real de oferta ya estabilizado o
confirmado por ti) o si **requiere tu acción** (🔴 — algo nuevo, posible cambio de la
página del banco). Solo esto último dispara el ⚠️ REVISAR del asunto. Ver sección 6.

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

- **Aprende el nivel normal** de cada banco (mediana de las últimas 7 corridas ≈ 1 semana).
- **Ajusta el piso solo**: si BCI crece de 60 a 130 ofertas, su piso sube solo. Y si un
  banco recorta su campaña de forma sostenida (ej. Itaú 71→23), en ~1 semana el sistema
  reconoce ese nuevo nivel y deja de marcarlo en falso.
- **Detecta tendencias**: si un banco cae bajo el 70% de su nivel habitual, te avisa
  **aunque todavía no llegue a 0** (alerta temprana).
- **Auto-diagnostica cada problema** (`clasificar_incidente`): mirando el histórico,
  decide si un DEGRADADO/CAÍDO **se resuelve solo** (ya pasó antes y volvió, o lleva
  varios días estable en un nuevo nivel) o **requiere tu acción** (algo nuevo, sin
  estabilizar). El correo separa 🔵 "se resuelven solos" de 🔴 "requieren tu acción",
  así solo actúas sobre lo segundo.
- **Aprende de tu revisión** (`confirmar_nivel` → `niveles_confirmados.json`): cuando
  revisas una baja y confirmas que es real (el banco recortó su oferta, no es un bug),
  el sistema lo registra y **deja de alarmar** por ese banco mientras se mantenga en
  ~ese nivel — pero **vuelve a avisarte si cae aún más** (una caída nueva, distinta).
  Así tu conocimiento entra al sistema y no tienes que revisar lo mismo cada día.

> **Importante / honesto:** esto NO es una "inteligencia artificial que se entrena
> sola". Es estadística simple sobre tu propio histórico + tus confirmaciones —
> verificable, sin caja negra. Cuantas más corridas acumula, mejor calibra. No reescribe
> scrapers solo (eso es peligroso); si un banco cambia su página, te avisa con el
> diagnóstico listo y lo arregla un humano.

---

## 7. El mail diario "por sí o por no"

Te llega **todos los días a las 9:00 AM (Chile)**, haya o no problemas, para confirmarte que el sistema corrió. (El refresco local corre antes, a las 8:30, así el correo de las 9 ya sale con todo fresco.)

- **Asunto:** arranca con `✅ TODO OK · MiCartera 14/14 bancos · …` (verde) o
  `⚠️ REVISAR · MiCartera — …` (rojo). Lo marcas de un vistazo. Si un banco tuvo un
  problema pero es de los que se resuelven solos (o una baja real ya confirmada por ti),
  el asunto sigue verde y lo cuenta como "gestionado" (ej. `14/14 (1 gestionado)`) — no
  te alarma por algo que está bajo control.
- **Cuerpo:** tarjetas de resumen + el estado de cada banco (trajo vs piso) + una **sección de cuotas sin interés del mes** (resumen: bancos con campaña + las de 0% en todos los comercios + botón "Ver Cuotas", **con aviso automático si el mes quedó desfasado** — ej. "ya es julio y las cuotas son de junio, actualizar") + una sección "cómo funciona".
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
| **Keep-alive** | Ping cada 10 min para que la web no duerma (`keepalive.yml`) | Gratis |

> **Por qué la web a veces tarda en cargar:** Render (plan gratuito) suspende el
> servicio tras ~15 min sin visitas; la primera carga después tarda ~40s y se ve en
> blanco ("el link del mail no muestra info"). `keepalive.yml` la mantiene despierta
> en horario de uso (~06–19 Chile). De madrugada puede dormir — si entrás y se ve
> vacío, esperá ~40s y recargá. Para que **nunca** duerma: UptimeRobot (gratis, tu
> cuenta) o Render pago (~USD 7/mes).

---

## 12. El apartado de Cuotas sin interés (`/ver/cuotas`)

Además de restaurantes y bencina, hay un tercer apartado (botón **💳 Cuotas** en la barra): las **campañas de cuotas sin interés del mes**, por banco y categoría.

- **Qué muestra:** por cada banco, sus campañas agrupadas en categorías (todos los comercios, automotriz, educación, supermercados, salud, contribuciones), con el número de cuotas, las **condiciones de uso** (topes, tarjetas, exclusiones, CAE), la vigencia y un **link a la fuente oficial** del banco.
- **Filtros (todo dinámico):** arriba hay un **selector de mes** (junio a diciembre — cada campaña sale en los meses que está vigente, según su vigencia; abre en el mes en curso; los meses pasados quedan como "historia" atenuados), los **logos de los bancos** y chips de **categoría**. Al elegir un mes, **se filtra todo**: solo aparecen los logos de los bancos con campaña ese mes, los contadores del encabezado ("bancos con campaña" y "campañas") se recalculan, y la lista muestra las campañas vigentes. Todo se genera de `cuotas_sin_interes.json`, nada hardcodeado.
- **0% vs tasa preferencial:** distingue las que son realmente **sin interés (0%)** de las de **tasa preferencial** (automotriz/educación/salud suelen ser 0,79%–1,19% mensual, NO 0%). No se vende como "sin interés" lo que no lo es.
- **De dónde sale el dato:** de las **páginas oficiales de cada banco** (no de Chócale). Se leen desde tu PC (Chile) con `curl`, porque varias bloquean el acceso desde servidores fuera de Chile. Chócale se usa solo como **control de calidad**: se cruza contra lo oficial y se marca si hay inconsistencias.
- **Cómo se mantiene:** es **curado mensual** (no scraper automático — las campañas cambian de formato cada mes y un scraper daría datos errados). El dato vive en `cuotas_sin_interes.json`; a inicio de mes se re-cura verificando las fuentes oficiales.
- **Confianza por banco:** cada banco indica si su dato es "verificado en la fuente", "fuente oficial" o "secundaria". Ripley y Mach no ofrecen cuotas sin interés tipo campaña (se indica).

> **Honestidad:** el día 1 del mes las páginas de los bancos suelen mostrar aún el mes anterior; el dato del mes en curso se completa en los primeros días. Cada campaña enlaza a su fuente oficial para verificar. (Detalle: lección L-24.)

---

## 13. Una línea para recordar

> **El cron te manda el mail diario y publica; tu PC mantiene Falabella fresco; la red
> de seguridad evita que algo desaparezca; el aprendizaje calibra los pisos solo. Tu
> única tarea es leer el mail — y avisarme sólo si un banco cambió su web.**

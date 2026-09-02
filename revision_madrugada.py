#!/usr/bin/env python3
"""
Revisión de madrugada — guardia automática de las páginas de MiCartera.

Cada check corresponde a un bug REAL ya documentado (LECCIONES_APRENDIDAS.md +
TUNING_PAGINAS.md). Es el fine-tuning hecho código (patrón L-07): cada error resuelto
se convierte en un guard permanente, para que NINGUNO reaparezca en silencio.

Corre en el cron de madrugada (revision_madrugada.yml). Verifica dos capas:
  - RUNTIME: producción viva (curl a la URL) — página responde, JS sano, endpoints seguros.
  - DATA: el dato del checkout (beneficios.json) — nombres, filtros, integridad.
  - DEPLOY: que producción esté sirviendo ESE checkout y no una versión congelada (L-44).

OJO (L-44): el checkout NO es automáticamente "lo que se sirve". La app carga los JSON en
memoria al bootear, así que un git pull sin restart deja producción pegada en data vieja.
Ese punto ciego dejó producción 3 días atrasada sin que ningún guard lo viera (2026-09-02);
por eso existe ACID-DEPLOY, que compara lo servido contra el checkout.

Si algo falla → exit 1 → el workflow manda un correo de alerta con el detalle.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.request

# L-18: en Windows (cp1252) los emojis del reporte revientan con UnicodeEncodeError —
# y justo en la rama que imprime los FALLOS, o sea que el crash tapaba el hallazgo.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

URL = os.getenv("PROD_URL", "https://datalab-api.duckdns.org")
UA = {"User-Agent": "curl/8.4.0"}
ROOT = os.path.dirname(os.path.abspath(__file__))
fallos = []


def http(path, method="GET", body=None):
    req = urllib.request.Request(URL + path, headers=dict(UA), method=method)
    if body is not None:
        req.data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa
        return 0, str(e)[:80]


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn")


# ───────────────────── RUNTIME (producción viva) ─────────────────────
htmls = {}
for path in ["/ver", "/ver/bencinas", "/ver/cuotas"]:
    st, html = http(path)
    htmls[path] = html
    # L-13: la página tiene que responder de verdad, no un shell vacío.
    if st != 200 or len(html) < 5000:
        fallos.append(f"[L-13] {path} no responde OK (HTTP {st}, {len(html)} bytes)")

# L-21: "200 ≠ funciona". El <script> de cada vista tiene que compilar; una comilla mal
# escapada lo tumba entero y la página carga pero no renderiza NADA.
for path, html in htmls.items():
    if not html:
        continue
    for i, s in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
        f = os.path.join(tempfile.gettempdir(), f"chk_{i}.js")
        open(f, "w", encoding="utf-8").write(s)
        r = subprocess.run(["node", "--check", f], capture_output=True, text=True)
        if r.returncode != 0:
            fallos.append(f"[L-21] {path} <script>[{i}] JS ROTO — la página no renderiza: "
                          f"{r.stderr.strip()[:110]}")

# Seguridad (auditoría 2026-07): los endpoints destructivos deben seguir cerrados.
for path in ["/scrape/ejecutar", "/scrape/bencinas"]:
    st, _ = http(path, method="POST")
    if st != 404:
        fallos.append(f"[SEG] {path} = HTTP {st}, esperado 404 (endpoint destructivo REABIERTO)")
st, _ = http("/rag", method="POST", body={"pregunta": "hola"})
if st != 403:
    fallos.append(f"[SEG] /rag sin token = HTTP {st}, esperado 403 (perdió el guard ADMIN_TOKEN)")
# La firma Twilio (/webhook) debe rechazar lo NO firmado. Si TWILIO_AUTH_TOKEN quedara
# vacío, la firma se apaga en SILENCIO (fail-open) y el bot aceptaría requests falsas.
# Este guard lo caza. (auditoría 2026-08-31)
st, _ = http("/webhook", method="POST", body={"Body": "hola", "From": "whatsapp:+56900000000"})
if st != 403:
    fallos.append(f"[SEG] /webhook sin firma = HTTP {st}, esperado 403 (firma Twilio APAGADA: TWILIO_AUTH_TOKEN vacío?)")

# ───────────────────── DATA (lo que se sirve) ─────────────────────
try:
    d = json.load(open(os.path.join(ROOT, "beneficios.json"), encoding="utf-8"))
except Exception as e:  # noqa
    d = []
    fallos.append(f"[DATA] no se pudo leer beneficios.json: {e}")

n = len(d)

# L-29: nombres reales, no el genérico "Dcto en Restaurante" (Falabella).
gen = [b for b in d if re.match(r"^(dcto|descuento)s?\s+en\s+", b.get("restaurante") or "", re.I)]
if gen:
    fallos.append(f"[L-29] {len(gen)} beneficios con nombre genérico 'Dcto en Restaurante': "
                  f"{[b.get('id') for b in gen[:5]]}")

# L-10 / L-14: nada con restaurante ni descuento_texto vacío.
vac_r = [b for b in d if not (b.get("restaurante") or "").strip()]
vac_d = [b for b in d if not (b.get("descuento_texto") or "").strip()]
if vac_r:
    fallos.append(f"[L-10] {len(vac_r)} beneficios con restaurante vacío")
if vac_d:
    fallos.append(f"[L-14] {len(vac_d)} beneficios con descuento_texto vacío")

# L-11: ids únicos (un id repetido rompe /beneficios/{id} y el upsert a Pinecone).
ids = [b.get("id") for b in d]
dup = sorted({x for x in ids if ids.count(x) > 1})
if dup:
    fallos.append(f"[L-11] {len(dup)} ids duplicados: {dup[:5]}")

# L-42: los días de BCI salen de scheduling.dayRecurrence (autoritativo), NO de los tags.
# Ningún beneficio BCI puede volver a mostrar 'todos' teniendo un día fijo en scheduling
# (Gracielo mostraba 'todos' siendo 'Todos los martes'; keywords decía 'MIERCOLES', mal).
try:
    _dia_fijo = set()   # ids bci_<id> con día específico en scheduling
    _con_region = set()  # ids bci_<id> con tag 'R. <región>' en la fuente
    _pg, _tp = 1, 1
    while _pg <= _tp and _pg <= 6:
        _req = urllib.request.Request(
            f"https://api.bciplus.cl/bff-loyalty-beneficios/v1/offers?itemsPorPagina=100&pagina={_pg}",
            headers={"Ocp-Apim-Subscription-Key": "fa981752762743668413b68821a43840",
                     "Accept": "application/json", "User-Agent": "Mozilla/5.0"})
        _api = json.loads(urllib.request.urlopen(_req, timeout=25).read().decode("utf-8", "replace"))
        _tp = (_api.get("paginado") or {}).get("totalPaginas", 1)
        for o in _api.get("ofertas", []):
            dr = (o.get("scheduling") or {}).get("dayRecurrence") or []
            if dr and len(dr) < 7:
                _dia_fijo.add(f"bci_{o.get('id')}")
            if any((t.get("nombre") or "").startswith("R. ") for t in o.get("tags", [])):
                _con_region.add(f"bci_{o.get('id')}")
        _pg += 1
    try:
        _otros_bci = json.load(open(os.path.join(ROOT, "beneficios_otros.json"), encoding="utf-8"))
    except Exception:
        _otros_bci = []
    _malos = [b for b in (d + _otros_bci)
              if b.get("banco") == "BCI" and b.get("dias_validos") == ["todos"]
              and b.get("id") in _dia_fijo]
    if len(_malos) > 3:
        fallos.append(f"[L-42] {len(_malos)} beneficios BCI muestran 'todos' teniendo día fijo en scheduling "
                      f"(ej. {_malos[0].get('restaurante','?')}) — regresó el fix de días (dayRecurrence)")
    # L-42b: la región de BCI sale del tag 'R. <x>' (no del título). Ningún beneficio BCI
    # puede tener región VACÍA teniendo el tag en la fuente (Dominga Bistró/La Mulata de
    # Iquique salían bajo Metropolitana por región vacía que pasa el filtro, L-28).
    _sin_region = [b for b in (d + _otros_bci)
                   if b.get("banco") == "BCI" and not (b.get("ubicacion") or "").strip()
                   and b.get("id") in _con_region]
    if len(_sin_region) > 3:
        fallos.append(f"[L-42b] {len(_sin_region)} beneficios BCI con región VACÍA teniendo tag 'R.' en la fuente "
                      f"(ej. {_sin_region[0].get('restaurante','?')}) — regresó el fix de región (aparecen en zonas equivocadas)")
except Exception:
    pass  # si la API de BCI no responde, no rompemos la guardia

# ───────── PRUEBA ÁCIDA: invariantes genéricos (no solo bugs ya vistos) ─────────
try:
    _otros_all = json.load(open(os.path.join(ROOT, "beneficios_otros.json"), encoding="utf-8"))
except Exception:
    _otros_all = []
_todo = d + _otros_all

# ACID-%: ningún descuento con % > 100 (absurdo: $monto o CAE leído como %, L-34/L-40).
_absurdos = []
for b in _todo:
    _m = re.search(r"(\d+)\s*%", b.get("descuento_texto", "") or "")
    if _m and int(_m.group(1)) > 100:
        _absurdos.append(b.get("restaurante", "?"))
if _absurdos:
    fallos.append(f"[ACID-%] {len(_absurdos)} descuentos con % > 100 (absurdo): {_absurdos[:3]}")

# ACID-FRESH: la data no puede quedar vieja (scraper que dejó de correr = proceso estéril, L-W20).
try:
    from datetime import datetime as _dtt, timedelta as _td
    _fs = [b["fecha_scrape"] for b in d if b.get("fecha_scrape")]
    if _fs:
        _ult = max(_dtt.fromisoformat(x) for x in _fs)
        if _dtt.now() - _ult > _td(days=3):
            fallos.append(f"[ACID-FRESH] datos viejos: último scrape {_ult:%Y-%m-%d %H:%M} (>3 días) — ¿el scraper dejó de correr?")
except Exception:
    pass

# ACID-DEPLOY: producción tiene que estar sirviendo ESTE checkout, no una versión congelada.
# "¿pusheó?" != "¿está sirviendo?" (L-44): el VPS pullea out-of-band y la app carga los JSON
# en MEMORIA al bootear → sin restart sigue sirviendo data vieja aunque el commit ya esté.
# Lo que se compara es la FECHA DEL DATO SERVIDO contra la del checkout (el commit es solo
# detalle informativo, porque un push reciente todavía no alcanzó a llegar y eso es normal).
try:
    from datetime import datetime as _dtd, timedelta as _tdd
    _st_e, _body_e = http("/estadisticas")
    if _st_e != 200:
        fallos.append(f"[ACID-DEPLOY] /estadisticas no responde (HTTP {_st_e}) — ¿producción caída?")
    else:
        _est = json.loads(_body_e)
        _prod_fecha = _est.get("fecha_datos")
        _fs_repo = [b["fecha_scrape"] for b in d if b.get("fecha_scrape")]
        _repo_fecha = max(_fs_repo) if _fs_repo else None
        if _prod_fecha is None:
            # El campo lo agregó el fix de L-44: si no viene, producción corre código ANTERIOR
            # a ese fix — o sea lleva sin desplegar desde entonces. Eso ya es el hallazgo.
            fallos.append(
                f"[ACID-DEPLOY] producción no expone 'fecha_datos' → está sirviendo código "
                f"anterior al fix L-44 (sirve {_est.get('total_beneficios')} beneficios; el "
                f"repo tiene {len(d)}). Falta 'git pull + systemctl --user restart cartera.service' en el VPS.")
        elif _repo_fecha:
            _atraso = _dtd.fromisoformat(_repo_fecha) - _dtd.fromisoformat(_prod_fecha)
            if _atraso > _tdd(days=2):
                fallos.append(
                    f"[ACID-DEPLOY] producción CONGELADA: sirve datos del {_prod_fecha[:10]} "
                    f"y el repo ya tiene los del {_repo_fecha[:10]} ({_atraso.days} días de atraso, "
                    f"commit servido {_est.get('version_commit') or '?'}). El git pull sin restart "
                    f"no basta — la app carga los JSON en memoria al bootear (L-44).")
except Exception:
    pass  # nunca romper la guardia por este check

# ACID-DÍAS: los bancos que publican día fijo (hoy 0% 'todos') no pueden spikear a 'todos'
# (= se rompió el parser de días, como pasó con BCI). Falabella/Itaú/Lider/Mach traen día específico.
for _bk in ["Banco Falabella", "Banco Itaú", "Lider BCI", "Mach"]:
    _bs = [b for b in _todo if b.get("banco") == _bk]
    if len(_bs) >= 8:
        _tod = sum(1 for b in _bs if b.get("dias_validos") == ["todos"])
        if _tod / len(_bs) > 0.5:
            fallos.append(f"[ACID-DÍAS] {_bk}: {_tod}/{len(_bs)} en 'todos' (>50%) — normalmente tiene día fijo, ¿se rompió el parser?")

# ACID-REGIÓN: si el nombre trae una ciudad conocida, la región NO puede estar vacía
# (Dominga Bistro Valdivia / La Mulata Iquique salían sin región -> bajo CUALQUIER zona,
# incl. Metropolitana, porque el vacío pasa el filtro, L-28/L-42b).
_CIUDAD_REG = ['iquique', 'valdivia', 'temuco', 'pucon', 'villarrica', 'chillan', 'talca',
               'concepcion', 'antofagasta', 'calama', 'arica', 'puerto varas', 'osorno',
               'copiapo', 'coyhaique', 'punta arenas', 'rancagua', 'curico']
_sin_reg = [b for b in _todo
            if not (b.get("ubicacion") or "").strip()
            and any(re.search(r"\b" + c + r"\b", norm(b.get("restaurante", ""))) for c in _CIUDAD_REG)]
if len(_sin_reg) > 2:
    fallos.append(f"[ACID-REGIÓN] {len(_sin_reg)} beneficios con ciudad en el nombre pero región VACÍA "
                  f"(ej. {_sin_reg[0].get('restaurante','?')}) — aparecen en zonas equivocadas")

# ACID-GENÉRICO: la vista /ver/beneficios no puede mostrar nombres genéricos de categoría
# (Falabella "Beneficios del mes"/"Beneficio en <x>"/cuponera no son un comercio → engañoso).
try:
    _stg, _bg = http("/ver/beneficios")
    if _stg == 200:
        _visg = 0
        for _cand in re.findall(r"(\[\{.*?\}\])\s*;", _bg, re.S):
            try:
                _dl = json.loads(_cand)
            except Exception:
                continue
            if isinstance(_dl, list) and _dl and isinstance(_dl[0], dict) and "banco" in _dl[0]:
                _visg = sum(1 for x in _dl if (x.get("restaurante", "") or "").strip().lower()
                            .startswith(("beneficio en", "beneficios del mes", "cuponera")))
                # ACID-UNIDAD: 'descuento_valor' no siempre es un % — 'precio_fijo'/'monto'
                # guardan ahí un PESO crudo (Mel Studio $84.990, Uno Salud Dental $29.900).
                # ACID-% no lo pilla (busca "%" en descuento_texto, que viene como "$84.990",
                # sin %). Un peso >100 colado en /ver/beneficios corrompe el sort "Mayor
                # descuento", el filtro de % mínimo y el hero "Mejor descuento" (que llegó a
                # mostrar "84990%" — auditoría 2026-09-01, L-45).
                _altos = [x for x in _dl if (x.get("descuento_valor") or 0) > 100]
                if _altos:
                    fallos.append(f"[ACID-UNIDAD] {len(_altos)} beneficios con descuento_valor>100 "
                                  f"VISIBLES en /ver/beneficios (ej. {_altos[0].get('restaurante','?')}="
                                  f"{_altos[0].get('descuento_valor')}) — un peso ($) tratado como %; "
                                  f"¿el filtro _es_verificable de api.py dejó de excluir tipos no-%?")
                break
        if _visg:
            fallos.append(f"[ACID-GENÉRICO] {_visg} nombres genéricos VISIBLES en /ver/beneficios "
                          f"(ej. 'Beneficios del mes') — el filtro del render regresó")
except Exception:
    pass

# L-28: la búsqueda no puede volver a dejar de indexar la geografía (comuna/tags).
def _txt(b):
    return norm(" ".join([b.get("restaurante", ""), b.get("banco", ""),
                          b.get("descripcion") or "", b.get("ubicacion") or "",
                          b.get("direccion") or "", b.get("comuna") or "",
                          " ".join(b.get("tags") or [])]))

if d and sum(1 for b in d if "providencia" in _txt(b)) == 0:
    fallos.append("[L-28] buscar 'providencia' = 0 resultados (¿el buscador dejó de indexar comuna/tags?)")

# L-28: el filtro de Modalidad no puede esconder todas las ofertas (presencial = no-online).
if d and sum(1 for b in d if b.get("presencial") or not b.get("online")) == 0:
    fallos.append("[L-28] 0 ofertas caen bajo 'Presencial' (el filtro de modalidad esconde todo)")

# L-16 / L-W20: la web no puede quedar casi vacía (proceso estéril).
if n < 700:
    fallos.append(f"[L-16] solo {n} beneficios (esperado ~800+); ¿colapsó algún banco?")

# L-33: TRAZABILIDAD — la data debe venir de fuente oficial/marcada, nunca de un agregador
# sin avisar (la bencina se re-curó desde Copec oficial + medios, con campo 'confianza').
try:
    benc = json.load(open(os.path.join(ROOT, "bencinas.json"), encoding="utf-8")).get("descuentos", [])
    sin_conf = [x for x in benc if not (x.get("confianza") or "").strip()]
    agg = [x for x in benc if "descuentosrata" in (x.get("url_fuente") or "").lower()]
    if sin_conf:
        fallos.append(f"[L-33] {len(sin_conf)} descuentos de bencina SIN 'confianza' (trazabilidad) — marcar la fuente")
    if agg:
        fallos.append(f"[L-33] {len(agg)} descuentos de bencina de agregador (descuentosrata) sin curar a fuente oficial")
except Exception as e:
    fallos.append(f"[L-33] no se pudo auditar la trazabilidad de bencina: {e}")
try:
    otros = json.load(open(os.path.join(ROOT, "beneficios_otros.json"), encoding="utf-8"))
    otros_agg = [b for b in otros if "descuentosrata" in (b.get("url_fuente") or "").lower()]
    if otros_agg:
        fallos.append(f"[L-33] {len(otros_agg)} 'otros beneficios' de fuente agregador (deben ser oficiales)")
except Exception:
    pass

# ───────────────────── Resultado ─────────────────────
print(f"Revisión de madrugada · {URL}")
# "servidos" era falso: n sale del checkout, no de produccion — decirlo mal fue
# justamente lo que dejo pasar 3 dias de atraso sin que nadie mirara (L-44).
print(f"{n} beneficios en el repo · {sum(1 for h in htmls.values() if h)} páginas alcanzadas\n")
if fallos:
    print(f"❌ {len(fallos)} PROBLEMA(S) DETECTADO(S) — un bug conocido reapareció:\n")
    for f in fallos:
        print("  •", f)
    sys.exit(1)
print("✅ TODO OK — ninguno de los problemas conocidos reapareció.")
sys.exit(0)

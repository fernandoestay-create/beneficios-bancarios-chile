#!/usr/bin/env python3
"""
Revisión de madrugada — guardia automática de las páginas de MiCartera.

Cada check corresponde a un bug REAL ya documentado (LECCIONES_APRENDIDAS.md +
TUNING_PAGINAS.md). Es el fine-tuning hecho código (patrón L-07): cada error resuelto
se convierte en un guard permanente, para que NINGUNO reaparezca en silencio.

Corre en el cron de madrugada (revision_madrugada.yml). Verifica dos capas:
  - RUNTIME: producción viva (curl a la URL) — página responde, JS sano, endpoints seguros.
  - DATA: lo que se sirve (beneficios.json del checkout) — nombres, filtros, integridad.

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

URL = os.getenv("PROD_URL", "https://api-beneficios-chile.onrender.com")
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
    _dia_fijo = set()  # ids bci_<id> con día específico en scheduling
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

# ACID-DÍAS: los bancos que publican día fijo (hoy 0% 'todos') no pueden spikear a 'todos'
# (= se rompió el parser de días, como pasó con BCI). Falabella/Itaú/Lider/Mach traen día específico.
for _bk in ["Banco Falabella", "Banco Itaú", "Lider BCI", "Mach"]:
    _bs = [b for b in _todo if b.get("banco") == _bk]
    if len(_bs) >= 8:
        _tod = sum(1 for b in _bs if b.get("dias_validos") == ["todos"])
        if _tod / len(_bs) > 0.5:
            fallos.append(f"[ACID-DÍAS] {_bk}: {_tod}/{len(_bs)} en 'todos' (>50%) — normalmente tiene día fijo, ¿se rompió el parser?")

# ── L-43 (auditoría ácida 2026-08-18): 4 guards nuevos ────────────────────────
# Deliberadamente NO importan scrapers.py: la guardia tiene que poder pillar el bug aunque
# el helper del scraper se rompa (el que construye no revisa, L-40).

def _sin_tilde(s):
    s = (s or "").replace("’", "'").replace("´", "'").replace("`", "'")
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn").strip()


_REGIONES_OK = {"Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo",
                "Valparaíso", "Metropolitana", "O'Higgins", "Maule", "Ñuble", "Biobío",
                "Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes"}
_DIAS7 = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

# [L-43a] descuento_valor es un PORCENTAJE. Un $monto ahí pinta "84990%" en el stat
# "Mejor descuento" y descoloca el orden y el filtro de descuento mínimo.
_pct_malos = [b for b in _todo if (b.get("descuento_valor") or 0) > 100]
if _pct_malos:
    fallos.append(f"[L-43a] {len(_pct_malos)} beneficios con descuento_valor > 100 "
                  f"(un $monto guardado como %): {[b.get('id') for b in _pct_malos[:3]]}")

# [L-43a-runtime] lo que VE el usuario: el stat "Mejor descuento" no puede pasar de 100%.
for _p in ["/ver"]:
    for _v, _l in re.findall(r'<div class="val">([^<]*)</div><div class="lbl">([^<]*)</div>',
                             htmls.get(_p) or ""):
        _m = re.match(r"^(\d+)%$", _v.strip())
        if "mejor descuento" in _l.lower() and _m and int(_m.group(1)) > 100:
            fallos.append(f"[L-43a] {_p} muestra 'Mejor descuento: {_v}' (>100%, imposible)")

# [L-43b] `ubicacion` es el campo de REGIÓN: si trae un local/URL/ciudad, el filtro de zona
# ESCONDE esa oferta (el front excluye lo que no calza con la región elegida, primo de L-28).
_reg_malas = [b for b in _todo if (b.get("ubicacion") or "").strip() and b["ubicacion"] not in _REGIONES_OK]
if _reg_malas:
    fallos.append(f"[L-43b] {len(_reg_malas)} beneficios con 'ubicacion' que NO es una región de Chile "
                  f"(se ocultan al filtrar por zona): "
                  f"{sorted({b['ubicacion'][:28] for b in _reg_malas})[:4]}")

# [L-43c] MAPA: toda región presente en la data tiene que resolver a coordenadas EN EL JS
# QUE SE SIRVE. 'Los Ríos' no calzaba con las claves 'los rios'/'losríos' (tilde + espacio)
# y la región entera se quedaba sin un solo pin. Se ejecuta la getCoords REAL de la página
# con node — replicarla acá a mano haría que el guard mida mi versión, no la servida.
try:
    _js = htmls.get("/ver") or ""
    # Del inicio de la tabla de coordenadas hasta el `let mapObj` que sigue a getCoords:
    # se lleva la tabla + la función tal cual se sirven, sin depender de su formato interno.
    _blk = re.search(r"(const REGION_COORDS=\{.*?)\nlet mapObj", _js, re.S)
    _regs = sorted({(b.get("ubicacion") or "").strip() for b in d if (b.get("ubicacion") or "").strip()})
    if _blk and "function getCoords" in _blk.group(1) and _regs:
        _f = os.path.join(tempfile.gettempdir(), "chk_coords.js")
        open(_f, "w", encoding="utf-8").write(
            _blk.group(1) + "\n" +
            f"const R={json.dumps(_regs, ensure_ascii=False)};\n"
            "console.log(JSON.stringify(R.filter(r=>!getCoords(r,0))));")
        _r = subprocess.run(["node", _f], capture_output=True, text=True)
        _sin_pin = json.loads(_r.stdout.strip() or "[]") if _r.returncode == 0 else []
        if _sin_pin:
            fallos.append(f"[L-43c] {len(_sin_pin)} región(es) SIN NINGÚN PIN en el mapa "
                          f"(la getCoords servida no las resuelve): {_sin_pin[:6]}")
        elif _r.returncode != 0:
            fallos.append(f"[L-43c] no se pudo ejecutar la getCoords servida: {_r.stderr.strip()[:90]}")
except Exception:
    pass

# [L-43d] 'todos los días' cuando la fuente nombra un día fijo es información ERRÓNEA
# (el usuario va el día equivocado): extiende L-42 a CUALQUIER banco, midiendo el texto
# que la propia fuente entregó. Si el texto dice "todos los días", 'todos' es correcto.
_dia_falso = []
for b in _todo:
    if b.get("dias_validos") != ["todos"]:
        continue
    _t = _sin_tilde(b.get("descripcion") or "")
    if not _t or "todos los dias" in _t:
        continue
    _t = re.sub(r"\b(" + "|".join(_DIAS7) + r")\s+\d{1,2}[/\-.]\d", " ", _t)
    _hay = {x for x in _DIAS7 if re.search(r"\b" + x + r"s?\b", _t)}
    if _hay and len(_hay) < 7:
        _dia_falso.append(b)
if _dia_falso:
    fallos.append(f"[L-43d] {len(_dia_falso)} beneficios dicen 'todos los días' pero su propia "
                  f"descripción nombra días fijos (ej. {_dia_falso[0].get('restaurante','?')} — "
                  f"{_dia_falso[0].get('banco','?')}): el usuario iría el día equivocado")

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
print(f"{n} beneficios servidos · {sum(1 for h in htmls.values() if h)} páginas alcanzadas\n")
if fallos:
    print(f"❌ {len(fallos)} PROBLEMA(S) DETECTADO(S) — un bug conocido reapareció:\n")
    for f in fallos:
        print("  •", f)
    sys.exit(1)
print("✅ TODO OK — ninguno de los problemas conocidos reapareció.")
sys.exit(0)

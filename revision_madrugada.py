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

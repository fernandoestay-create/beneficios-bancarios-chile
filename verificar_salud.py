#!/usr/bin/env python3
"""
Health check de producción para MiCartera.

Valida, sin levantar el servidor, que el sistema está listo para deploy:
  1. LOGOS    - todo logo referenciado en api.py existe localmente en static/logos/
                y NO queda ninguna URL externa (Wikimedia/Google bloquean hotlink).
  2. BENEFICIOS - beneficios.json es una lista no vacía con los campos requeridos
                  y días normalizados.
  3. BENCINAS - bencinas.json tiene la estructura esperada, campos requeridos,
                días normalizados y el descuento Scotiabank sábado presente.

Uso:
    python3 verificar_salud.py          # corre todos los checks
    echo $?                             # 0 = todo OK, 1 = hubo fallos

Pensado para correr en pre-deploy / CI (Render) y localmente antes de pushear.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = ROOT / "api.py"
LOGOS_DIR = ROOT / "static" / "logos"
BENEFICIOS = ROOT / "beneficios.json"
BENCINAS = ROOT / "bencinas.json"

# Días normalizados (minúscula, sin tilde). 'todos' solo aplica a restaurantes.
DIAS_BENCINAS = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"}
DIAS_BENEFICIOS = DIAS_BENCINAS | {"todos"}

# Patrones de URLs externas que rompen en producción (hotlink bloqueado / falsas).
URLS_PROHIBIDAS = re.compile(r"https?://[^\"'\s)]*?(wikimedia|wikipedia|googleusercontent|play-lh)")

errores = []
avisos = []


def fail(msg):
    errores.append(msg)


def warn(msg):
    avisos.append(msg)


def check_logos():
    print("== 1. LOGOS ==")
    texto = API.read_text(encoding="utf-8")

    # Toda referencia /static/logos/<archivo>
    refs = sorted(set(re.findall(r"/static/logos/([A-Za-z0-9_.-]+)", texto)))
    if not refs:
        fail("api.py no referencia ningún logo en /static/logos/ (¿roto?)")
        return
    print(f"   {len(refs)} logos referenciados en api.py")

    faltantes = [r for r in refs if not (LOGOS_DIR / r).is_file()]
    if faltantes:
        for f in faltantes:
            fail(f"logo referenciado pero NO existe el archivo: static/logos/{f}")
    else:
        print(f"   OK: los {len(refs)} archivos existen en static/logos/")

    # Ninguna URL externa de logo
    externas = URLS_PROHIBIDAS.findall(texto)
    if externas:
        # findall con grupo devuelve solo el grupo; recontar líneas para el reporte
        lineas = [i + 1 for i, ln in enumerate(texto.splitlines()) if URLS_PROHIBIDAS.search(ln)]
        fail(f"api.py tiene {len(lineas)} URL(s) de logo externas (hotlink bloqueado) en líneas {lineas[:10]}")
    else:
        print("   OK: 0 URLs externas de logo (todo self-hosted)")

    # Info: archivos huérfanos (existen pero no se referencian) — no es fallo
    en_disco = {p.name for p in LOGOS_DIR.iterdir() if p.is_file()}
    huerfanos = sorted(en_disco - set(refs))
    if huerfanos:
        warn(f"{len(huerfanos)} logos en disco sin referencia (ok, reserva): {huerfanos}")


def check_beneficios():
    print("== 2. BENEFICIOS (restaurantes) ==")
    try:
        data = json.loads(BENEFICIOS.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"beneficios.json no parsea: {e}")
        return
    if not isinstance(data, list) or not data:
        fail("beneficios.json debe ser una lista no vacía")
        return
    print(f"   {len(data)} beneficios")

    requeridos = {"id", "banco", "tarjeta", "restaurante", "dias_validos"}
    sin_campos = 0
    dias_malos = set()
    bancos = {}
    for d in data:
        if not requeridos.issubset(d):
            sin_campos += 1
        for dia in (d.get("dias_validos") or []):
            if dia not in DIAS_BENEFICIOS:
                dias_malos.add(dia)
        bancos[d.get("banco", "?")] = bancos.get(d.get("banco", "?"), 0) + 1

    if sin_campos:
        fail(f"{sin_campos} beneficios sin todos los campos requeridos {sorted(requeridos)}")
    else:
        print(f"   OK: todos tienen {sorted(requeridos)}")
    if dias_malos:
        fail(f"beneficios con días NO normalizados: {sorted(dias_malos)}")
    else:
        print("   OK: días normalizados")
    print(f"   {len(bancos)} bancos: " + ", ".join(f"{k}({v})" for k, v in sorted(bancos.items())))


def check_bencinas():
    print("== 3. BENCINAS (combustibles) ==")
    try:
        data = json.loads(BENCINAS.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"bencinas.json no parsea: {e}")
        return
    for k in ("descuentos", "estaciones", "precios_todas", "meta"):
        if k not in data:
            fail(f"bencinas.json sin la clave '{k}'")
    descuentos = data.get("descuentos", [])
    if not descuentos:
        fail("bencinas.json sin descuentos")
        return
    print(f"   {len(descuentos)} descuentos, {len(data.get('estaciones', []))} estaciones, "
          f"{len(data.get('precios_todas', []))} precios")

    requeridos = {"id", "cadena", "banco", "tarjeta", "descuento_texto", "dias_validos", "activo"}
    sin_campos = 0
    dias_malos = set()
    for d in descuentos:
        if not requeridos.issubset(d):
            sin_campos += 1
        for dia in (d.get("dias_validos") or []):
            if dia not in DIAS_BENCINAS:
                dias_malos.add(dia)
    if sin_campos:
        fail(f"{sin_campos} descuentos de bencina sin campos requeridos {sorted(requeridos)}")
    else:
        print(f"   OK: todos tienen {sorted(requeridos)}")
    if dias_malos:
        fail(f"bencinas con días NO normalizados: {sorted(dias_malos)}")
    else:
        print("   OK: días normalizados")

    # Guard de regresión: Scotiabank Shell sábado debe existir (fix 2026-06-01)
    scotia_sab = [d for d in descuentos
                  if d.get("banco") == "Scotiabank" and "sabado" in (d.get("dias_validos") or [])]
    if not scotia_sab:
        fail("REGRESIÓN: no está el descuento Scotiabank Shell sábado (App Shell ex Mi Copiloto)")
    else:
        tiers = ", ".join(f"{d['tarjeta']}={d['descuento_texto']}" for d in scotia_sab)
        print(f"   OK: Scotiabank sábado presente ({len(scotia_sab)} tiers: {tiers})")


def main():
    print("=" * 60)
    print("HEALTH CHECK MiCartera —", ROOT.name)
    print("=" * 60)
    check_logos()
    check_beneficios()
    check_bencinas()
    print("=" * 60)
    for a in avisos:
        print("AVISO:", a)
    if errores:
        print(f"\nRESULTADO: ❌ {len(errores)} FALLO(S)")
        for e in errores:
            print("  -", e)
        return 1
    print("\nRESULTADO: ✅ TODO OK — listo para producción")
    return 0


if __name__ == "__main__":
    sys.exit(main())

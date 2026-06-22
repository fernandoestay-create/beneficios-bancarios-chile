#!/usr/bin/env python3
"""
Chequeo experto del estado de cada banco tras una corrida del scraper.

Objetivo (pedido de Fernando, 2026-06-22): que NINGUN banco pueda caerse o
degradarse en silencio cuando un sitio cambia, activa geo-fence o bloquea. Tras
cada corrida del cron se compara lo traido por banco contra (a) un piso absoluto
y (b) la corrida previa, se clasifica cada banco y se genera el reporte por banco
que va al email. Es la FUENTE UNICA de los pisos (verificar_salud.py los importa).

Estados por banco:
  OK         trajo >= su piso efectivo.
  DEGRADADO  trajo algo pero por debajo del piso efectivo (cambio de pagina,
             geo-fence parcial, anti-bot). NO se preserva (podria ser real) pero
             se alerta por mail.
  CAIDO      trajo 0 teniendo historial. Se preservan los datos previos (red de
             seguridad, ver scrapers.OrquestadorScrapers.aplicar_red_de_seguridad)
             y se alerta por mail.

Lecciones: L-15 (geo-fence del runner) / L-16 (anti proceso-esteril por banco).
"""
from collections import Counter

# Piso absoluto por banco (~40-50% del histórico de 2026-06). Red de seguridad si
# el conteo previo tambien estaba mal. BancoEstado: diferido (campaña caída),
# espera 0 a proposito, no se alerta.
PISOS_BANCOS = {
    "Banco de Chile": 100, "BCI": 50, "Banco Falabella": 40,
    "Banco Security": 30, "Santander": 30, "Banco Itaú": 25,
    "Scotiabank": 25, "Banco BICE": 25, "Banco Ripley": 20,
    "Entel": 8, "Tenpo": 3, "Lider BCI": 3, "Banco Consorcio": 2, "Mach": 2,
}

BANCOS_DIFERIDOS = {"BancoEstado"}  # esperan 0 a propósito, no generan alerta

# Si un banco trae menos de esta fracción de lo que trajo la corrida previa, se
# considera degradado aunque supere su piso absoluto (atrapa la caída relativa).
FRACCION_DEGRADADO = 0.6

_COLOR = {"OK": "#10b981", "DEGRADADO": "#f59e0b", "CAIDO": "#dc2626"}
_ICONO = {"OK": "✅", "DEGRADADO": "⚠️", "CAIDO": "🔴"}


def piso_efectivo(banco, previo):
    """El mayor entre el piso absoluto del banco y una fracción del conteo previo."""
    return max(PISOS_BANCOS.get(banco, 1), int(previo * FRACCION_DEGRADADO))


def evaluar_corrida(nuevos_por_banco, previos_por_banco):
    """Clasifica cada banco comparando lo nuevo vs lo previo y su piso.

    Devuelve lista de dicts ordenada por banco:
        {banco, nuevo, previo, piso, estado, motivo}
    """
    reporte = []
    bancos = (set(nuevos_por_banco) | set(previos_por_banco) | set(PISOS_BANCOS)) - BANCOS_DIFERIDOS
    for banco in sorted(bancos):
        nuevo = int(nuevos_por_banco.get(banco, 0))
        previo = int(previos_por_banco.get(banco, 0))
        piso = piso_efectivo(banco, previo)
        if nuevo == 0:
            estado, motivo = "CAIDO", f"trajo 0 (previo {previo})"
        elif nuevo < piso:
            estado, motivo = "DEGRADADO", f"trajo {nuevo}, esperado >= {piso} (previo {previo})"
        else:
            estado, motivo = "OK", f"trajo {nuevo}"
        reporte.append({"banco": banco, "nuevo": nuevo, "previo": previo,
                        "piso": piso, "estado": estado, "motivo": motivo})
    return reporte


def problemas(reporte):
    """Bancos en estado CAIDO o DEGRADADO."""
    return [r for r in reporte if r["estado"] in ("CAIDO", "DEGRADADO")]


def resumen(reporte):
    c = Counter(r["estado"] for r in reporte)
    return {"ok": c.get("OK", 0), "degradado": c.get("DEGRADADO", 0),
            "caido": c.get("CAIDO", 0), "total": len(reporte)}


def generar_asunto(reporte, fecha, total_beneficios):
    """Asunto del email: verde si todo OK, ALERTA con nombres si hay problemas."""
    probs = problemas(reporte)
    if probs:
        caidos = [r["banco"] for r in probs if r["estado"] == "CAIDO"]
        degr = [r["banco"] for r in probs if r["estado"] == "DEGRADADO"]
        partes = []
        if caidos:
            partes.append("CAÍDO: " + ", ".join(caidos))
        if degr:
            partes.append("degradado: " + ", ".join(degr))
        return f"⚠️ ALERTA Scraping {fecha} — " + " | ".join(partes)
    r = resumen(reporte)
    return f"✅ Scraping {fecha} — {r['ok']}/{r['total']} bancos OK · {total_beneficios} beneficios"


def generar_html(reporte, fecha, total_beneficios, preservados=None, bencinas=None):
    """Cuerpo HTML del email: banner de alerta (si hay) + tabla con estado por banco."""
    preservados = {(p[0] if isinstance(p, (list, tuple)) else p) for p in (preservados or [])}
    probs = problemas(reporte)
    r = resumen(reporte)

    orden = {"CAIDO": 0, "DEGRADADO": 1, "OK": 2}
    filas = []
    for it in sorted(reporte, key=lambda x: (orden[x["estado"]], -x["nuevo"])):
        color, ico = _COLOR[it["estado"]], _ICONO[it["estado"]]
        pres = " <i style='color:#6b7280'>(preservado)</i>" if it["banco"] in preservados else ""
        filas.append(
            "<tr style='border-bottom:1px solid #f3f4f6'>"
            f"<td style='padding:7px 0'>{it['banco']}{pres}</td>"
            f"<td style='padding:7px 0;text-align:right;font-weight:700'>{it['nuevo']}</td>"
            f"<td style='padding:7px 0;text-align:right;color:#9ca3af'>{it['piso']}</td>"
            f"<td style='padding:7px 0;text-align:right;color:{color};font-weight:700'>{ico} {it['estado']}</td>"
            "</tr>"
        )

    banner = ""
    if probs:
        det = "; ".join(f"{p['banco']} ({p['motivo']})" for p in probs)
        banner = (
            "<div style='background:#fef2f2;border:1px solid #fecaca;padding:12px 16px;"
            "border-radius:8px;margin-bottom:14px;color:#dc2626;font-size:14px'>"
            f"<b>⚠️ {len(probs)} banco(s) con problema.</b> {det}. "
            "Los CAÍDOS conservan sus datos previos (no desaparecen de la web). Revisá el scraper.</div>"
        )

    color_top = "#dc2626" if probs else "#6366f1"
    titulo = "⚠️ Alerta Scraping" if probs else "✅ Reporte Scraping"
    bencinas_txt = f" · ⛽ {bencinas} bencinas" if bencinas is not None else ""

    return f"""<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto">
  <div style="background:{color_top};padding:18px;border-radius:12px 12px 0 0">
    <h1 style="color:#fff;margin:0;font-size:20px">{titulo}</h1>
    <p style="color:rgba(255,255,255,.85);margin:5px 0 0;font-size:13px">{fecha} · {total_beneficios} beneficios · {r['ok']} OK / {r['degradado']} degradados / {r['caido']} caídos{bencinas_txt}</p>
  </div>
  <div style="background:#fff;padding:18px;border:1px solid #e5e7eb">
    {banner}
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="border-bottom:2px solid #e5e7eb;color:#6b7280;font-size:11px">
        <td style="padding:6px 0">BANCO</td>
        <td style="padding:6px 0;text-align:right">TRAJO</td>
        <td style="padding:6px 0;text-align:right">PISO</td>
        <td style="padding:6px 0;text-align:right">ESTADO</td>
      </tr>
      {''.join(filas)}
    </table>
    <div style="margin-top:16px">
      <a href="https://api-beneficios-chile.onrender.com/ver" style="background:#6366f1;color:#fff;padding:9px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px">🍽️ Ver Restaurantes</a>
    </div>
  </div>
  <div style="background:#f9fafb;padding:11px 18px;border-radius:0 0 12px 12px;border:1px solid #e5e7eb;border-top:0">
    <p style="color:#9ca3af;font-size:11px;margin:0">Chequeo experto por banco · GitHub Actions · <a href="https://github.com/fernandoestay-create/beneficios-bancarios-chile/actions" style="color:#6366f1">Ver logs</a></p>
  </div>
</div>"""

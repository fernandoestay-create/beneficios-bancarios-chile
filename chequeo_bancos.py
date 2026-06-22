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
    # Aprendizaje: si hay historial, el piso se calibra al nivel normal de cada banco
    # y se detectan caidas relativas a su propio historico (alerta temprana). Sin
    # historial (primeras corridas), cae limpio a los pisos fijos.
    try:
        import aprendizaje
        _hist = aprendizaje.cargar_historial()
    except Exception:
        aprendizaje = None
        _hist = []

    reporte = []
    bancos = (set(nuevos_por_banco) | set(previos_por_banco) | set(PISOS_BANCOS)) - BANCOS_DIFERIDOS
    for banco in sorted(bancos):
        nuevo = int(nuevos_por_banco.get(banco, 0))
        previo = int(previos_por_banco.get(banco, 0))
        piso_base = piso_efectivo(banco, previo)
        tend = None
        if aprendizaje:
            piso = aprendizaje.piso_aprendido(banco, piso_base, _hist)
            tend = aprendizaje.tendencia(banco, nuevo, _hist)
        else:
            piso = piso_base
        if nuevo == 0:
            estado, motivo = "CAIDO", f"trajo 0 (previo {previo})"
        elif nuevo < piso:
            estado, motivo = "DEGRADADO", f"trajo {nuevo}, esperado >= {piso} (previo {previo})"
        elif tend:
            estado, motivo = "DEGRADADO", f"tendencia a la baja: {tend}"
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
            partes.append("caído " + ", ".join(caidos))
        if degr:
            partes.append("bajó " + ", ".join(degr))
        return f"⚠️ REVISAR · MiCartera — " + " | ".join(partes) + f" · {fecha}"
    r = resumen(reporte)
    return f"✅ TODO OK · MiCartera {r['ok']}/{r['total']} bancos · {total_beneficios} beneficios · {fecha}"


def generar_html(reporte, fecha, total_beneficios, preservados=None, bencinas=None, aprendizaje_info=None):
    """Cuerpo HTML del email: banner de alerta (si hay) + tabla con estado por banco."""
    preservados_list = list(preservados or [])
    preservados_set = {(p[0] if isinstance(p, (list, tuple)) else p) for p in preservados_list}
    probs = problemas(reporte)
    r = resumen(reporte)
    nprob = r["degradado"] + r["caido"]

    orden = {"CAIDO": 0, "DEGRADADO": 1, "OK": 2}
    bg = {"OK": "#ffffff", "DEGRADADO": "#fffbeb", "CAIDO": "#fef2f2"}
    filas = []
    for it in sorted(reporte, key=lambda x: (orden[x["estado"]], -x["nuevo"])):
        color, ico = _COLOR[it["estado"]], _ICONO[it["estado"]]
        pres = " <span style='color:#6b7280;font-size:11px'>(preservado)</span>" if it["banco"] in preservados_set else ""
        filas.append(
            f"<tr style='background:{bg[it['estado']]};border-bottom:1px solid #f3f4f6'>"
            f"<td style='padding:8px 6px'>{it['banco']}{pres}</td>"
            f"<td style='padding:8px 6px;text-align:right;font-weight:700'>{it['nuevo']}</td>"
            f"<td style='padding:8px 6px;text-align:right;color:#9ca3af'>{it['piso']}</td>"
            f"<td style='padding:8px 6px;text-align:right;color:{color};font-weight:700'>{ico} {it['estado']}</td>"
            "</tr>"
        )

    banner = ""
    if probs:
        det = "".join(f"<li><b>{p['banco']}</b>: {p['motivo']}</li>" for p in probs)
        banner = (
            "<div style='background:#fef2f2;border:1px solid #fecaca;padding:12px 16px;"
            "border-radius:10px;margin-bottom:16px;color:#9a1c1c;font-size:13px'>"
            f"<b>⚠️ {len(probs)} banco(s) necesitan tu atención:</b>"
            f"<ul style='margin:6px 0 0;padding-left:18px'>{det}</ul>"
            "<div style='margin-top:6px;color:#7f1d1d'>Los <b>caídos</b> conservan sus datos previos (la web no pierde el banco). "
            "Si fue un cambio de la página del banco, avísame para arreglar el scraper.</div></div>"
        )

    color_top = "#b91c1c" if probs else "#0f6e56"
    titulo = "⚠️ Revisar — hay bancos con problema" if probs else "✅ Todo OK — el sistema corrió bien"

    def _card(lbl, val, col):
        return (f"<td style='background:#f9fafb;border-radius:10px;padding:14px 6px;text-align:center'>"
                f"<div style='font-size:23px;font-weight:700;color:{col}'>{val}</div>"
                f"<div style='font-size:11px;color:#6b7280;margin-top:3px'>{lbl}</div></td>")
    cards = ("<table style='width:100%;border-collapse:separate;border-spacing:8px 0;margin-bottom:18px'><tr>"
             + _card("beneficios", total_beneficios, "#003058")
             + _card("bancos OK", f"{r['ok']}/{r['total']}", "#0f6e56")
             + _card("a revisar", nprob, "#b45309" if nprob else "#9ca3af")
             + (_card("bencinas", bencinas, "#0f6e56") if bencinas is not None else "")
             + "</tr></table>")

    pres_html = ""
    if preservados_list:
        li = "".join(f"<li><b>{(p[0] if isinstance(p,(list,tuple)) else p)}</b>: se mantienen "
                     f"{(p[1] if isinstance(p,(list,tuple)) else '?')} ofertas de la corrida anterior</li>"
                     for p in preservados_list)
        pres_html = (f"<div style='margin-top:10px;color:#92400e'><b>Esta corrida preservó datos de:</b>"
                     f"<ul style='margin:4px 0 0;padding-left:18px'>{li}</ul></div>")

    como = (
        "<div style='background:#f9fafb;border-radius:10px;padding:14px 16px;margin-top:18px;font-size:13px;line-height:1.65;color:#374151'>"
        "<b style='font-size:14px;color:#1f2937'>🔧 Cómo funciona este reporte</b>"
        "<ul style='margin:8px 0 0;padding-left:18px'>"
        "<li>Se scrapean los <b>15 bancos</b> a diario, desde tu PC en Chile (sin geo-fence) + un cron en la nube de respaldo.</li>"
        "<li>Cada banco se compara con su <b>piso</b> (mínimo esperado) — columnas TRAJO vs PISO. "
        "<b style='color:#0f6e56'>✅ OK</b> = sobre el piso · <b style='color:#b45309'>⚠️ degradado</b> = bajó del piso · <b style='color:#b91c1c'>🔴 caído</b> = trajo 0.</li>"
        "<li><b>Reintentos automáticos</b> ante fallas temporales (timeout, sitio lento).</li>"
        "<li><b>Red de seguridad:</b> si un banco cae a 0, se conservan sus datos previos y este mail te avisa — la web nunca queda sin el banco.</li>"
        "<li>La data solo se publica si pasa el <b>chequeo de salud</b> (sin duplicados ni datos corruptos, todos los bancos sobre su piso).</li>"
        + (f"<li><b>🧠 Aprende:</b> lleva <b>{aprendizaje_info['corridas']} corridas</b> en memoria; ajusta el piso de cada banco a su nivel normal histórico y avisa si uno cae respecto a lo habitual — antes de llegar a 0.</li>"
           if aprendizaje_info and aprendizaje_info.get('corridas') else "")
        + "</ul>"
        f"{pres_html}"
        "</div>"
    )

    return f"""<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#1f2937">
  <div style="background:{color_top};padding:20px;border-radius:12px 12px 0 0">
    <h1 style="color:#fff;margin:0;font-size:21px">{titulo}</h1>
    <p style="color:rgba(255,255,255,.85);margin:6px 0 0;font-size:13px">{fecha} · MiCartera — beneficios bancarios Chile</p>
  </div>
  <div style="background:#fff;padding:20px;border:1px solid #e5e7eb">
    {banner}
    {cards}
    <h2 style="font-size:15px;margin:0 0 8px;color:#1f2937">Estado de cada banco</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="border-bottom:2px solid #e5e7eb;color:#6b7280;font-size:11px;text-align:left">
        <th style="padding:6px;font-weight:600">BANCO</th>
        <th style="padding:6px;text-align:right;font-weight:600">TRAJO</th>
        <th style="padding:6px;text-align:right;font-weight:600">PISO</th>
        <th style="padding:6px;text-align:right;font-weight:600">ESTADO</th>
      </tr>
      {''.join(filas)}
    </table>
    {como}
    <div style="margin-top:18px">
      <a href="https://api-beneficios-chile.onrender.com/ver" style="background:#003058;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;margin-right:8px">🍽️ Ver Restaurantes</a>
      <a href="https://api-beneficios-chile.onrender.com/ver/bencinas" style="background:#0f6e56;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px">⛽ Ver Bencinas</a>
    </div>
  </div>
  <div style="background:#f9fafb;padding:12px 18px;border-radius:0 0 12px 12px;border:1px solid #e5e7eb;border-top:0">
    <p style="color:#9ca3af;font-size:11px;margin:0">MiCartera · reporte automático diario · este correo te llega siempre (haya o no problemas) para confirmarte que el sistema corrió.</p>
  </div>
</div>"""

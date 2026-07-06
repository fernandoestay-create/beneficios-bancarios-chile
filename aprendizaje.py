#!/usr/bin/env python3
"""
Memoria y aprendizaje del sistema MiCartera.

Cada corrida deja un snapshot en historial.json. Con esa serie temporal el sistema
se vuelve mas preciso solo:
  - APRENDE el nivel normal de cada banco (mediana de las ultimas N corridas).
  - Ajusta el PISO de alerta a ese nivel (piso_aprendido = max(piso_fijo, normal*0.6)),
    asi si un banco crece el piso sube solo.
  - DETECTA tendencias: un banco que cae respecto a su PROPIO historico, aunque
    todavia supere el piso fijo (alerta temprana, antes de llegar a 0).
  - Guarda los problemas de cada corrida (memoria de incidentes).

NO es un modelo neuronal (seria humo para 14 scrapers): es aprendizaje estadistico
sobre el propio historico, honesto y verificable. Mas corridas -> mejor calibracion.

historial.json vive en el repo (se commitea con cada corrida) para persistir entre
los runners efimeros del cron y el refresco local.
"""
import json
import os
from statistics import median

ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORIAL = os.path.join(ROOT, "historial.json")
N_VENTANA = 7           # corridas recientes (~1 semana) para "aprender" el nivel normal.
                        # 7 y no 12: así el sistema reconoce un CAMBIO DE NIVEL sostenido en
                        # ~1 semana (ej. un banco que renueva su campaña mensual con menos
                        # ofertas, como Itaú 71→23 en jul-2026) y deja de marcarlo DEGRADADO
                        # en falso. El piso fijo (PISOS_BANCOS) sigue siendo la red mínima.
FRACCION_PISO = 0.6     # el piso aprendido es 60% del nivel normal
UMBRAL_TENDENCIA = 0.7  # si cae bajo el 70% de su normal, es tendencia a la baja
MAX_HIST = 400          # ~1 anio de corridas


def cargar_historial():
    if os.path.exists(HISTORIAL):
        try:
            with open(HISTORIAL, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def registrar_corrida(fecha, por_banco, problemas=None, preservados=None, total=0):
    """Append un snapshot al historial. Idempotente por fecha (1 snapshot/dia: si ya
    hay uno de esa fecha lo reemplaza, para que varias corridas el mismo dia no inflen)."""
    hist = [h for h in cargar_historial() if h.get("fecha") != fecha]
    hist.append({
        "fecha": fecha,
        "total": int(total),
        "por_banco": {k: int(v) for k, v in dict(por_banco).items()},
        "problemas": list(problemas or []),
        "preservados": [list(p) if isinstance(p, (list, tuple)) else p for p in (preservados or [])],
    })
    hist = sorted(hist, key=lambda h: h.get("fecha", ""))[-MAX_HIST:]
    with open(HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1)
    return len(hist)


def nivel_normal(banco, hist=None):
    """Nivel normal aprendido de un banco: mediana de sus ultimas N corridas (>0)."""
    hist = hist if hist is not None else cargar_historial()
    vals = [h.get("por_banco", {}).get(banco, 0) for h in hist[-N_VENTANA:]]
    vals = [v for v in vals if v > 0]
    return median(vals) if vals else 0


def piso_aprendido(banco, piso_fijo, hist=None):
    """Piso adaptativo: el mayor entre el piso fijo (red de seguridad, nunca baja de ahi)
    y el 60% del nivel normal aprendido. Si un banco crece, el piso sube solo."""
    return max(piso_fijo, int(nivel_normal(banco, hist) * FRACCION_PISO))


def tendencia(banco, nuevo, hist=None):
    """Caida sostenida: ¿el banco cayo bajo el 70% de su nivel normal historico?
    Devuelve un str con el motivo o None. Detecta degradaciones que el piso fijo
    dejaria pasar (alerta temprana, antes del 0)."""
    normal = nivel_normal(banco, hist)
    if normal and 0 < nuevo < normal * UMBRAL_TENDENCIA:
        caida = int((1 - nuevo / normal) * 100)
        return f"{nuevo} vs ~{int(normal)} habitual (-{caida}%)"
    return None


def resumen_aprendizaje(hist=None):
    """Para el mail: cuanto sabe el sistema (cuantas corridas memorizadas)."""
    hist = hist if hist is not None else cargar_historial()
    return {
        "corridas": len(hist),
        "desde": hist[0]["fecha"] if hist else "",
        "hasta": hist[-1]["fecha"] if hist else "",
    }

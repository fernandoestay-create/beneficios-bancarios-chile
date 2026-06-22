#!/usr/bin/env python3
"""
diagnosticar.py — Guarda el HTML crudo de los bancos CAIDOS para arreglo rapido.

Cuando un banco cae por cambio de estructura de su web, re-fetchea su URL y
guarda la pagina en diagnostico/<banco>.html. Asi, cuando le pidas a Claude
"arregla el scraper de X", el HTML del momento de la caida ya esta listo para
diagnosticar que cambio en el sitio.

Uso:
  python diagnosticar.py --desde-status        # los caidos/degradados de scrape_status.json
  python diagnosticar.py "Banco Falabella"     # un banco puntual
"""
import sys, os, json

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import requests
import scrapers

# Banco -> clase scraper (mismo set que el orquestador en scrapers.py)
CLASES = {
    "Banco de Chile": scrapers.ScraperBancoChile,
    "Banco Falabella": scrapers.ScraperBancoFalabella,
    "BCI": scrapers.ScraperBCI,
    "Banco Itaú": scrapers.ScraperItau,
    "Scotiabank": scrapers.ScraperScotiabank,
    "Santander": scrapers.ScraperSantander,
    "Banco Consorcio": scrapers.ScraperConsorcio,
    "BancoEstado": scrapers.ScraperBancoEstado,
    "Banco Security": scrapers.ScraperBancoSecurity,
    "Banco Ripley": scrapers.ScraperBancoRipley,
    "Entel": scrapers.ScraperEntel,
    "Tenpo": scrapers.ScraperTenpo,
    "Lider BCI": scrapers.ScraperLiderBCI,
    "Banco BICE": scrapers.ScraperBICE,
    "Mach": scrapers.ScraperMach,
}


def _url_de(clase):
    """Saca la URL principal del scraper: atributo de clase, o de instancia."""
    for attr in ("URL", "API_URL", "BASE_URL", "BASE", "URL_BASE"):
        u = getattr(clase, attr, None)
        if isinstance(u, str) and u.startswith("http"):
            return u
    try:
        inst = clase()
        for attr in ("url", "URL", "api_url", "API_URL", "base_url"):
            u = getattr(inst, attr, None)
            if isinstance(u, str) and u.startswith("http"):
                return u
    except Exception:
        pass
    return None


def diagnosticar(banco):
    clase = CLASES.get(banco)
    if not clase:
        print(f"  {banco}: sin clase scraper conocida")
        return
    url = _url_de(clase)
    if not url:
        print(f"  {banco}: no se pudo determinar la URL (revisar la clase a mano)")
        return
    os.makedirs(os.path.join(ROOT, "diagnostico"), exist_ok=True)
    dest = os.path.join(ROOT, "diagnostico", banco.replace(" ", "_") + ".html")
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"  {banco}: HTTP {r.status_code}, {len(r.text)} bytes -> {dest}")
    except Exception as e:
        print(f"  {banco}: ERROR al fetchear {url} -> {e}")


def _caidos_de_status():
    path = os.path.join(ROOT, "scrape_status.json")
    if not os.path.exists(path):
        return []
    st = json.load(open(path, encoding="utf-8"))
    caidos = [p["banco"] for p in st.get("preservados", [])]
    degr = [r["banco"] for r in st.get("reporte_por_banco", []) if r.get("estado") == "DEGRADADO"]
    return list(dict.fromkeys(caidos + degr))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--desde-status" in args:
        bancos = _caidos_de_status()
        if not bancos:
            print("Sin bancos caidos/degradados que diagnosticar.")
            sys.exit(0)
        print(f"Diagnosticando {len(bancos)} banco(s) con problema...")
        for b in bancos:
            diagnosticar(b)
    elif args:
        for b in args:
            diagnosticar(b)
    else:
        print(__doc__)

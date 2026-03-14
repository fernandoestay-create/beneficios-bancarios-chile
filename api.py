"""
API REST - BENEFICIOS BANCARIOS
================================
FastAPI + OpenAI RAG
"""

from fastapi import FastAPI, HTTPException, Query, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import quote_plus
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Importar scrapers
from scrapers import Beneficio, OrquestadorScrapers

# ============================================
# MODELOS PYDANTIC
# ============================================

class BeneficioResponse(BaseModel):
    id: str
    banco: str
    tarjeta: str
    restaurante: str
    descuento_valor: float
    descuento_tipo: str
    descuento_texto: str
    dias_validos: List[str]
    ubicacion: str
    ciudad: str = ""
    presencial: bool
    online: bool
    restricciones_texto: str
    activo: bool
    fecha_scrape: str
    descripcion: str = ""
    valido_desde: str = ""
    valido_hasta: str = ""
    url_fuente: str = ""
    imagen_url: str = ""
    logo_url: str = ""
    direccion: str = ""

    class Config:
        from_attributes = True

class ConsultaRAG(BaseModel):
    pregunta: str
    banco: Optional[str] = None
    dia: Optional[str] = None

class RespuestaRAG(BaseModel):
    pregunta: str
    respuesta: str
    beneficios_encontrados: List[BeneficioResponse]
    timestamp: str

# ============================================
# INICIALIZACIÓN
# ============================================

app = FastAPI(
    title="API Beneficios Bancarios Chile",
    description="API para consultar descuentos de bancos chilenos en restaurantes",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

beneficios_db: List[Beneficio] = []
timestamp_ultimo_scrape = None

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def inicializar_datos():
    global beneficios_db, timestamp_ultimo_scrape

    # Resolver ruta relativa al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "beneficios.json")

    if os.path.exists(json_path):
        print(f"📁 Cargando beneficios desde {json_path}...")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            beneficios_db = [Beneficio(**item) for item in data]
            timestamp_ultimo_scrape = datetime.now().isoformat()
            print(f"✅ Cargados {len(beneficios_db)} beneficios")
    else:
        print("⚠️ beneficios.json no encontrado. Ejecuta 'python scrapers.py' primero.")
        print("   Intentando scraping de Banco de Chile solamente...")
        from scrapers import ScraperBancoChile
        scraper = ScraperBancoChile()
        beneficios_db = scraper.scrapear()
        timestamp_ultimo_scrape = datetime.now().isoformat()


def buscar_beneficios(
    restaurante: Optional[str] = None,
    banco: Optional[str] = None,
    dia: Optional[str] = None,
    min_descuento: int = 0,
    ubicacion: Optional[str] = None,
) -> List[Beneficio]:
    resultados = beneficios_db

    if restaurante:
        restaurante_lower = restaurante.lower()
        resultados = [b for b in resultados if restaurante_lower in b.restaurante.lower()]

    if banco:
        banco_lower = banco.lower()
        resultados = [b for b in resultados if banco_lower in b.banco.lower()]

    if dia:
        dia_lower = dia.lower()
        resultados = [
            b for b in resultados
            if dia_lower in [d.lower() for d in b.dias_validos]
            or 'todos' in [d.lower() for d in b.dias_validos]
        ]

    if min_descuento > 0:
        resultados = [b for b in resultados if b.descuento_valor >= min_descuento]

    if ubicacion:
        ubicacion_lower = ubicacion.lower()
        resultados = [b for b in resultados if ubicacion_lower in b.ubicacion.lower()]

    return resultados


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def get_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY")
    host = os.getenv("PINECONE_HOST")
    index_name = os.getenv("PINECONE_INDEX", "beneficios-bancarios")
    if not api_key or not host:
        return None
    from pinecone import Pinecone
    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name, host=f"https://{host}")


def buscar_semantico(pregunta: str, top_k: int = 10) -> List[dict]:
    """Búsqueda semántica en Pinecone"""
    openai_client = get_openai_client()
    index = get_pinecone_index()
    if not openai_client or not index:
        return []

    # Generar embedding de la pregunta
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[pregunta],
    )
    query_vector = response.data[0].embedding

    # Buscar en Pinecone
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        namespace="beneficios-bancarios",
    )

    return [
        {
            "id": m.id,
            "score": m.score,
            **m.metadata,
        }
        for m in results.matches
    ]


async def consultar_openai(pregunta: str, contexto: str) -> str:
    """Consulta a OpenAI con contexto RAG"""
    openai_client = get_openai_client()
    if not openai_client:
        return "⚠️ OPENAI_API_KEY no configurada. Configúrala en el archivo .env"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente experto en beneficios y descuentos bancarios "
                        "de restaurantes en Chile. Responde de forma concisa, útil y amigable. "
                        "Basa tus respuestas SOLO en los datos proporcionados. "
                        "Incluye siempre el nombre del restaurante, banco, descuento y días válidos."
                    )
                },
                {
                    "role": "user",
                    "content": f"Datos de beneficios disponibles:\n{contexto}\n\nPregunta: {pregunta}"
                }
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error al consultar OpenAI: {str(e)}"


# ============================================
# ENDPOINTS
# ============================================

@app.on_event("startup")
async def startup():
    inicializar_datos()


@app.get("/")
async def root():
    return {
        "status": "API funcionando",
        "total_beneficios": len(beneficios_db),
        "ultimo_scrape": timestamp_ultimo_scrape,
        "endpoints": {
            "GET /beneficios": "Listar todos los beneficios",
            "GET /beneficios/buscar": "Buscar con filtros",
            "GET /beneficios/{id}": "Obtener beneficio por ID",
            "GET /bancos": "Listar bancos disponibles",
            "GET /estadisticas": "Estadísticas generales",
            "GET /restaurantes/top": "Top restaurantes",
            "POST /rag": "Consultar con IA (OpenAI)",
        }
    }


@app.get("/beneficios", response_model=List[BeneficioResponse])
async def listar_beneficios(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return beneficios_db[skip:skip + limit]


@app.get("/beneficios/buscar", response_model=List[BeneficioResponse])
async def buscar(
    restaurante: Optional[str] = Query(None, description="Nombre del restaurante"),
    banco: Optional[str] = Query(None, description="Nombre del banco"),
    dia: Optional[str] = Query(None, description="Día de la semana"),
    min_descuento: int = Query(0, ge=0, description="Descuento mínimo %"),
    ubicacion: Optional[str] = Query(None, description="Región o ciudad"),
):
    resultados = buscar_beneficios(restaurante, banco, dia, min_descuento, ubicacion)
    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontraron beneficios")
    return resultados


@app.get("/beneficios/{beneficio_id}", response_model=BeneficioResponse)
async def obtener_beneficio(beneficio_id: str):
    for b in beneficios_db:
        if b.id == beneficio_id:
            return b
    raise HTTPException(status_code=404, detail="Beneficio no encontrado")


@app.get("/bancos")
async def listar_bancos():
    bancos_stats = {}
    for b in beneficios_db:
        if b.banco not in bancos_stats:
            bancos_stats[b.banco] = {"total": 0, "descuento_promedio": 0, "descuentos": []}
        bancos_stats[b.banco]["total"] += 1
        bancos_stats[b.banco]["descuentos"].append(b.descuento_valor)

    resultado = {}
    for banco, stats in bancos_stats.items():
        vals = [v for v in stats["descuentos"] if v > 0]
        resultado[banco] = {
            "total_beneficios": stats["total"],
            "descuento_promedio": round(sum(vals) / len(vals), 1) if vals else 0,
            "descuento_maximo": max(vals) if vals else 0,
        }

    return {"total_bancos": len(resultado), "bancos": resultado}


@app.get("/estadisticas")
async def estadisticas():
    vals = [b.descuento_valor for b in beneficios_db if b.descuento_valor > 0]
    return {
        "total_beneficios": len(beneficios_db),
        "total_bancos": len(set(b.banco for b in beneficios_db)),
        "total_restaurantes": len(set(b.restaurante for b in beneficios_db)),
        "descuento_promedio": round(sum(vals) / len(vals), 1) if vals else 0,
        "descuento_maximo": max(vals) if vals else 0,
        "bancos": list(set(b.banco for b in beneficios_db)),
        "ultimo_scrape": timestamp_ultimo_scrape,
    }


@app.get("/restaurantes/top")
async def top_restaurantes(limit: int = Query(10, ge=1, le=50)):
    rest_info = {}
    for b in beneficios_db:
        if b.restaurante not in rest_info:
            rest_info[b.restaurante] = {"count": 0, "max_descuento": 0, "bancos": set()}
        rest_info[b.restaurante]["count"] += 1
        rest_info[b.restaurante]["max_descuento"] = max(rest_info[b.restaurante]["max_descuento"], b.descuento_valor)
        rest_info[b.restaurante]["bancos"].add(b.banco)

    top = sorted(rest_info.items(), key=lambda x: x[1]["max_descuento"], reverse=True)[:limit]
    return [
        {
            "restaurante": r,
            "cantidad_descuentos": info["count"],
            "max_descuento": info["max_descuento"],
            "bancos": list(info["bancos"]),
        }
        for r, info in top
    ]


@app.post("/rag", response_model=RespuestaRAG)
async def consulta_rag(consulta: ConsultaRAG):
    """Consulta con IA usando RAG (Pinecone + OpenAI)"""
    pregunta = consulta.pregunta

    # 1. Búsqueda semántica en Pinecone
    resultados_semanticos = buscar_semantico(pregunta, top_k=15)

    # 2. También filtrar por banco/día si se especifica
    beneficios_filtrados = buscar_beneficios(banco=consulta.banco, dia=consulta.dia)

    # 3. Combinar resultados: semánticos + filtrados
    if resultados_semanticos:
        # Contexto desde Pinecone (semántico)
        contexto = "\n".join([
            f"- {r['restaurante']}: {r['descuento_texto']} ({r['banco']}) - "
            f"Días: {r.get('dias_validos', '')} - {r.get('ubicacion', '')} "
            f"(relevancia: {r['score']:.2f})"
            for r in resultados_semanticos
        ])

        # Mapear IDs semánticos a beneficios completos
        ids_semanticos = {r["id"] for r in resultados_semanticos}
        beneficios_relevantes = [b for b in beneficios_db if b.id in ids_semanticos]
    else:
        # Fallback: búsqueda por palabras clave
        beneficios_relevantes = beneficios_filtrados
        if not beneficios_relevantes:
            palabras = pregunta.lower().split()
            for palabra in palabras:
                if len(palabra) > 3:
                    resultados = buscar_beneficios(restaurante=palabra)
                    if resultados:
                        beneficios_relevantes = resultados
                        break

        if not beneficios_relevantes:
            beneficios_relevantes = sorted(
                beneficios_db, key=lambda b: b.descuento_valor, reverse=True
            )[:20]

        contexto = "\n".join([
            f"- {b.restaurante}: {b.descuento_texto} ({b.banco}) - "
            f"Días: {', '.join(b.dias_validos)} - {b.ubicacion}"
            for b in beneficios_relevantes[:15]
        ])

    respuesta = await consultar_openai(pregunta, contexto)

    return RespuestaRAG(
        pregunta=pregunta,
        respuesta=respuesta,
        beneficios_encontrados=beneficios_relevantes[:5],
        timestamp=datetime.now().isoformat(),
    )


# ============================================
# SCRAPING ENDPOINTS
# ============================================

@app.post("/scrape/ejecutar")
async def ejecutar_scrape():
    """Ejecuta scraping (solo Banco de Chile por API, Falabella requiere CLI)"""
    global beneficios_db, timestamp_ultimo_scrape

    print("🚀 Ejecutando scraping de Banco de Chile...")
    from scrapers import ScraperBancoChile
    scraper = ScraperBancoChile()
    nuevos = scraper.scrapear()

    # Mantener beneficios de Falabella existentes
    falabella_existentes = [b for b in beneficios_db if 'Falabella' in b.banco]
    beneficios_db = nuevos + falabella_existentes
    timestamp_ultimo_scrape = datetime.now().isoformat()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "beneficios.json")
    data = [b.to_dict() for b in beneficios_db]
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "status": "Scraping completado",
        "total_beneficios": len(beneficios_db),
        "timestamp": timestamp_ultimo_scrape,
    }


@app.get("/scrape/status")
async def scrape_status():
    return {
        "total_beneficios": len(beneficios_db),
        "ultimo_scrape": timestamp_ultimo_scrape,
        "estado": "activo" if beneficios_db else "sin datos",
    }


# ============================================
# ACCESO TEMPORAL — tokens con fecha de expiración
# ============================================

# Tokens de acceso: {"clave": fecha_expiración}
# Para agregar uno nuevo: TOKENS_ACCESO["nuevaclave"] = datetime(2026, 3, 20)
TOKENS_ACCESO = {
    "prueba": datetime(2026, 3, 15, 23, 59, 59),   # caduca 15 marzo 2026
}

# Modo público: si es True, no pide clave (para cuando quieras abrir la página)
ACCESO_PUBLICO = False


def _login_page(error: str = ""):
    """Página simple de login para acceso temporal"""
    err_html = f'<p style="color:#e74c3c;margin-bottom:12px">{error}</p>' if error else ''
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Acceso — Beneficios Bancarios</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;
display:flex;align-items:center;justify-content:center}}
.card{{background:#fff;border-radius:16px;padding:40px 36px;width:360px;
box-shadow:0 20px 60px rgba(0,0,0,.3);text-align:center}}
.card h1{{font-size:22px;color:#333;margin-bottom:6px}}
.card p.sub{{font-size:13px;color:#888;margin-bottom:24px}}
.card input{{width:100%;padding:12px 16px;border:2px solid #e0e0e0;border-radius:10px;
font-size:15px;outline:none;transition:border .2s}}
.card input:focus{{border-color:#667eea}}
.card button{{width:100%;padding:12px;margin-top:14px;border:none;border-radius:10px;
background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;font-size:15px;
font-weight:600;cursor:pointer;transition:opacity .2s}}
.card button:hover{{opacity:.9}}
.emoji{{font-size:48px;margin-bottom:12px}}
</style></head><body>
<div class="card">
<div class="emoji">🔒</div>
<h1>Acceso de prueba</h1>
<p class="sub">Ingresa la clave que te compartieron</p>
{err_html}
<form method="POST" action="/ver/login">
<input type="text" name="clave" placeholder="Clave de acceso" autocomplete="off" autofocus>
<button type="submit">Entrar</button>
</form>
</div></body></html>"""


@app.post("/ver/login", response_class=HTMLResponse)
async def ver_login(clave: str = Form(...)):
    """Valida la clave y setea cookie de sesión"""
    clave = clave.strip().lower()
    if clave not in TOKENS_ACCESO:
        return HTMLResponse(_login_page("Clave incorrecta"), status_code=401)
    if datetime.now() > TOKENS_ACCESO[clave]:
        return HTMLResponse(_login_page("Esta clave ya caducó ⏰"), status_code=403)
    # Cookie válida por 24h
    resp = RedirectResponse("/ver", status_code=303)
    resp.set_cookie("acceso_key", clave, max_age=86400, httponly=True)
    return resp


# ============================================
# PÁGINA WEB - TABLA COMPLETA DE RESULTADOS
# ============================================

@app.get("/ver", response_class=HTMLResponse)
async def ver_resultados(
    dia: Optional[str] = Query(None, description="Día de la semana"),
    banco: Optional[str] = Query(None, description="Nombre del banco"),
    q: Optional[str] = Query(None, description="Búsqueda libre"),
    key: Optional[str] = Query(None, description="Clave de acceso temporal"),
    acceso_key: Optional[str] = Cookie(None),
):
    """Genera página HTML con cards de beneficios, filtros interactivos e imágenes"""
    import html as html_lib

    # --- Control de acceso temporal ---
    if not ACCESO_PUBLICO:
        # Prioridad: query param > cookie
        token = (key or "").strip().lower() or (acceso_key or "").strip().lower()
        if not token or token not in TOKENS_ACCESO:
            return HTMLResponse(_login_page())
        if datetime.now() > TOKENS_ACCESO[token]:
            return HTMLResponse(_login_page("Esta clave ya caducó ⏰"), status_code=403)
        # Si vino por query param, setear cookie para no pedir de nuevo
        # (se hace al final del response)

    all_data = beneficios_db
    # Serializar a JSON para filtros en JS
    deals_json = json.dumps([
        {
            "banco": b.banco,
            "restaurante": b.restaurante,
            "descuento_valor": b.descuento_valor,
            "descuento_texto": b.descuento_texto,
            "dias_validos": b.dias_validos,
            "ubicacion": b.ubicacion,
            "direccion": getattr(b, 'direccion', ''),
            "presencial": b.presencial,
            "online": b.online,
            "url_fuente": b.url_fuente,
            "imagen_url": getattr(b, 'imagen_url', ''),
            "logo_url": getattr(b, 'logo_url', ''),
            "valido_hasta": b.valido_hasta,
            "descripcion": getattr(b, 'descripcion', ''),
            "tarjeta": b.tarjeta,
            "comuna": getattr(b, 'comuna', ''),
        }
        for b in all_data
    ], ensure_ascii=False)

    bancos_list = sorted(set(b.banco for b in all_data))
    REGIONES_VALIDAS = {
        'Arica y Parinacota', 'Tarapacá', 'Antofagasta', 'Atacama', 'Coquimbo',
        'Valparaíso', 'Metropolitana', "O'Higgins", 'Maule', 'Ñuble', 'Biobío',
        'Araucanía', 'Los Ríos', 'Los Lagos', 'Aysén', 'Magallanes',
    }
    _regiones_set = set(r for r in set(b.ubicacion for b in all_data if b.ubicacion) if r in REGIONES_VALIDAS)
    regiones_list = (['Metropolitana'] if 'Metropolitana' in _regiones_set else []) + sorted(r for r in _regiones_set if r != 'Metropolitana')
    comunas_list = sorted(set(b.comuna for b in all_data if b.comuna and b.ubicacion == 'Metropolitana'))
    banco_options = "".join(f'<option value="{html_lib.escape(b)}">{html_lib.escape(b)}</option>' for b in bancos_list)
    region_options = "".join(f'<option value="{html_lib.escape(r)}">{html_lib.escape(r)}</option>' for r in regiones_list)
    comuna_options = "".join(f'<option value="{html_lib.escape(c)}">{html_lib.escape(c)}</option>' for c in comunas_list)
    bancos_json_list = json.dumps(bancos_list, ensure_ascii=False)
    regiones_json_list = json.dumps(regiones_list, ensure_ascii=False)
    comunas_json_list = json.dumps(comunas_list, ensure_ascii=False)

    # Pre-selección de filtros desde URL
    init_dia = f'"{dia}"' if dia else 'null'
    init_banco = f'"{banco}"' if banco else 'null'
    init_q = f'"{q}"' if q else 'null'

    total = len(all_data)
    total_bancos = len(bancos_list)
    total_rest = len(set(b.restaurante for b in all_data))
    vals = [b.descuento_valor for b in all_data if b.descuento_valor > 0]
    max_desc = max(vals) if vals else 0

    page_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Descuentos Bancarios Chile</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
:root{{--bg:#f8f7f4;--panel:#fff;--panel2:#f3f1ed;--text:#1a1a2e;--muted:#6b7280;--line:#e5e2da;
--primary:#4f46e5;--primary2:#7c3aed;--ok:#16a34a;--warn:#ea580c;--radius:16px;
--shadow:0 4px 20px rgba(0,0,0,.06);}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text);}}
.container{{width:min(1260px,calc(100% - 24px));margin:0 auto;padding:20px 0 60px}}
.hero{{display:grid;grid-template-columns:1.4fr .8fr;gap:16px;margin-bottom:20px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}}
.hero-main{{padding:28px;background:linear-gradient(135deg,#faf5ff,#eff6ff)}}
.eyebrow{{display:inline-flex;align-items:center;gap:6px;background:rgba(79,70,229,.08);
border:1px solid rgba(79,70,229,.15);color:var(--primary);padding:6px 12px;border-radius:999px;font-size:12px;font-weight:600}}
h1{{margin:12px 0 6px;font-size:clamp(24px,4vw,38px);line-height:1.1;font-weight:800;
background:linear-gradient(135deg,var(--primary),var(--primary2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{color:var(--muted);font-size:14px;line-height:1.6}}
.stats-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:16px}}
.stat{{background:var(--panel2);border-radius:14px;padding:16px;text-align:center}}
.stat .val{{font-size:28px;font-weight:800;color:var(--primary)}}
.stat .lbl{{color:var(--muted);font-size:12px;margin-top:2px}}
/* View toggle (inside results) */
.view-toggle{{display:flex;gap:4px;margin-bottom:16px;background:var(--panel2);padding:4px;border-radius:12px;width:fit-content}}
.view-btn{{border:0;background:transparent;color:var(--muted);padding:10px 20px;border-radius:10px;
font-weight:700;font-size:14px;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:6px}}
.view-btn.active{{background:var(--panel);color:var(--primary);box-shadow:var(--shadow)}}
.view-btn:hover:not(.active){{color:var(--text)}}
.view-content{{display:none}}.view-content.active{{display:block}}
.layout{{display:grid;grid-template-columns:280px 1fr;gap:16px;align-items:start}}
.filters{{position:sticky;top:12px;padding:18px}}
.filters h2{{font-size:16px;margin-bottom:14px;font-weight:700}}
.group{{margin-bottom:14px}}
.group label{{display:block;font-size:12px;color:var(--muted);margin-bottom:5px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.input,select{{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);
color:var(--text);font-size:13px;outline:none;transition:border .2s}}
.input:focus,select:focus{{border-color:var(--primary)}}
.chips{{display:flex;flex-wrap:wrap;gap:6px}}
.chip{{border:1px solid var(--line);background:var(--panel2);color:var(--text);padding:6px 11px;border-radius:999px;
font-size:12px;cursor:pointer;font-weight:500;transition:all .15s}}
.chip:hover{{border-color:var(--primary);background:#f5f3ff}}
.chip.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));border-color:transparent;color:#fff}}
/* Day circle multi-select */
.day-select{{display:flex;align-items:center;gap:2px;flex-wrap:nowrap}}
.day-sel{{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-size:9px;font-weight:700;border:1.5px solid var(--line);color:var(--muted);background:var(--panel2);
cursor:pointer;transition:all .15s;user-select:none;flex-shrink:0}}
.day-sel:hover{{border-color:var(--primary);color:var(--primary)}}
.day-sel.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));border-color:transparent;color:#fff}}
.day-sel-all{{width:auto;padding:0 8px;border-radius:999px;font-size:9px;letter-spacing:.3px;flex-shrink:0}}
.range-row{{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center}}
input[type=range]{{accent-color:var(--primary)}}
.btns{{display:flex;gap:8px;margin-top:10px}}
.btns-top{{margin-top:0;margin-bottom:10px;position:sticky;top:0;z-index:5;background:var(--panel);padding:6px 0}}
.btns-bottom{{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}}
button{{border:0;border-radius:10px;padding:10px 14px;font-weight:700;cursor:pointer;font-size:13px}}
.btn-primary{{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;flex:1}}
.btn-secondary{{background:var(--panel2);color:var(--text);border:1px solid var(--line)}}
.btn-sm{{padding:7px 14px;font-size:12px;font-weight:600;border-radius:8px}}
.btn-link{{background:none;color:var(--muted);font-size:12px;font-weight:500;padding:6px 10px;text-decoration:underline;text-underline-offset:2px}}
.results{{padding:18px}}
.toolbar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px}}
.pill{{padding:6px 12px;border-radius:999px;background:rgba(22,163,74,.08);color:var(--ok);
border:1px solid rgba(22,163,74,.15);font-size:12px;font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
.deal{{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;
display:flex;flex-direction:column;transition:box-shadow .2s,transform .15s}}
.deal:hover{{box-shadow:0 8px 30px rgba(0,0,0,.1);transform:translateY(-2px)}}
.deal-img{{height:160px;background:#f3f1ed;position:relative;overflow:hidden}}
.deal-img img{{width:100%;height:100%;object-fit:cover}}
.deal-img .badge{{position:absolute;top:10px;right:10px;background:linear-gradient(135deg,var(--primary),var(--primary2));
color:#fff;padding:6px 12px;border-radius:10px;font-weight:800;font-size:14px}}
.deal-img .bank-badge{{position:absolute;top:10px;left:10px;background:rgba(255,255,255,.95);
backdrop-filter:blur(6px);padding:5px 10px;border-radius:8px;display:flex;align-items:center;gap:6px}}
.bank-badge img{{height:18px;width:auto;display:block}}
.bank-badge span{{font-size:0;}}
.deal-body{{padding:14px;flex:1;display:flex;flex-direction:column;gap:8px}}
.deal-title{{font-size:16px;font-weight:700}}
.deal-desc{{color:var(--muted);font-size:13px;line-height:1.5}}
.day-bar{{display:flex;align-items:center;gap:6px;background:#f5f3ff;border:1px solid var(--line);border-radius:10px;padding:8px 10px}}
.day-circles{{display:flex;gap:4px;flex:1}}
.day-circle{{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-size:11px;font-weight:700;border:2px solid #e0dce8;color:#bbb;background:#fff;transition:all .2s}}
.day-circle.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));border-color:transparent;color:#fff}}
.mode-badge{{font-size:11px;font-weight:600;padding:4px 8px;border-radius:6px;white-space:nowrap}}
.mode-badge.presencial{{background:#e8f5e9;color:#2e7d32}}
.mode-badge.online{{background:#e3f2fd;color:#1565c0}}
.deal-info{{display:flex;flex-direction:column;gap:4px}}
.deal-info-row{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}}
.deal-info-row svg,.deal-info-row .info-icon{{width:14px;flex-shrink:0}}
.cta-row{{display:flex;justify-content:center;padding-top:8px}}
.link{{color:#fff;text-decoration:none;background:linear-gradient(135deg,var(--primary),var(--primary2));
padding:8px 20px;border-radius:10px;font-weight:700;font-size:13px;transition:opacity .2s}}
.link:hover{{opacity:.85}}
.deal-footer{{background:#f8f7f5;border-top:1px solid var(--line);padding:10px 14px;display:flex;flex-direction:column;gap:3px}}
.deal-footer .validity{{color:var(--muted);font-size:11px}}
.deal-footer .disclaimer{{color:#aaa;font-size:10px;font-style:italic}}
.empty{{display:none;text-align:center;padding:40px;color:var(--muted);border:2px dashed var(--line);border-radius:var(--radius)}}
.no-img{{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f3f1ed,#e8e5de);font-size:40px}}
.footer{{text-align:center;margin-top:24px;color:var(--muted);font-size:12px}}
/* Multi-select */
.multi-select{{position:relative}}
.ms-trigger{{width:100%;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);
cursor:pointer;display:flex;align-items:center;min-height:40px;gap:4px;flex-wrap:wrap}}
.ms-placeholder{{color:var(--muted);font-size:13px}}
.ms-tags{{display:flex;flex-wrap:wrap;gap:4px;flex:1}}
.ms-tag{{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;padding:2px 8px;
border-radius:6px;font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:3px;white-space:nowrap}}
.ms-remove{{cursor:pointer;font-size:14px;line-height:1;opacity:.8}}.ms-remove:hover{{opacity:1}}
.ms-arrow{{margin-left:auto;color:var(--muted);font-size:12px;flex-shrink:0}}
.ms-dropdown{{display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;background:var(--panel);
border:1px solid var(--line);border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.12);z-index:100;
max-height:220px;overflow-y:auto;padding:4px}}
.multi-select.open .ms-dropdown{{display:block}}
.ms-option{{padding:7px 10px;display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;border-radius:6px}}
.ms-option:hover{{background:var(--panel2)}}
.ms-option input{{accent-color:var(--primary);width:16px;height:16px;cursor:pointer}}
.ms-search-input{{width:calc(100% - 8px);margin:4px;padding:7px 10px;border-radius:8px;border:1px solid var(--line);
font-size:12px;outline:none;background:var(--panel2)}}.ms-search-input:focus{{border-color:var(--primary)}}
/* Summary bar */
.summary-bar{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;align-items:stretch;justify-content:center}}
.summary-pill{{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
padding:8px 4px 6px;border-radius:10px;background:var(--panel2);border:1px solid var(--line);
width:68px;cursor:pointer;transition:all .15s;user-select:none}}
.summary-pill:hover{{border-color:var(--primary);background:#f5f3ff}}
.summary-pill.active{{background:linear-gradient(135deg,rgba(79,70,229,.1),rgba(124,58,237,.1));
border-color:var(--primary);box-shadow:0 0 0 2px rgba(79,70,229,.2)}}
.summary-pill .sp-logo{{height:22px;display:flex;align-items:center;justify-content:center;flex:1}}
.summary-pill .sp-logo img{{height:100%;width:auto;max-width:56px;object-fit:contain}}
.summary-pill .sp-nologo{{font-size:9px;font-weight:700;color:var(--muted);
text-align:center;line-height:1.1;max-width:56px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;
height:22px;display:flex;align-items:center;justify-content:center}}
.summary-pill .sp-ct{{font-weight:800;font-size:14px;color:var(--primary);margin-top:4px}}
/* Map */
#map{{height:calc(100vh - 260px);min-height:450px;border-radius:var(--radius);border:1px solid var(--line)}}
.leaflet-popup-content{{font-family:Inter,sans-serif;font-size:13px;line-height:1.5}}
.popup-title{{font-weight:700;font-size:15px;margin-bottom:4px}}
.popup-bank{{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;margin-bottom:4px}}
.popup-bank img{{height:14px}}
.popup-desc{{color:var(--muted);margin:4px 0}}
.popup-link{{display:inline-block;background:var(--primary);color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-weight:600;font-size:12px;margin-top:4px}}
@media(max-width:980px){{.hero,.layout,.grid{{grid-template-columns:1fr}}.stats-grid{{grid-template-columns:1fr}}
.filters{{position:static}}.deal-img{{height:140px}}#map{{height:60vh}}
.day-circle{{width:24px;height:24px;font-size:10px}}.day-bar{{gap:4px;padding:6px 8px}}}}
</style>
</head>
<body>
<div class="container">
<section class="hero">
<div class="card hero-main">
<div class="eyebrow">🍽️ Desde tu bot de WhatsApp</div>
<h1>Descuentos bancarios en restaurantes de Chile</h1>
<p class="sub">Todos los beneficios de Banco de Chile, Banco Falabella y más, actualizados.
Filtra por banco, día, zona y descuento mínimo.</p>
</div>
<div class="card stats-grid">
<div class="stat"><div class="val">{total}</div><div class="lbl">Descuentos activos</div></div>
<div class="stat"><div class="val">{total_bancos}</div><div class="lbl">Bancos</div></div>
<div class="stat"><div class="val">{int(max_desc)}%</div><div class="lbl">Mejor descuento</div></div>
</div>
</section>
<section class="layout">
<aside class="card filters">
<h2>Filtros</h2>
<button class="btn-secondary" id="resetBtn" style="width:100%;margin-bottom:10px;font-size:12px;padding:7px 0">Limpiar filtros</button>
<div class="group"><label>Buscar</label>
<input id="search" class="input" type="text" placeholder="Ej: sushi, pizza..."></div>
<div class="group"><label>Banco</label>
<div class="multi-select" id="bankMS"></div></div>
<div class="group"><label>Día</label>
<div class="day-select" id="daySelect">
<div class="day-sel day-sel-all active" data-day="all">Todos</div>
<div class="day-sel" data-day="lunes">L</div>
<div class="day-sel" data-day="martes">M</div>
<div class="day-sel" data-day="miercoles">X</div>
<div class="day-sel" data-day="jueves">J</div>
<div class="day-sel" data-day="viernes">V</div>
<div class="day-sel" data-day="sabado">S</div>
<div class="day-sel" data-day="domingo">D</div>
</div></div>
<div class="group"><label>Zona</label>
<div class="multi-select" id="regionMS"></div></div>
<div class="group" id="comunaGroup" style="display:none"><label>Comuna</label>
<div class="multi-select" id="comunaMS"></div></div>
<div class="group"><label>Descuento mínimo</label>
<div class="range-row"><input id="minDisc" type="range" min="0" max="50" step="5" value="0">
<strong id="minDiscVal">0%</strong></div></div>
<div class="group"><label>Modalidad</label>
<div class="chips" id="modeChips">
<button class="chip active" data-mode="all">Todas</button>
<button class="chip" data-mode="presencial">🏪 Presencial</button>
<button class="chip" data-mode="online">💻 Online</button>
</div></div>
<div class="group" id="sortGroup"><label>Ordenar</label>
<select id="sortFilter">
<option value="desc-desc">Mayor descuento</option>
<option value="desc-asc">Menor descuento</option>
<option value="name">Nombre A-Z</option>
<option value="bank">Banco A-Z</option>
</select></div>
<button class="btn-secondary" id="resetBtn2" style="width:100%;margin-top:10px;font-size:12px;padding:7px 0">Limpiar filtros</button>
</aside>
<main class="card results">
<div class="view-toggle">
<button class="view-btn active" data-view="tarjetas">🍽️ Tarjetas</button>
<button class="view-btn" data-view="mapa">📍 Mapa</button>
</div>
<div id="view-tarjetas" class="view-content active">
<div class="toolbar">
<h2>Resultados</h2>
<span class="pill" id="count">0</span>
</div>
<div id="summaryBar" class="summary-bar"></div>
<div class="grid" id="grid"></div>
<div class="empty" id="empty">No hay descuentos con esos filtros 🤷</div>
</div>
<div id="view-mapa" class="view-content">
<div class="toolbar">
<h2>Mapa</h2>
<span class="pill" id="mapCount">0 en mapa</span>
</div>
<div id="map"></div>
<p style="color:var(--muted);font-size:11px;margin-top:8px;text-align:center">📍 Solo se muestran restaurantes con dirección conocida</p>
</div>
</main>
</section>
<div class="footer">Actualizado: {timestamp_ultimo_scrape or 'N/A'} · Beneficios Bancarios Chile 🇨🇱</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const deals={deals_json};

// ── Bank logos ──
const BANK_LOGOS={{
'Banco de Chile':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Banco_de_Chile_Logotipo.svg/200px-Banco_de_Chile_Logotipo.svg.png',
'Banco Falabella':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Logotipo_Banco_Falabella.svg/200px-Logotipo_Banco_Falabella.svg.png',
'BCI':'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Bci_Logotype.svg/200px-Bci_Logotype.svg.png',
'Banco Itaú':'https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Ita%C3%BA_Unibanco_logo_2023.svg/200px-Ita%C3%BA_Unibanco_logo_2023.svg.png',
'Scotiabank':'https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Scotiabank_logo.svg/200px-Scotiabank_logo.svg.png',
'Santander':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Banco_Santander_Logotipo.svg/200px-Banco_Santander_Logotipo.svg.png',
'Banco Consorcio':'https://upload.wikimedia.org/wikipedia/commons/thumb/d/dc/Logo_consorcio.svg/200px-Logo_consorcio.svg.png',
'BancoEstado':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Logo_BancoEstado.svg/200px-Logo_BancoEstado.svg.png',
'Banco Security':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Logo_empresa_banco_security.png/200px-Logo_empresa_banco_security.png',
'Banco Ripley':'https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Logo_Ripley_banco_2.png/200px-Logo_Ripley_banco_2.png',
'Entel':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/EntelChile_Logo.svg/200px-EntelChile_Logo.svg.png',
'Tenpo':'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Logotipo_Tenpo.svg/200px-Logotipo_Tenpo.svg.png',
'Lider BCI':'https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Lider_2025.svg/200px-Lider_2025.svg.png',
'Banco BICE':'https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Bice-logo.svg/200px-Bice-logo.svg.png',
'Mach':'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Logotipo_MACH.svg/200px-Logotipo_MACH.svg.png'
}};
const BANK_COLORS={{
'Banco de Chile':'#003DA5','Banco Falabella':'#00B140',
'BCI':'#E31837','Banco Itaú':'#003399','Scotiabank':'#EC111A',
'Santander':'#EC0000','Banco Consorcio':'#003366','BancoEstado':'#00A651',
'Banco Security':'#1B3A5C','Banco Ripley':'#7B2D8E','Entel':'#FF6B00',
'Tenpo':'#00C389','Lider BCI':'#E31837','Banco BICE':'#002F6C','Mach':'#6B21A8'
}};
function bankBadgeHtml(banco){{
const logo=BANK_LOGOS[banco];
if(logo)return `<img src="${{logo}}" alt="${{banco}}" onerror="this.style.display='none';this.nextElementSibling.style.fontSize='11px'"><span>${{banco}}</span>`;
return `<span style="font-size:11px;font-weight:700">${{banco}}</span>`;
}}

// ── View toggle ──
let currentView='tarjetas';
document.querySelectorAll('.view-btn').forEach(btn=>{{btn.addEventListener('click',()=>{{
document.querySelectorAll('.view-btn').forEach(b=>b.classList.remove('active'));
document.querySelectorAll('.view-content').forEach(c=>c.classList.remove('active'));
btn.classList.add('active');
currentView=btn.dataset.view;
document.getElementById('view-'+currentView).classList.add('active');
// Show/hide sort (only for tarjetas)
document.getElementById('sortGroup').style.display=currentView==='tarjetas'?'':'none';
if(currentView==='mapa'){{initMap();setTimeout(()=>{{if(mapObj)mapObj.invalidateSize();renderMapMarkers()}},80)}}
}})}});

// ── Card grid ──
const grid=document.getElementById('grid'),empty=document.getElementById('empty'),
countEl=document.getElementById('count'),search=document.getElementById('search'),
comunaG=document.getElementById('comunaGroup'),
sortF=document.getElementById('sortFilter'),minD=document.getElementById('minDisc'),
minDV=document.getElementById('minDiscVal'),summaryBar=document.getElementById('summaryBar');

// ── Multi-Select Component ──
const bankOpts={bancos_json_list};
const regionOpts={regiones_json_list};
const comunaOpts={comunas_json_list};
class MS{{
constructor(id,opts,ph){{this.el=document.getElementById(id);this.opts=opts;this.sel=new Set();this.ph=ph;this._build()}}
_build(){{
const hs=this.opts.length>5;
this.el.innerHTML=`<div class="ms-trigger"><div class="ms-tags"><span class="ms-placeholder">${{this.ph}}</span></div><span class="ms-arrow">▾</span></div><div class="ms-dropdown">${{hs?'<input class="ms-search-input" placeholder="Buscar...">':''}}<div class="ms-opts">${{this.opts.map(o=>`<label class="ms-option"><input type="checkbox" value="${{o}}"> ${{o}}</label>`).join('')}}</div></div>`;
this.el.querySelector('.ms-trigger').addEventListener('click',e=>{{
if(e.target.closest('.ms-remove'))return;
document.querySelectorAll('.multi-select.open').forEach(x=>{{if(x!==this.el)x.classList.remove('open')}});
this.el.classList.toggle('open')}});
this.el.querySelectorAll('.ms-option input').forEach(cb=>{{cb.addEventListener('change',()=>{{
if(cb.checked)this.sel.add(cb.value);else this.sel.delete(cb.value);
this._tags();render()}})}});
const si=this.el.querySelector('.ms-search-input');
if(si){{si.addEventListener('input',()=>{{const q=si.value.toLowerCase();
this.el.querySelectorAll('.ms-option').forEach(o=>{{o.style.display=o.textContent.toLowerCase().includes(q)?'':'none'}})}});
si.addEventListener('click',e=>e.stopPropagation())}}
document.addEventListener('click',e=>{{if(!this.el.contains(e.target))this.el.classList.remove('open')}})}}
_tags(){{
const t=this.el.querySelector('.ms-tags');
if(!this.sel.size){{t.innerHTML=`<span class="ms-placeholder">${{this.ph}}</span>`;return}}
t.innerHTML=[...this.sel].map(v=>`<span class="ms-tag">${{v}}<span class="ms-remove" data-v="${{v}}">×</span></span>`).join('');
t.querySelectorAll('.ms-remove').forEach(x=>{{x.addEventListener('click',e=>{{
e.stopPropagation();this.sel.delete(x.dataset.v);
const c=[...this.el.querySelectorAll('input[type=checkbox]')].find(c=>c.value===x.dataset.v);
if(c)c.checked=false;this._tags();render()}})}})}}
vals(){{return this.sel.size?[...this.sel]:null}}
reset(){{this.sel.clear();this.el.querySelectorAll('input[type=checkbox]').forEach(c=>c.checked=false);this._tags()}}
}}
const bankMS=new MS('bankMS',bankOpts,'Todos los bancos');
const regionMS=new MS('regionMS',regionOpts,'Todas las regiones');
const comunaMS=new MS('comunaMS',comunaOpts,'Todas las comunas');
// Show comunas when Metropolitana selected
regionMS.el.querySelectorAll('.ms-option input').forEach(cb=>{{cb.addEventListener('change',()=>{{
const rv=regionMS.vals();
if(rv&&rv.includes('Metropolitana')){{comunaG.style.display='block'}}
else{{comunaG.style.display='none';comunaMS.reset()}}
}})}});

function chipVal(id,attr){{const a=document.querySelector('#'+id+' .chip.active');return a?a.dataset[attr]:'all'}}
function initChips(id,attr){{document.getElementById(id).addEventListener('click',e=>{{
const c=e.target.closest('.chip');if(!c)return;
document.querySelectorAll('#'+id+' .chip').forEach(x=>x.classList.remove('active'));c.classList.add('active')}})}}
initChips('modeChips','mode');

// ── Day multi-select circles ──
const daySelect=document.getElementById('daySelect');
const dayAll=daySelect.querySelector('[data-day="all"]');
const daySels=[...daySelect.querySelectorAll('.day-sel:not(.day-sel-all)')];
function getSelectedDays(){{
  if(dayAll.classList.contains('active'))return null;
  const sel=daySels.filter(d=>d.classList.contains('active')).map(d=>d.dataset.day);
  return sel.length?sel:null;
}}
daySelect.addEventListener('click',e=>{{
  const d=e.target.closest('.day-sel');if(!d)return;
  if(d===dayAll){{
    dayAll.classList.add('active');daySels.forEach(s=>s.classList.remove('active'));
  }}else{{
    dayAll.classList.remove('active');d.classList.toggle('active');
    if(!daySels.some(s=>s.classList.contains('active')))dayAll.classList.add('active');
  }}
}});
minD.addEventListener('input',()=>{{minDV.textContent=minD.value+'%'}});

// ── Normalize for search ──
function norm(s){{return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/[^a-z0-9\\s]/g,'')}}

function render(){{
const qRaw=search.value.trim();
const qWords=qRaw?norm(qRaw).split(/\\s+/).filter(w=>w.length>0):[];
const banks=bankMS.vals(),regions=regionMS.vals(),comunas=comunaMS.vals();
const sort=sortF.value,min=+minD.value,selDays=getSelectedDays(),mode=chipVal('modeChips','mode');
let f=deals.filter(d=>{{
const txt=norm([d.restaurante,d.banco,d.descripcion||'',d.ubicacion||'',d.direccion||''].join(' '));
const mS=!qWords.length||qWords.every(w=>txt.includes(w));
const mB=!banks||banks.includes(d.banco);
const mR=!regions||regions.includes(d.ubicacion);
const mC=!comunas||comunas.includes(d.comuna);
const mD=d.descuento_valor>=min;
const mDay=!selDays||d.dias_validos.includes('todos')||selDays.some(sd=>d.dias_validos.includes(sd));
const mMode=mode==='all'||(mode==='presencial'&&d.presencial)||(mode==='online'&&d.online);
return mS&&mB&&mR&&mC&&mD&&mDay&&mMode}});
f.sort((a,b)=>{{switch(sort){{case'desc-asc':return a.descuento_valor-b.descuento_valor;
case'name':return a.restaurante.localeCompare(b.restaurante);
case'bank':return a.banco.localeCompare(b.banco);
default:return b.descuento_valor-a.descuento_valor}}}});
// ── Summary bar (count per bank) ──
const byBank={{}};f.forEach(d=>{{byBank[d.banco]=(byBank[d.banco]||0)+1}});
const bankEntries=Object.entries(byBank).sort((a,b)=>b[1]-a[1]);
if(bankEntries.length>0){{
summaryBar.style.display='flex';
const selBanks=bankMS.vals();
summaryBar.innerHTML=bankEntries.map(([b,c])=>{{
const logo=BANK_LOGOS[b];
const isActive=selBanks&&selBanks.includes(b);
const lh=logo?`<div class="sp-logo"><img src="${{logo}}" alt="${{b}}" onerror="this.parentNode.innerHTML='<span class=sp-nologo>${{b}}</span>'"></div>`
:`<span class="sp-nologo">${{b}}</span>`;
return `<span class="summary-pill${{isActive?' active':''}}" data-banco="${{b}}" title="${{b}}">${{lh}}<span class="sp-ct">${{c}}</span></span>`}}).join('');
summaryBar.querySelectorAll('.summary-pill').forEach(pill=>{{pill.addEventListener('click',()=>{{
const banco=pill.dataset.banco;
const cb=[...bankMS.el.querySelectorAll('input[type=checkbox]')].find(c=>c.value===banco);
if(cb){{cb.checked=!cb.checked;if(cb.checked)bankMS.sel.add(banco);else bankMS.sel.delete(banco);bankMS._tags();render()}}
}})}});
}}else{{summaryBar.style.display='none';summaryBar.innerHTML=''}}
grid.innerHTML='';
if(!f.length){{empty.style.display='block';countEl.textContent='0 encontrados';return}}
empty.style.display='none';countEl.textContent=f.length+' encontrados';
f.forEach(d=>{{
const imgSrc=d.imagen_url||d.logo_url;
const imgHtml=imgSrc?`<img src="${{imgSrc}}" alt="${{d.restaurante}}" loading="lazy">`
:`<div class="no-img">🍽️</div>`;
const DAY_MAP=[['lunes','L'],['martes','M'],['miercoles','X'],['jueves','J'],['viernes','V'],['sabado','S'],['domingo','D']];
const dayCircles=DAY_MAP.map(([k,l])=>{{
const on=d.dias_validos.includes(k)||d.dias_validos.includes('todos');
return `<div class="day-circle${{on?' active':''}}">${{l}}</div>`}}).join('');
const modeBadge=d.online?'<span class="mode-badge online">💻 Online</span>'
:'<span class="mode-badge presencial">🏪 Pres.</span>';
const linkHtml=d.url_fuente?`<a class="link" href="${{d.url_fuente}}" target="_blank">Ver detalle</a>`:'';
const el=document.createElement('article');el.className='deal';
el.innerHTML=`<div class="deal-img">${{imgHtml}}
<div class="badge">${{d.descuento_texto||d.descuento_valor+'%'}}</div>
<div class="bank-badge">${{bankBadgeHtml(d.banco)}}</div></div>
<div class="deal-body"><div class="deal-title">${{d.restaurante}}</div>
${{d.descripcion?`<div class="deal-desc">${{d.descripcion.slice(0,100)}}</div>`:''}}
<div class="day-bar"><div class="day-circles">${{dayCircles}}</div>${{modeBadge}}</div>
<div class="deal-info">
<div class="deal-info-row" style="text-transform:capitalize"><span class="info-icon">📍</span>${{d.comuna?d.comuna+', ':''}}${{d.ubicacion||'Chile'}}</div>
${{d.direccion?`<div class="deal-info-row"><span class="info-icon">🏠</span>${{d.direccion}}</div>`:''}}
</div>
<div class="cta-row">${{linkHtml}}</div></div>
<div class="deal-footer">
<div class="validity">⏳ Vigencia: ${{d.valido_hasta?'hasta '+d.valido_hasta:'Sin fecha'}}</div>
<div class="disclaimer">⚠️ Siempre revisar condiciones especiales en el banco</div></div>`;
grid.appendChild(el)}})}}

function renderAll(){{render();if(currentView==='mapa'&&mapObj)renderMapMarkers()}}
function resetAll(){{
search.value='';bankMS.reset();regionMS.reset();comunaMS.reset();comunaG.style.display='none';
sortF.value='desc-desc';minD.value=0;minDV.textContent='0%';
document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
document.querySelector('#modeChips .chip[data-mode="all"]').classList.add('active');
dayAll.classList.add('active');daySels.forEach(s=>s.classList.remove('active'));renderAll()}}
document.getElementById('resetBtn').addEventListener('click',resetAll);
document.getElementById('resetBtn2').addEventListener('click',resetAll);

const initDia={init_dia},initBanco={init_banco},initQ={init_q};
if(initQ)search.value=initQ;
if(initBanco){{const c=[...bankMS.el.querySelectorAll('input[type=checkbox]')].find(c=>c.value===initBanco);
if(c){{c.checked=true;bankMS.sel.add(initBanco);bankMS._tags()}}}}
if(initDia){{dayAll.classList.remove('active');
daySels.forEach(s=>{{if(s.dataset.day===initDia)s.classList.add('active')}});}}
render();
search.addEventListener('input',renderAll);sortF.addEventListener('change',renderAll);
minD.addEventListener('input',renderAll);
daySelect.addEventListener('click',()=>setTimeout(renderAll,10));
document.getElementById('modeChips').addEventListener('click',()=>setTimeout(renderAll,10));

// ── MAP ──
const REGION_COORDS={{
'region metropolitana de santiago':[-33.4489,-70.6693],
'metropolitana':[-33.4489,-70.6693],'santiago':[-33.4489,-70.6693],
'valparaiso':[-33.0472,-71.6127],'valparaíso':[-33.0472,-71.6127],
'biobio':[-36.8201,-73.0444],'biobío':[-36.8201,-73.0444],'concepcion':[-36.8270,-73.0503],
'maule':[-35.4264,-71.6554],'araucania':[-38.7359,-72.5904],'araucanía':[-38.7359,-72.5904],
'antofagasta':[-23.6509,-70.3954],'coquimbo':[-29.9533,-71.3395],
'ohiggins':[-34.1654,-70.7399],"o'higgins":[-34.1654,-70.7399],
'los lagos':[-41.4693,-72.9424],'los rios':[-39.8142,-73.2459],'losríos':[-39.8142,-73.2459],
'atacama':[-27.3668,-70.3323],'tarapaca':[-20.2133,-69.9553],'tarapacá':[-20.2133,-69.9553],
'arica':[-18.4783,-70.3126],'magallanes':[-53.1548,-70.9113],
'aysen':[-45.5712,-72.0685],'aysén':[-45.5712,-72.0685],
'nuble':[-36.6096,-72.1034],'ñuble':[-36.6096,-72.1034],
'chile':[-33.4489,-70.6693]
}};
function getCoords(ubicacion,idx){{
if(!ubicacion)return null;
const key=ubicacion.toLowerCase().replace(/región\\s*(de(l)?\\s*)?/gi,'').trim();
for(const[k,v] of Object.entries(REGION_COORDS)){{
if(key.includes(k)||k.includes(key))return[v[0]+(Math.random()-.5)*.02,v[1]+(Math.random()-.5)*.02];
}}
return null;
}}
let mapObj=null,markers=null;
function initMap(){{
if(mapObj){{mapObj.invalidateSize();renderMapMarkers();return}}
mapObj=L.map('map').setView([-33.45,-70.65],6);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png',{{
attribution:'&copy; <a href="https://carto.com">CARTO</a>',maxZoom:18}}).addTo(mapObj);
markers=L.layerGroup().addTo(mapObj);
renderMapMarkers();
}}
function renderMapMarkers(){{
if(!markers)return;
markers.clearLayers();
// Uses same filters as card view
const qRaw=search.value.trim();
const qWords=qRaw?norm(qRaw).split(/\\s+/).filter(w=>w.length>0):[];
const banks=bankMS.vals(),regions=regionMS.vals(),comunas=comunaMS.vals();
const min=+minD.value,selDays=getSelectedDays(),mode=chipVal('modeChips','mode');
let count=0;
const withAddr=deals.filter(d=>d.direccion||d.ubicacion);
withAddr.forEach((d,i)=>{{
const txt=norm([d.restaurante,d.banco,d.descripcion||'',d.direccion||'',d.ubicacion||''].join(' '));
const mS=!qWords.length||qWords.every(w=>txt.includes(w));
const mB=!banks||banks.includes(d.banco);
const mR=!regions||regions.includes(d.ubicacion);
const mC=!comunas||comunas.includes(d.comuna);
const mD=d.descuento_valor>=min;
const mDay=!selDays||d.dias_validos.includes('todos')||selDays.some(sd=>d.dias_validos.includes(sd));
const mMode=mode==='all'||(mode==='presencial'&&d.presencial)||(mode==='online'&&d.online);
if(!mS||!mB||!mR||!mC||!mD||!mDay||!mMode)return;
const coords=getCoords(d.ubicacion,i);
if(!coords)return;
count++;
const color=BANK_COLORS[d.banco]||'#6b7280';
const icon=L.divIcon({{className:'',html:`<div style="background:${{color}};width:28px;height:28px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:800">${{d.descuento_valor||'?'}}%</div>`,
iconSize:[28,28],iconAnchor:[14,14]}});
const bankLogo=BANK_LOGOS[d.banco]||'';
const logoHtml=bankLogo?`<img src="${{bankLogo}}" style="height:14px">`:'';
const popup=`<div><div class="popup-title">${{d.restaurante}}</div>
<div class="popup-bank" style="background:${{color}}15;color:${{color}}">${{logoHtml}} ${{d.banco}}</div>
<div style="font-weight:700;color:var(--primary)">${{d.descuento_texto||d.descuento_valor+'%'}}</div>
${{d.descripcion?`<div class="popup-desc">${{d.descripcion.slice(0,80)}}</div>`:''}}
${{d.direccion?`<div style="font-size:12px">📍 ${{d.direccion}}</div>`:''}}
<div style="font-size:11px;color:#6b7280">📅 ${{d.dias_validos.join(', ')}}</div>
${{d.url_fuente?`<a class="popup-link" href="${{d.url_fuente}}" target="_blank">Ver detalle</a>`:''}}</div>`;
L.marker(coords,{{icon}}).bindPopup(popup,{{maxWidth:280}}).addTo(markers);
}});
document.getElementById('mapCount').textContent=count+' en mapa';
}}
</script>
</body></html>"""
    # Si llegó por ?key=xxx, setear cookie para sesión
    resp = HTMLResponse(content=page_html)
    if key and not ACCESO_PUBLICO:
        resp.set_cookie("acceso_key", key.strip().lower(), max_age=86400, httponly=True)
    return resp


# ============================================
# WHATSAPP WEBHOOK (Twilio Sandbox)
# ============================================

def _detectar_dia_hoy() -> str:
    """Retorna el día de la semana en español"""
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
    return dias[datetime.now().weekday()]


async def procesar_comando_whatsapp(texto: str) -> str:
    """Procesa mensajes de WhatsApp con IA (RAG) o comandos rápidos"""
    texto_original = texto.strip()
    texto = texto_original.lower()

    # ── Comandos rápidos (atajos) ──
    if texto in ['/', 'hola', 'hi', 'hello', 'help', 'menu', 'comandos', 'inicio']:
        dia_hoy = _detectar_dia_hoy()
        return f"""¡Hola! 👋🍽️ ¿De qué tienes ganas hoy?

Soy tu asistente de descuentos en restaurantes 🇨🇱
Pregúntame lo que quieras, por ejemplo:

🔥 "descuentos para hoy" (hoy es {dia_hoy})
🍣 "donde comer sushi con descuento"
💳 "mejores descuentos banco falabella"
💰 "restaurantes con 30% o más"

*Atajos:* /top · /stats"""

    if texto == '/top':
        rest_max = {}
        for b in beneficios_db:
            if b.restaurante not in rest_max or b.descuento_valor > rest_max[b.restaurante]:
                rest_max[b.restaurante] = b.descuento_valor
        top = sorted(rest_max.items(), key=lambda x: x[1], reverse=True)[:5]
        resultado = "*Top 5 Restaurantes*\n\n"
        for i, (rest, desc) in enumerate(top, 1):
            resultado += f"{i}. {rest} ({desc}% dto)\n"
        return resultado

    if texto == '/stats':
        total_bancos = len(set(b.banco for b in beneficios_db))
        total_rest = len(set(b.restaurante for b in beneficios_db))
        vals = [b.descuento_valor for b in beneficios_db if b.descuento_valor > 0]
        promedio = sum(vals) / len(vals) if vals else 0
        return f"""*Estadisticas*

Total Beneficios: {len(beneficios_db)}
Bancos: {total_bancos}
Restaurantes: {total_rest}
Descuento Promedio: {promedio:.1f}%
Descuento Maximo: {max(vals) if vals else 0}%"""

    # ── Consulta con IA (RAG) para todo lo demás ──
    if len(texto) < 2:
        return "Escribe tu pregunta sobre descuentos en restaurantes 🍽️"

    try:
        dia_hoy = _detectar_dia_hoy()
        DIAS_MAP = {
            'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miercoles',
            'miércoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sabado': 'sabado', 'sábado': 'sabado', 'domingo': 'domingo',
        }

        # ── Detectar si piden por día específico o "hoy" ──
        dia_filtro = None
        if 'hoy' in texto:
            dia_filtro = dia_hoy
        else:
            for palabra, dia_norm in DIAS_MAP.items():
                if palabra in texto:
                    dia_filtro = dia_norm
                    break

        # ── Detectar si piden por banco específico ──
        banco_filtro = None
        BANCOS_WA = {
            'falabella': 'Falabella', 'bci': 'BCI', 'itau': 'Itaú', 'itaú': 'Itaú',
            'scotiabank': 'Scotiabank', 'scotia': 'Scotiabank',
            'santander': 'Santander', 'security': 'Banco Security',
            'ripley': 'Banco Ripley', 'consorcio': 'Banco Consorcio',
            'bancoestado': 'BancoEstado', 'banco estado': 'BancoEstado',
            'entel': 'Entel',
            'tenpo': 'Tenpo',
            'lider bci': 'Lider BCI', 'liderbci': 'Lider BCI', 'lider': 'Lider BCI',
            'bice': 'Banco BICE',
            'mach': 'Mach',
        }
        if 'banco de chile' in texto or ('chile' in texto and 'banco' in texto):
            banco_filtro = 'Banco de Chile'
        else:
            for clave, nombre in BANCOS_WA.items():
                if clave in texto:
                    banco_filtro = nombre
                    break

        # ── Extraer término de búsqueda para el link ──
        q_busqueda = None
        palabras_skip = {'descuento', 'descuentos', 'beneficio', 'beneficios', 'para',
                         'con', 'que', 'hay', 'hoy', 'los', 'las', 'del', 'donde',
                         'comer', 'tiene', 'tiene', 'mejor', 'mejores', 'mas', 'más',
                         'banco', 'chile', 'falabella', 'de', 'en', 'el', 'la', 'un',
                         'una', 'quiero', 'dame', 'ver', 'todos', 'todas', 'puedo',
                         'bci', 'itau', 'itaú', 'scotiabank', 'scotia', 'santander',
                         'security', 'ripley', 'consorcio', 'bancoestado', 'estado',
                         'entel'}
        palabras_utiles = [p for p in texto.split() if p not in palabras_skip and len(p) > 2]
        if palabras_utiles:
            q_busqueda = " ".join(palabras_utiles[:3])

        # ── Armar contexto según tipo de consulta ──
        if dia_filtro or ('todos' in texto and ('descuento' in texto or 'beneficio' in texto)):
            # CONSULTA POR DÍA → Buscar beneficios del día, limitando contexto
            resultados = buscar_beneficios(dia=dia_filtro, banco=banco_filtro)
            if not resultados and dia_filtro:
                resultados = buscar_beneficios(dia=dia_filtro)

            # Si hay keyword específico (ej: "sushi", "pizza"), filtrar
            keyword = None
            if palabras_utiles:
                # Excluir días de la búsqueda keyword
                dias_palabras = set(DIAS_MAP.keys()) | {'hoy', 'mañana'}
                keyword_words = [w for w in palabras_utiles if w not in dias_palabras]
                if keyword_words:
                    keyword = " ".join(keyword_words[:2])

            if keyword:
                # Filtrar por keyword en restaurante o descripcion
                kw_lower = keyword.lower()
                filtrados = [b for b in resultados
                             if kw_lower in b.restaurante.lower()
                             or kw_lower in b.descripcion.lower()]
                if filtrados:
                    resultados = filtrados

            # Agrupar por banco
            por_banco = {}
            for b in resultados:
                if b.banco not in por_banco:
                    por_banco[b.banco] = []
                por_banco[b.banco].append(b)

            # Limitar contexto: top 2 por banco + conteo total
            TOP_PER_BANK = 2
            contexto_partes = []
            for banco, beneficios in sorted(por_banco.items()):
                beneficios_sorted = sorted(beneficios, key=lambda x: x.descuento_valor, reverse=True)
                contexto_partes.append(f"\n=== {banco} ({len(beneficios)} descuentos) ===")
                for b in beneficios_sorted[:TOP_PER_BANK]:
                    contexto_partes.append(
                        f"- {b.restaurante}: {b.descuento_texto} | {b.ubicacion}"
                    )
                resto = len(beneficios) - TOP_PER_BANK
                if resto > 0:
                    contexto_partes.append(f"  ...y {resto} más")
            contexto = "\n".join(contexto_partes)
            total_encontrados = len(resultados)
        else:
            # CONSULTA GENERAL → Búsqueda semántica en Pinecone
            pregunta_enriquecida = texto_original
            if 'hoy' in texto:
                pregunta_enriquecida += f" (hoy es {dia_hoy})"

            resultados_semanticos = buscar_semantico(pregunta_enriquecida, top_k=15)

            if resultados_semanticos:
                # Agrupar por banco
                por_banco = {}
                for r in resultados_semanticos:
                    banco = r.get('banco', 'Otro')
                    if banco not in por_banco:
                        por_banco[banco] = []
                    por_banco[banco].append(r)

                contexto_partes = []
                for banco, items in sorted(por_banco.items()):
                    contexto_partes.append(f"\n=== {banco} ===")
                    for r in items:
                        contexto_partes.append(
                            f"- {r['restaurante']}: {r['descuento_texto']} | "
                            f"Días: {r.get('dias_validos', 'todos')} | {r.get('ubicacion', '')}"
                        )
                contexto = "\n".join(contexto_partes)
            else:
                resultados = buscar_beneficios(restaurante=texto)
                if not resultados:
                    resultados = beneficios_db[:20]
                contexto = "\n".join([
                    f"- {b.restaurante}: {b.descuento_texto} ({b.banco}) | "
                    f"Días: {', '.join(b.dias_validos)} | {b.ubicacion}"
                    for b in resultados[:20]
                ])
            total_encontrados = len(resultados_semanticos) if resultados_semanticos else len(resultados)

        # ── Generar link a tabla completa ──
        BASE_URL = "https://api-beneficios-chile.onrender.com/ver"
        params = []
        if dia_filtro:
            params.append(f"dia={quote_plus(dia_filtro)}")
        if banco_filtro:
            params.append(f"banco={quote_plus(banco_filtro)}")
        if not dia_filtro and not banco_filtro and q_busqueda:
            params.append(f"q={quote_plus(q_busqueda)}")
        link_tabla = BASE_URL + ("?" + "&".join(params) if params else "")

        # ── Consultar OpenAI ──
        openai_client = get_openai_client()
        if not openai_client:
            return "⚠️ Servicio de IA no disponible. Usa /top o /stats."

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente de WhatsApp experto en descuentos bancarios "
                        "en restaurantes de Chile. Hoy es " + dia_hoy + ".\n\n"
                        "REGLAS IMPORTANTES:\n"
                        "- Responde SOLO con los datos proporcionados, no inventes\n"
                        "- Agrupa por banco:\n"
                        "  *🏦 Banco* (X dctos hoy)\n"
                        "  • Restaurante - descuento\n"
                        "- Muestra los 1-2 mejores por banco (mayor %) que ya vienen en los datos\n"
                        "- Indica cuántos descuentos tiene cada banco en total\n"
                        "- Formato WhatsApp: *negrita* para bancos\n"
                        "- ⚠️ MÁXIMO 900 caracteres (LÍMITE ESTRICTO)\n"
                        "- Sé MUY conciso\n"
                        "- NO incluyas link, se agrega automáticamente\n"
                        "- Español chileno casual con emojis"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Total de beneficios encontrados: {total_encontrados}\n\n"
                        f"Beneficios agrupados por banco:\n{contexto}\n\n"
                        f"Pregunta del usuario: {texto_original}"
                    )
                }
            ],
            temperature=0.3,
            max_tokens=350,
        )
        respuesta = response.choices[0].message.content

        # Agregar link a la tabla completa
        sufijo = f"\n\n📋 *Ver tabla completa con links:*\n{link_tabla}"
        max_texto = 1500 - len(sufijo)
        return respuesta[:max_texto] + sufijo

    except Exception as e:
        print(f"  Error RAG WhatsApp: {e}")
        # Fallback: búsqueda simple agrupada por banco
        resultados = buscar_beneficios(restaurante=texto)
        if resultados:
            return _formatear_wa(resultados, max_items=10)
        return "Hubo un error procesando tu consulta. Intenta de nuevo 🙏"


def _formatear_wa(beneficios, max_items=3):
    """Formatea beneficios para WhatsApp"""
    if not beneficios:
        return "No encontre beneficios. Intenta con otro nombre."
    texto = f"*{len(beneficios)} resultados:*\n\n"
    for i, b in enumerate(beneficios[:max_items], 1):
        dias = ", ".join(b.dias_validos) if b.dias_validos else "Consultar"
        texto += f"{i}. *{b.restaurante}*\n"
        texto += f"   {b.banco} - {b.descuento_texto}\n"
        texto += f"   Dias: {dias}\n"
        if b.ubicacion:
            texto += f"   {b.ubicacion}\n"
        texto += "\n"
    if len(beneficios) > max_items:
        texto += f"... y {len(beneficios) - max_items} mas."
    return texto[:1500]


@app.post("/webhook")
async def webhook_whatsapp(From: str = Form(""), Body: str = Form("")):
    """Webhook para Twilio WhatsApp Sandbox"""
    from twilio.twiml.messaging_response import MessagingResponse

    usuario = From.replace("whatsapp:", "")
    print(f"  WhatsApp de {usuario}: {Body}")

    respuesta = await procesar_comando_whatsapp(Body)

    resp = MessagingResponse()
    resp.message(respuesta)

    return Response(content=str(resp), media_type="application/xml")


@app.get("/webhook")
async def webhook_verify():
    return {"status": "ok", "webhook": "activo"}


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"\n🚀 Iniciando API en http://localhost:{port}")
    print(f"📖 Documentación en http://localhost:{port}/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=port)

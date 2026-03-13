"""
API REST - BENEFICIOS BANCARIOS
================================
FastAPI + OpenAI RAG
"""

from fastapi import FastAPI, HTTPException, Query, Form, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import quote_plus
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime
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
# PÁGINA WEB - TABLA COMPLETA DE RESULTADOS
# ============================================

@app.get("/ver", response_class=HTMLResponse)
async def ver_resultados(
    dia: Optional[str] = Query(None, description="Día de la semana"),
    banco: Optional[str] = Query(None, description="Nombre del banco"),
    q: Optional[str] = Query(None, description="Búsqueda libre"),
):
    """Genera página HTML con cards de beneficios, filtros interactivos e imágenes"""
    import html as html_lib

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
        }
        for b in all_data
    ], ensure_ascii=False)

    bancos_list = sorted(set(b.banco for b in all_data))
    regiones_list = sorted(set(b.ubicacion for b in all_data if b.ubicacion))
    banco_options = "".join(f'<option value="{html_lib.escape(b)}">{html_lib.escape(b)}</option>' for b in bancos_list)
    region_options = "".join(f'<option value="{html_lib.escape(r)}">{html_lib.escape(r)}</option>' for r in regiones_list)

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
/* Tab navigation */
.tabs{{display:flex;gap:4px;margin-bottom:16px;background:var(--panel2);padding:4px;border-radius:12px;width:fit-content}}
.tab-btn{{border:0;background:transparent;color:var(--muted);padding:10px 20px;border-radius:10px;
font-weight:700;font-size:14px;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:6px}}
.tab-btn.active{{background:var(--panel);color:var(--primary);box-shadow:var(--shadow)}}
.tab-btn:hover:not(.active){{color:var(--text)}}
.tab-content{{display:none}}.tab-content.active{{display:block}}
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
.range-row{{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center}}
input[type=range]{{accent-color:var(--primary)}}
.btns{{display:flex;gap:8px;margin-top:10px}}
button{{border:0;border-radius:10px;padding:10px 14px;font-weight:700;cursor:pointer;font-size:13px}}
.btn-primary{{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;flex:1}}
.btn-secondary{{background:var(--panel2);color:var(--text);border:1px solid var(--line)}}
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
/* Map */
#map{{height:calc(100vh - 200px);min-height:500px;border-radius:var(--radius);border:1px solid var(--line)}}
.map-layout{{display:grid;grid-template-columns:280px 1fr;gap:16px;align-items:start}}
.map-stats{{padding:14px;margin-bottom:10px;text-align:center}}
.map-stats .val{{font-size:22px;font-weight:800;color:var(--primary)}}
.leaflet-popup-content{{font-family:Inter,sans-serif;font-size:13px;line-height:1.5}}
.popup-title{{font-weight:700;font-size:15px;margin-bottom:4px}}
.popup-bank{{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;margin-bottom:4px}}
.popup-bank img{{height:14px}}
.popup-desc{{color:var(--muted);margin:4px 0}}
.popup-link{{display:inline-block;background:var(--primary);color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-weight:600;font-size:12px;margin-top:4px}}
@media(max-width:980px){{.hero,.layout,.grid,.map-layout{{grid-template-columns:1fr}}.stats-grid{{grid-template-columns:1fr}}
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
<div class="tabs">
<button class="tab-btn active" data-tab="descuentos">🍽️ Descuentos</button>
<button class="tab-btn" data-tab="mapa">📍 Mapa</button>
</div>
<div id="tab-descuentos" class="tab-content active">
<section class="layout">
<aside class="card filters">
<h2>Filtros</h2>
<div class="group"><label>Buscar</label>
<input id="search" class="input" type="text" placeholder="Ej: sushi, pizza..."></div>
<div class="group"><label>Banco</label>
<select id="bankFilter"><option value="all">Todos los bancos</option>{banco_options}</select></div>
<div class="group"><label>Día</label>
<div class="chips" id="dayChips">
<button class="chip active" data-day="all">Todos</button>
<button class="chip" data-day="lunes">Lun</button>
<button class="chip" data-day="martes">Mar</button>
<button class="chip" data-day="miercoles">Mié</button>
<button class="chip" data-day="jueves">Jue</button>
<button class="chip" data-day="viernes">Vie</button>
<button class="chip" data-day="sabado">Sáb</button>
<button class="chip" data-day="domingo">Dom</button>
</div></div>
<div class="group"><label>Zona</label>
<select id="regionFilter"><option value="all">Todas</option>{region_options}</select></div>
<div class="group"><label>Ordenar</label>
<select id="sortFilter">
<option value="desc-desc">Mayor descuento</option>
<option value="desc-asc">Menor descuento</option>
<option value="name">Nombre A-Z</option>
<option value="bank">Banco A-Z</option>
</select></div>
<div class="group"><label>Descuento mínimo</label>
<div class="range-row"><input id="minDisc" type="range" min="0" max="50" step="5" value="0">
<strong id="minDiscVal">0%</strong></div></div>
<div class="group"><label>Modalidad</label>
<div class="chips" id="modeChips">
<button class="chip active" data-mode="all">Todas</button>
<button class="chip" data-mode="presencial">🏪 Presencial</button>
<button class="chip" data-mode="online">💻 Online</button>
</div></div>
<div class="btns">
<button class="btn-primary" id="applyBtn">Aplicar</button>
<button class="btn-secondary" id="resetBtn">Limpiar</button>
</div>
</aside>
<main class="card results">
<div class="toolbar">
<h2>Resultados</h2>
<span class="pill" id="count">0</span>
</div>
<div class="grid" id="grid"></div>
<div class="empty" id="empty">No hay descuentos con esos filtros 🤷</div>
</main>
</section>
</div>
<div id="tab-mapa" class="tab-content">
<section class="map-layout">
<aside class="card filters">
<h2>Mapa de descuentos</h2>
<div class="card map-stats">
<div class="val" id="mapCount">0</div>
<div class="lbl">Restaurantes en el mapa</div>
</div>
<div class="group"><label>Buscar</label>
<input id="mapSearch" class="input" type="text" placeholder="Ej: sushi, pizza..."></div>
<div class="group"><label>Banco</label>
<select id="mapBankFilter"><option value="all">Todos los bancos</option>{banco_options}</select></div>
<div class="group"><label>Zona</label>
<select id="mapRegionFilter"><option value="all">Todas</option>{region_options}</select></div>
<p style="color:var(--muted);font-size:12px;margin-top:10px">📍 Solo se muestran restaurantes con dirección conocida. Los marcadores se ubican por zona geográfica.</p>
</aside>
<main>
<div id="map"></div>
</main>
</section>
</div>
<div class="footer">Actualizado: {timestamp_ultimo_scrape or 'N/A'} · Beneficios Bancarios Chile 🇨🇱</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const deals={deals_json};

// ── Bank logos ──
const BANK_LOGOS={{
'Banco de Chile':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Banco_de_Chile_Logotipo.svg/200px-Banco_de_Chile_Logotipo.svg.png',
'Banco Falabella':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Logotipo_Banco_Falabella.svg/200px-Logotipo_Banco_Falabella.svg.png'
}};
function bankBadgeHtml(banco){{
const logo=BANK_LOGOS[banco];
if(logo)return `<img src="${{logo}}" alt="${{banco}}" onerror="this.style.display='none';this.nextElementSibling.style.fontSize='11px'"><span>${{banco}}</span>`;
return `<span style="font-size:11px;font-weight:700">${{banco}}</span>`;
}}

// ── Tabs ──
document.querySelectorAll('.tab-btn').forEach(btn=>{{btn.addEventListener('click',()=>{{
document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
btn.classList.add('active');
document.getElementById('tab-'+btn.dataset.tab).classList.add('active');
if(btn.dataset.tab==='mapa')initMap();
}})}});

// ── Card grid ──
const grid=document.getElementById('grid'),empty=document.getElementById('empty'),
countEl=document.getElementById('count'),search=document.getElementById('search'),
bankF=document.getElementById('bankFilter'),regionF=document.getElementById('regionFilter'),
sortF=document.getElementById('sortFilter'),minD=document.getElementById('minDisc'),
minDV=document.getElementById('minDiscVal');

function chipVal(id,attr){{const a=document.querySelector('#'+id+' .chip.active');return a?a.dataset[attr]:'all'}}
function initChips(id,attr){{document.getElementById(id).addEventListener('click',e=>{{
const c=e.target.closest('.chip');if(!c)return;
document.querySelectorAll('#'+id+' .chip').forEach(x=>x.classList.remove('active'));c.classList.add('active')}})}}
initChips('dayChips','day');initChips('modeChips','mode');
minD.addEventListener('input',()=>{{minDV.textContent=minD.value+'%'}});

function render(){{
const q=search.value.trim().toLowerCase(),bank=bankF.value,region=regionF.value,
sort=sortF.value,min=+minD.value,day=chipVal('dayChips','day'),mode=chipVal('modeChips','mode');
let f=deals.filter(d=>{{
const mS=!q||[d.restaurante,d.banco,d.descripcion,d.ubicacion,d.direccion].join(' ').toLowerCase().includes(q);
const mB=bank==='all'||d.banco===bank;
const mR=region==='all'||d.ubicacion===region;
const mD=d.descuento_valor>=min;
const mDay=day==='all'||d.dias_validos.includes(day)||d.dias_validos.includes('todos');
const mMode=mode==='all'||(mode==='presencial'&&d.presencial)||(mode==='online'&&d.online);
return mS&&mB&&mR&&mD&&mDay&&mMode}});
f.sort((a,b)=>{{switch(sort){{case'desc-asc':return a.descuento_valor-b.descuento_valor;
case'name':return a.restaurante.localeCompare(b.restaurante);
case'bank':return a.banco.localeCompare(b.banco);
default:return b.descuento_valor-a.descuento_valor}}}});
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
<div class="deal-info-row"><span class="info-icon">📍</span>${{(d.ubicacion||'Chile').replace(/\\b\\w/g,c=>c.toUpperCase())}}</div>
${{d.direccion?`<div class="deal-info-row"><span class="info-icon">🏠</span>${{d.direccion}}</div>`:''}}
</div>
<div class="cta-row">${{linkHtml}}</div></div>
<div class="deal-footer">
<div class="validity">⏳ Vigencia: ${{d.valido_hasta?'hasta '+d.valido_hasta:'Sin fecha'}}</div>
<div class="disclaimer">⚠️ Siempre revisar condiciones especiales en el banco</div></div>`;
grid.appendChild(el)}})}}

document.getElementById('applyBtn').addEventListener('click',render);
document.getElementById('resetBtn').addEventListener('click',()=>{{
search.value='';bankF.value='all';regionF.value='all';sortF.value='desc-desc';
minD.value=0;minDV.textContent='0%';
document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
document.querySelector('#dayChips .chip[data-day="all"]').classList.add('active');
document.querySelector('#modeChips .chip[data-mode="all"]').classList.add('active');render()}});

const initDia={init_dia},initBanco={init_banco},initQ={init_q};
if(initQ)search.value=initQ;
if(initBanco)bankF.value=initBanco;
if(initDia){{document.querySelectorAll('#dayChips .chip').forEach(c=>{{c.classList.remove('active');
if(c.dataset.day===initDia)c.classList.add('active')}})}}
render();
search.addEventListener('input',render);bankF.addEventListener('change',render);
regionF.addEventListener('change',render);sortF.addEventListener('change',render);
minD.addEventListener('input',render);
document.getElementById('dayChips').addEventListener('click',()=>setTimeout(render,10));
document.getElementById('modeChips').addEventListener('click',()=>setTimeout(render,10));

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
const key=ubicacion.toLowerCase().replace(/región\s*(de(l)?\s*)?/gi,'').trim();
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
document.getElementById('mapSearch').addEventListener('input',renderMapMarkers);
document.getElementById('mapBankFilter').addEventListener('change',renderMapMarkers);
document.getElementById('mapRegionFilter').addEventListener('change',renderMapMarkers);
}}
function renderMapMarkers(){{
if(!markers)return;
markers.clearLayers();
const q=document.getElementById('mapSearch').value.trim().toLowerCase();
const bank=document.getElementById('mapBankFilter').value;
const region=document.getElementById('mapRegionFilter').value;
let count=0;
const withAddr=deals.filter(d=>d.direccion||d.ubicacion);
withAddr.forEach((d,i)=>{{
const mS=!q||[d.restaurante,d.banco,d.descripcion,d.direccion].join(' ').toLowerCase().includes(q);
const mB=bank==='all'||d.banco===bank;
const mR=region==='all'||d.ubicacion===region;
if(!mS||!mB||!mR)return;
const coords=getCoords(d.ubicacion,i);
if(!coords)return;
count++;
const color=d.banco.includes('Chile')?'#003DA5':'#00B140';
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
document.getElementById('mapCount').textContent=count;
}}
</script>
</body></html>"""
    return HTMLResponse(content=page_html)


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
        if 'falabella' in texto:
            banco_filtro = 'Falabella'
        elif 'banco de chile' in texto or ('chile' in texto and 'banco' in texto):
            banco_filtro = 'Banco de Chile'

        # ── Extraer término de búsqueda para el link ──
        q_busqueda = None
        palabras_skip = {'descuento', 'descuentos', 'beneficio', 'beneficios', 'para',
                         'con', 'que', 'hay', 'hoy', 'los', 'las', 'del', 'donde',
                         'comer', 'tiene', 'tiene', 'mejor', 'mejores', 'mas', 'más',
                         'banco', 'chile', 'falabella', 'de', 'en', 'el', 'la', 'un',
                         'una', 'quiero', 'dame', 'ver', 'todos', 'todas', 'puedo'}
        palabras_utiles = [p for p in texto.split() if p not in palabras_skip and len(p) > 2]
        if palabras_utiles:
            q_busqueda = " ".join(palabras_utiles[:3])

        # ── Armar contexto según tipo de consulta ──
        if dia_filtro or ('todos' in texto and ('descuento' in texto or 'beneficio' in texto)):
            # CONSULTA POR DÍA → Buscar TODOS de la base de datos, agrupados por banco
            resultados = buscar_beneficios(dia=dia_filtro, banco=banco_filtro)
            if not resultados and dia_filtro:
                resultados = buscar_beneficios(dia=dia_filtro)

            # Agrupar por banco
            por_banco = {}
            for b in resultados:
                if b.banco not in por_banco:
                    por_banco[b.banco] = []
                por_banco[b.banco].append(b)

            contexto_partes = []
            for banco, beneficios in sorted(por_banco.items()):
                contexto_partes.append(f"\n=== {banco} ({len(beneficios)} descuentos) ===")
                for b in sorted(beneficios, key=lambda x: x.descuento_valor, reverse=True):
                    contexto_partes.append(
                        f"- {b.restaurante}: {b.descuento_texto} | "
                        f"Días: {', '.join(b.dias_validos)} | {b.ubicacion}"
                    )
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
                        "- Agrupa por banco con esta jerarquía:\n"
                        "  *🏦 Banco* (X dctos)\n"
                        "  • Restaurante - descuento\n"
                        "- Muestra los TOP 3-5 mejores descuentos por banco (los de mayor %)\n"
                        "- Si hay más, indica cuántos más hay por banco\n"
                        "- Formato WhatsApp: *negrita* para bancos\n"
                        "- ⚠️ MÁXIMO 1100 caracteres en total (LÍMITE ESTRICTO)\n"
                        "- Sé MUY conciso, no uses ubicaciones ni días si no preguntan\n"
                        "- NO incluyas link, se agrega automáticamente al final\n"
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

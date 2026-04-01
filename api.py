"""
API REST - BENEFICIOS BANCARIOS
================================
FastAPI + OpenAI RAG
"""

from fastapi import FastAPI, HTTPException, Query, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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
from scrapers import Beneficio, OrquestadorScrapers, DescuentoBencina, EstacionBencina

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

class DescuentoBencinaResponse(BaseModel):
    id: str
    cadena: str
    banco: str
    tarjeta: str
    descuento_por_litro: int
    descuento_texto: str
    dias_validos: List[str]
    condicion: str = ""
    tope_litros: int = 0
    tope_monto: int = 0
    vigencia_mes: str = ""
    valido_hasta: str = ""
    restricciones_texto: str = ""
    activo: bool = True

    class Config:
        from_attributes = True

class EstacionBencinaResponse(BaseModel):
    id: str
    nombre: str
    cadena: str
    direccion: str = ""
    comuna: str = ""
    region: str = ""
    latitud: float = 0.0
    longitud: float = 0.0
    precio_93: int = 0
    precio_95: int = 0
    precio_97: int = 0
    precio_diesel: int = 0
    precio_kerosene: int = 0
    precio_fecha: str = ""

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

# Mount static files for logos
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

beneficios_db: List[Beneficio] = []
bencinas_descuentos: List[DescuentoBencina] = []
bencinas_estaciones: List[EstacionBencina] = []
bencinas_precios_todas: List[EstacionBencina] = []
bencinas_meta: dict = {}
timestamp_ultimo_scrape = None

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def inicializar_datos():
    global beneficios_db, bencinas_descuentos, bencinas_estaciones, bencinas_precios_todas, bencinas_meta, timestamp_ultimo_scrape

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

    # Cargar datos de bencinas
    bencinas_path = os.path.join(script_dir, "bencinas.json")
    if os.path.exists(bencinas_path):
        print(f"⛽ Cargando bencinas desde {bencinas_path}...")
        with open(bencinas_path, 'r', encoding='utf-8') as f:
            bdata = json.load(f)
            bencinas_descuentos = [DescuentoBencina(**d) for d in bdata.get("descuentos", [])]
            bencinas_estaciones = [EstacionBencina(**e) for e in bdata.get("estaciones", [])]
            bencinas_precios_todas = [EstacionBencina(**e) for e in bdata.get("precios_todas", [])]
            bencinas_meta = bdata.get("meta", {})
            print(f"✅ Bencinas: {len(bencinas_descuentos)} descuentos, {len(bencinas_estaciones)} estaciones, {len(bencinas_precios_todas)} precios")
    else:
        print("⚠️ bencinas.json no encontrado. Ejecuta scraping de bencinas.")


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
# ENDPOINTS BENCINAS
# ============================================

@app.get("/bencinas")
async def listar_bencinas(
    cadena: Optional[str] = None,
    banco: Optional[str] = None,
    dia: Optional[str] = None,
):
    """Lista descuentos de bencina con filtros opcionales"""
    resultados = bencinas_descuentos

    if cadena:
        cadena_lower = cadena.lower()
        resultados = [d for d in resultados if cadena_lower in d.cadena.lower()]

    if banco:
        banco_lower = banco.lower()
        resultados = [d for d in resultados if banco_lower in d.banco.lower()]

    if dia:
        dia_lower = dia.lower()
        resultados = [d for d in resultados if dia_lower in [x.lower() for x in d.dias_validos]]

    return {
        "total": len(resultados),
        "vigencia_mes": bencinas_meta.get("vigencia_mes", ""),
        "descuentos": [d.to_dict() for d in resultados],
    }


@app.get("/bencinas/estaciones")
async def listar_estaciones(
    cadena: Optional[str] = None,
    comuna: Optional[str] = None,
):
    """Lista estaciones de servicio con coordenadas"""
    resultados = bencinas_estaciones

    if cadena:
        cadena_lower = cadena.lower()
        resultados = [e for e in resultados if cadena_lower in e.cadena.lower()]

    if comuna:
        comuna_lower = comuna.lower()
        resultados = [e for e in resultados if comuna_lower in e.comuna.lower()]

    return {
        "total": len(resultados),
        "estaciones": [e.to_dict() for e in resultados],
    }


@app.get("/bencinas/mapa")
async def bencinas_mapa():
    """Datos combinados: estaciones + descuentos para el mapa"""
    # Agrupar descuentos por cadena
    descuentos_por_cadena = {}
    for d in bencinas_descuentos:
        if d.cadena not in descuentos_por_cadena:
            descuentos_por_cadena[d.cadena] = []
        descuentos_por_cadena[d.cadena].append(d.to_dict())

    # Combinar estaciones con sus descuentos
    estaciones_con_descuentos = []
    for e in bencinas_estaciones:
        est_dict = e.to_dict()
        est_dict["descuentos"] = descuentos_por_cadena.get(e.cadena, [])
        estaciones_con_descuentos.append(est_dict)

    return {
        "total_estaciones": len(estaciones_con_descuentos),
        "total_descuentos": len(bencinas_descuentos),
        "vigencia_mes": bencinas_meta.get("vigencia_mes", ""),
        "estaciones": estaciones_con_descuentos,
    }


@app.get("/bencinas/precios")
async def precios_bencina(
    combustible: str = "93",
    comuna: Optional[str] = None,
    region: Optional[str] = None,
    cadena: Optional[str] = None,
    orden: str = "precio_asc",
    limite: int = 20,
):
    """Busca las estaciones con mejores precios de combustible.

    Fuente: Bencinas en Línea - Comisión Nacional de Energía.
    Los precios son de exclusiva responsabilidad de las estaciones informantes.
    """
    # Mapear combustible a campo
    campo_map = {
        '93': 'precio_93', '95': 'precio_95', '97': 'precio_97',
        'diesel': 'precio_diesel', 'kerosene': 'precio_kerosene',
    }
    campo = campo_map.get(combustible.lower(), 'precio_93')

    # Filtrar estaciones con precio > 0
    resultados = [e for e in bencinas_precios_todas if getattr(e, campo, 0) > 0]

    if comuna:
        comuna_lower = comuna.lower()
        resultados = [e for e in resultados if comuna_lower in e.comuna.lower()]

    if region:
        region_lower = region.lower()
        resultados = [e for e in resultados if region_lower in e.region.lower()]

    if cadena:
        cadena_lower = cadena.lower()
        resultados = [e for e in resultados if cadena_lower in e.cadena.lower()]

    # Ordenar
    reverse = orden == "precio_desc"
    resultados.sort(key=lambda e: getattr(e, campo, 0), reverse=reverse)

    # Limitar
    resultados = resultados[:limite]

    return {
        "total": len(resultados),
        "combustible": combustible,
        "fecha_precios": bencinas_meta.get("fecha_precios", ""),
        "disclaimer": "Los precios publicados son de exclusiva responsabilidad de las estaciones de servicio informantes. Fuente: Bencinas en Línea - Comisión Nacional de Energía.",
        "estaciones": [e.to_dict() for e in resultados],
    }


@app.get("/bencinas/precios/mejores")
async def mejores_precios(
    combustible: str = "93",
    region: Optional[str] = None,
    limite: int = 10,
):
    """Top estaciones más baratas por tipo de combustible.

    Fuente: Bencinas en Línea - Comisión Nacional de Energía.
    """
    campo_map = {
        '93': 'precio_93', '95': 'precio_95', '97': 'precio_97',
        'diesel': 'precio_diesel', 'kerosene': 'precio_kerosene',
    }
    campo = campo_map.get(combustible.lower(), 'precio_93')

    resultados = [e for e in bencinas_precios_todas if getattr(e, campo, 0) > 0]

    if region:
        region_lower = region.lower()
        resultados = [e for e in resultados if region_lower in e.region.lower()]

    resultados.sort(key=lambda e: getattr(e, campo, 0))
    resultados = resultados[:limite]

    return {
        "total": len(resultados),
        "combustible": combustible,
        "region": region or "Todo Chile",
        "fecha_precios": bencinas_meta.get("fecha_precios", ""),
        "disclaimer": "Los precios publicados son de exclusiva responsabilidad de las estaciones de servicio informantes. Fuente: Bencinas en Línea - Comisión Nacional de Energía.",
        "estaciones": [e.to_dict() for e in resultados],
    }


@app.get("/bencinas/precios/resumen")
async def resumen_precios():
    """Resumen de precios promedio por cadena y combustible"""
    cadenas_stats = {}
    for e in bencinas_precios_todas:
        if e.cadena not in cadenas_stats:
            cadenas_stats[e.cadena] = {
                'count': 0, '93': [], '95': [], '97': [], 'diesel': []
            }
        cadenas_stats[e.cadena]['count'] += 1
        if e.precio_93 > 0: cadenas_stats[e.cadena]['93'].append(e.precio_93)
        if e.precio_95 > 0: cadenas_stats[e.cadena]['95'].append(e.precio_95)
        if e.precio_97 > 0: cadenas_stats[e.cadena]['97'].append(e.precio_97)
        if e.precio_diesel > 0: cadenas_stats[e.cadena]['diesel'].append(e.precio_diesel)

    resumen = []
    for cadena, stats in sorted(cadenas_stats.items(), key=lambda x: -x[1]['count']):
        entry = {'cadena': cadena, 'estaciones': stats['count']}
        for tipo in ('93', '95', '97', 'diesel'):
            precios = stats[tipo]
            if precios:
                entry[f'precio_{tipo}_min'] = min(precios)
                entry[f'precio_{tipo}_max'] = max(precios)
                entry[f'precio_{tipo}_promedio'] = round(sum(precios) / len(precios))
        resumen.append(entry)

    return {
        "total_estaciones": len(bencinas_precios_todas),
        "fecha_precios": bencinas_meta.get("fecha_precios", ""),
        "disclaimer": "Fuente: Bencinas en Línea - Comisión Nacional de Energía.",
        "resumen_por_cadena": resumen,
    }


@app.post("/scrape/bencinas")
async def ejecutar_scrape_bencinas():
    """Ejecuta scraping de descuentos de bencina y precios"""
    global bencinas_descuentos, bencinas_estaciones, bencinas_precios_todas, bencinas_meta

    orquestador = OrquestadorScrapers()
    desc, est = orquestador.scrapear_bencinas()
    orquestador.guardar_bencinas_json(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bencinas.json")
    )

    bencinas_descuentos = desc
    bencinas_estaciones = est
    bencinas_precios_todas = orquestador.precios_todas
    bencinas_meta = {
        "fecha_scrape": datetime.now().isoformat(),
        "fecha_precios": datetime.now().isoformat(),
        "vigencia_mes": datetime.now().strftime("%Y-%m"),
    }

    return {
        "status": "Scraping de bencinas completado",
        "total_descuentos": len(desc),
        "total_estaciones": len(est),
        "total_con_precios": len(bencinas_precios_todas),
        "vigencia_mes": bencinas_meta["vigencia_mes"],
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
ACCESO_PUBLICO = True


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
    banco: Optional[List[str]] = Query(None, description="Nombre del banco (puede ser múltiple)"),
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
    init_bancos = json.dumps(banco, ensure_ascii=False) if banco else 'null'
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
/* Geolocation */
.geo-bar{{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}}
.geo-btn{{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:10px;
border:1px solid var(--line);background:var(--panel2);color:var(--text);font-size:13px;
font-weight:600;cursor:pointer;transition:all .2s}}
.geo-btn:hover{{border-color:var(--primary);background:#f5f3ff;color:var(--primary)}}
.geo-btn.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;border-color:transparent}}
.geo-btn.loading{{opacity:.7;cursor:wait}}
.geo-status{{font-size:12px;color:var(--muted)}}
@media(max-width:980px){{.hero,.layout,.grid{{grid-template-columns:1fr}}.stats-grid{{grid-template-columns:1fr}}
.filters{{position:static}}.deal-img{{height:140px}}#map{{height:60vh}}
.day-circle{{width:24px;height:24px;font-size:10px}}.day-bar{{gap:4px;padding:6px 8px}}}}
</style>
</head>
<body>
<div class="container">
<nav style="display:flex;gap:4px;margin-bottom:20px;background:var(--panel);padding:4px;border-radius:14px;box-shadow:var(--shadow);width:fit-content">
<a href="/ver" style="text-decoration:none;padding:10px 24px;border-radius:10px;font-weight:700;font-size:14px;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;box-shadow:0 2px 8px rgba(79,70,229,.3)">🍽️ Restaurantes</a>
<a href="/ver/bencinas" style="text-decoration:none;padding:10px 24px;border-radius:10px;font-weight:700;font-size:14px;color:#6b7280;transition:all .2s">⛽ Bencina</a>
</nav>
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
<div id="summaryBar" class="summary-bar"></div>
<div id="view-tarjetas" class="view-content active">
<div class="toolbar">
<h2>Resultados</h2>
<span class="pill" id="count">0</span>
</div>
<div class="grid" id="grid"></div>
<div class="empty" id="empty">No hay descuentos con esos filtros 🤷</div>
</div>
<div id="view-mapa" class="view-content">
<div class="toolbar">
<h2>Mapa</h2>
<span class="pill" id="mapCount">0 en mapa</span>
</div>
<div class="geo-bar">
<button class="geo-btn" id="geoBtn" onclick="toggleGeolocation()">📍 Mi ubicación</button>
<span class="geo-status" id="geoStatus"></span>
</div>
<div id="map"></div>
<p style="color:var(--muted);font-size:11px;margin-top:8px;text-align:center">📍 Ubicaciones aproximadas por región · Activa tu GPS para verte en el mapa</p>
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
'Banco Consorcio':'/static/logos/consorcio.svg',
'BancoEstado':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Logo_BancoEstado.svg/200px-Logo_BancoEstado.svg.png',
'Banco Security':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Logo_empresa_banco_security.png/200px-Logo_empresa_banco_security.png',
'Banco Ripley':'https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Logo_Ripley_banco_2.png/200px-Logo_Ripley_banco_2.png',
'Entel':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/EntelChile_Logo.svg/200px-EntelChile_Logo.svg.png',
'Tenpo':'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Logotipo_Tenpo.svg/200px-Logotipo_Tenpo.svg.png',
'Lider BCI':'https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Lider_2025.svg/200px-Lider_2025.svg.png',
'Banco BICE':'/static/logos/bice.svg',
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
this._tags();renderAll()}})}});
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
if(c)c.checked=false;this._tags();renderAll()}})}})}}
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
if(cb){{cb.checked=!cb.checked;if(cb.checked)bankMS.sel.add(banco);else bankMS.sel.delete(banco);bankMS._tags();renderAll()}}
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

const initDia={init_dia},initBancos={init_bancos},initQ={init_q};
if(initQ)search.value=initQ;
if(initBancos&&initBancos.length){{initBancos.forEach(b=>{{
const c=[...bankMS.el.querySelectorAll('input[type=checkbox]')].find(c=>c.value===b);
if(c){{c.checked=true;bankMS.sel.add(b)}}
}});bankMS._tags()}}
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

// ── Geolocation ──
let geoMarker=null,geoActive=false;
function toggleGeolocation(){{
const btn=document.getElementById('geoBtn'),status=document.getElementById('geoStatus');
if(geoActive){{
  // Desactivar
  geoActive=false;btn.classList.remove('active');
  if(geoMarker){{mapObj.removeLayer(geoMarker);geoMarker=null}}
  status.textContent='';return;
}}
if(!navigator.geolocation){{status.textContent='Tu navegador no soporta geolocalización';return}}
btn.classList.add('loading');status.textContent='Obteniendo ubicación...';
navigator.geolocation.getCurrentPosition(
  pos=>{{
    geoActive=true;btn.classList.remove('loading');btn.classList.add('active');
    const lat=pos.coords.latitude,lng=pos.coords.longitude;
    status.textContent=`📍 ${{lat.toFixed(4)}}, ${{lng.toFixed(4)}}`;
    if(!mapObj)initMap();
    if(geoMarker)mapObj.removeLayer(geoMarker);
    // Blue pulsing marker for user location
    const geoIcon=L.divIcon({{className:'',html:`<div style="position:relative"><div style="width:18px;height:18px;background:#4285F4;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 8px rgba(66,133,244,.5)"></div><div style="position:absolute;top:-6px;left:-6px;width:30px;height:30px;border-radius:50%;background:rgba(66,133,244,.15);animation:geoPulse 2s infinite"></div></div>`,
    iconSize:[18,18],iconAnchor:[9,9]}});
    geoMarker=L.marker([lat,lng],{{icon:geoIcon,zIndex:9999}}).addTo(mapObj)
      .bindPopup('<div style="text-align:center"><strong>📍 Estás aquí</strong><br><span style="color:#6b7280;font-size:12px">Tu ubicación actual</span></div>');
    mapObj.setView([lat,lng],13);
    geoMarker.openPopup();
  }},
  err=>{{
    btn.classList.remove('loading');
    const msgs={{1:'Permiso denegado — activa la ubicación en tu navegador',2:'Ubicación no disponible',3:'Tiempo agotado'}};
    status.textContent='⚠️ '+(msgs[err.code]||'Error desconocido');
  }},
  {{enableHighAccuracy:true,timeout:10000,maximumAge:60000}}
);
}}
// CSS animation for geo pulse
(function(){{const s=document.createElement('style');s.textContent='@keyframes geoPulse{{0%{{transform:scale(1);opacity:.6}}100%{{transform:scale(2.5);opacity:0}}}}';document.head.appendChild(s)}})();
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


# ── Estado conversacional por usuario ──
# {phone: {"mode": "restaurantes"|"bencinas", "step": "ask_mode"|"ask_banco"|"ask_dia"|"ask_comida", ...}}
user_flow = {}

BANCOS_ALIAS = {
    'banco de chile': 'Banco de Chile', 'chile': 'Banco de Chile',
    'falabella': 'Banco Falabella', 'banco falabella': 'Banco Falabella',
    'bci': 'BCI',
    'itau': 'Banco Itaú', 'itaú': 'Banco Itaú', 'banco itau': 'Banco Itaú',
    'scotiabank': 'Scotiabank', 'scotia': 'Scotiabank',
    'santander': 'Santander',
    'security': 'Banco Security', 'banco security': 'Banco Security',
    'ripley': 'Banco Ripley', 'banco ripley': 'Banco Ripley',
    'consorcio': 'Banco Consorcio', 'banco consorcio': 'Banco Consorcio',
    'bancoestado': 'BancoEstado', 'banco estado': 'BancoEstado', 'estado': 'BancoEstado',
    'entel': 'Entel',
    'tenpo': 'Tenpo',
    'lider': 'Lider BCI', 'lider bci': 'Lider BCI',
    'bice': 'Banco BICE', 'banco bice': 'Banco BICE',
    'mach': 'Mach',
}

DIAS_ALIAS = {
    'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miercoles', 'miércoles': 'miercoles',
    'jueves': 'jueves', 'viernes': 'viernes', 'sabado': 'sabado', 'sábado': 'sabado',
    'domingo': 'domingo', 'hoy': _detectar_dia_hoy(),
}


def _parse_bancos(texto: str) -> list:
    """Parsea bancos del texto del usuario"""
    texto = texto.lower().strip()
    if texto in ['todos', 'todo', 'all', 'cualquiera', 'da igual', 'no importa']:
        return []  # sin filtro = todos
    # Intentar match largo primero, luego corto
    encontrados = []
    for alias, nombre in sorted(BANCOS_ALIAS.items(), key=lambda x: -len(x[0])):
        if alias in texto and nombre not in encontrados:
            encontrados.append(nombre)
            texto = texto.replace(alias, '', 1)
    return encontrados


def _parse_dia(texto: str) -> str:
    """Parsea día del texto del usuario"""
    texto = texto.lower().strip()
    if texto in ['todos', 'todo', 'all', 'cualquiera', 'da igual', 'no importa']:
        return ''  # sin filtro
    if texto == 'hoy':
        return _detectar_dia_hoy()
    for alias, dia in DIAS_ALIAS.items():
        if alias in texto:
            return dia
    return ''


def _generar_resultado_flow(bancos: list, dia: str, comida: str) -> str:
    """Genera resultado filtrado + link para el flujo conversacional"""
    resultados = list(beneficios_db)

    # Filtrar por banco(s)
    if bancos:
        resultados = [b for b in resultados if b.banco in bancos]

    # Filtrar por día
    if dia:
        resultados = [b for b in resultados
                      if dia in b.dias_validos or 'todos' in b.dias_validos]

    # Filtrar por comida (keyword en restaurante o descripcion)
    if comida:
        kw = comida.lower()
        filtrados = [b for b in resultados
                     if kw in b.restaurante.lower()
                     or kw in getattr(b, 'descripcion', '').lower()]
        if filtrados:
            resultados = filtrados

    # Ordenar por mayor descuento
    resultados.sort(key=lambda b: b.descuento_valor, reverse=True)

    if not resultados:
        return "No encontré descuentos con esos filtros 🤷\n\nEscribe *hola* para buscar de nuevo."

    # Agrupar por banco (top 3 por banco, max 5 bancos)
    por_banco = {}
    for b in resultados:
        if b.banco not in por_banco:
            por_banco[b.banco] = []
        por_banco[b.banco].append(b)

    texto = f"🍽️ *{len(resultados)} descuentos encontrados*\n"
    if bancos:
        texto += f"💳 {', '.join(bancos)}\n"
    if dia:
        texto += f"📅 {dia.capitalize()}\n"
    if comida:
        texto += f"🍕 {comida}\n"
    texto += "\n"

    bancos_mostrados = 0
    for banco, items in sorted(por_banco.items(), key=lambda x: -max(i.descuento_valor for i in x[1])):
        if bancos_mostrados >= 5:
            break
        texto += f"*🏦 {banco}* ({len(items)} dctos)\n"
        for b in items[:3]:
            texto += f"  • {b.restaurante} — {b.descuento_texto}\n"
        if len(items) > 3:
            texto += f"  _...y {len(items)-3} más_\n"
        texto += "\n"
        bancos_mostrados += 1

    # Link con TODOS los filtros
    BASE_URL = "https://api-beneficios-chile.onrender.com/ver"
    params = []
    if dia:
        params.append(f"dia={quote_plus(dia)}")
    if bancos:
        for b in bancos:
            params.append(f"banco={quote_plus(b)}")
    link = BASE_URL + ("?" + "&".join(params) if params else "")

    texto += f"📋 *Ver todos con filtros:*\n{link}"
    return texto[:1500]


def _generar_resultado_bencinas(dia: str) -> str:
    """Genera resultado de descuentos de bencina filtrado por día"""
    resultados = list(bencinas_descuentos)

    if dia:
        resultados = [d for d in resultados
                      if dia in d.dias_validos or 'todos' in d.dias_validos]

    resultados.sort(key=lambda d: d.descuento_por_litro, reverse=True)

    if not resultados:
        return "No encontré descuentos de bencina para ese día 🤷\n\nEscribe *hola* para buscar de nuevo."

    # Agrupar por cadena
    por_cadena = {}
    for d in resultados:
        if d.cadena not in por_cadena:
            por_cadena[d.cadena] = []
        por_cadena[d.cadena].append(d)

    dia_txt = dia.capitalize() if dia else "Todos los días"
    texto = f"⛽ *{len(resultados)} descuentos de bencina*\n📅 {dia_txt}\n\n"

    for cadena, items in sorted(por_cadena.items(), key=lambda x: -max(i.descuento_por_litro for i in x[1])):
        texto += f"*⛽ {cadena}*\n"
        for d in items[:5]:
            texto += f"  • {d.banco} ({d.tarjeta}) — *${d.descuento_por_litro}/L*\n"
            if d.tope_monto:
                texto += f"    _Tope ${d.tope_monto:,}/mes_\n"
        if len(items) > 5:
            texto += f"  _...y {len(items)-5} más_\n"
        texto += "\n"

    BASE_URL = "https://api-beneficios-chile.onrender.com/ver/bencinas"
    texto += f"📋 *Ver todos con mapa:*\n{BASE_URL}"
    return texto[:1500]


async def procesar_comando_whatsapp(texto: str, usuario: str = "") -> str:
    """Procesa mensajes de WhatsApp con IA (RAG) o comandos rápidos"""
    texto_original = texto.strip()
    texto = texto_original.lower()

    # ── Flujo conversacional activo? ──
    if usuario and usuario in user_flow:
        state = user_flow[usuario]

        # PASO 1: ¿Restaurantes o Bencinas?
        if state["step"] == "ask_mode":
            if texto in ['2', 'bencina', 'bencinas', 'combustible', 'gasolina', 'fuel', 'gas']:
                state["mode"] = "bencinas"
                state["step"] = "ask_dia_bencina"
                dia_hoy = _detectar_dia_hoy()
                return f"""⛽ *Bencinas*

📅 *¿Qué día?*
_1._ Hoy ({dia_hoy})
_2._ Lunes
_3._ Martes
_4._ Miércoles
_5._ Jueves
_6._ Viernes
_7._ Sábado
_8._ Domingo
_9._ Todos"""
            else:
                # 1, restaurantes, o cualquier otra cosa -> restaurantes
                state["mode"] = "restaurantes"
                state["step"] = "ask_dia_rest"
                dia_hoy = _detectar_dia_hoy()
                return f"""🍽️ *Restaurantes*

📅 *¿Qué día?*
_1._ Hoy ({dia_hoy})
_2._ Lunes
_3._ Martes
_4._ Miércoles
_5._ Jueves
_6._ Viernes
_7._ Sábado
_8._ Domingo
_9._ Todos"""

        # ── BENCINAS: día → resultado ──
        if state["step"] == "ask_dia_bencina":
            dia_map = {'1': _detectar_dia_hoy(), '2': 'lunes', '3': 'martes', '4': 'miercoles',
                       '5': 'jueves', '6': 'viernes', '7': 'sabado', '8': 'domingo', '9': ''}
            dia = dia_map.get(texto.strip(), _parse_dia(texto))
            resultado = _generar_resultado_bencinas(dia)
            del user_flow[usuario]
            return resultado

        # ── RESTAURANTES: día → banco(s) → resultado ──
        if state["step"] == "ask_dia_rest":
            dia_map = {'1': _detectar_dia_hoy(), '2': 'lunes', '3': 'martes', '4': 'miercoles',
                       '5': 'jueves', '6': 'viernes', '7': 'sabado', '8': 'domingo', '9': ''}
            state["dia"] = dia_map.get(texto.strip(), _parse_dia(texto))
            dia_txt = state["dia"].capitalize() if state["dia"] else "Todos"
            state["step"] = "ask_banco"
            bancos = sorted(set(b.banco for b in beneficios_db))
            lista = "\n".join(f"_{i+1}._ {b}" for i, b in enumerate(bancos))
            return f"""✅ *{dia_txt}*

💳 *¿Qué banco(s)?*
{lista}
_{len(bancos)+1}._ Todos

_Ej: 1 o varios: 1,2,4,5_"""

        if state["step"] == "ask_banco":
            bancos = sorted(set(b.banco for b in beneficios_db))
            # Intentar por número(s) separados por coma
            selected = []
            parts = [p.strip() for p in texto.replace(' ', ',').split(',') if p.strip()]
            for p in parts:
                try:
                    num = int(p)
                    if 1 <= num <= len(bancos):
                        selected.append(bancos[num - 1])
                    elif num == len(bancos) + 1:
                        selected = []  # todos
                        break
                except ValueError:
                    parsed = _parse_bancos(p)
                    selected.extend(parsed)
            state["bancos"] = selected
            resultado = _generar_resultado_flow(state["bancos"], state["dia"], "")
            del user_flow[usuario]
            return resultado

    # ── Cualquier mensaje sin flujo activo → iniciar flujo ──
    if usuario:
        user_flow[usuario] = {"step": "ask_mode", "mode": "", "bancos": [], "dia": "", "comida": ""}
    return f"""👋 *¡Hola! ¿Cómo estás?*
En qué quieres ahorrar hoy? 💰

*1.* 🍽️ Restaurantes ({len(beneficios_db)} descuentos)
*2.* ⛽ Bencinas ({len(bencinas_descuentos)} descuentos)"""


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


# ============================================
# PAGINA WEB - BENCINAS CON MAPA
# ============================================

@app.get("/ver/bencinas", response_class=HTMLResponse)
async def ver_bencinas():
    """Pagina de descuentos de bencina con mapa de estaciones - estilo visual restaurantes"""
    import html as html_lib

    # Serializar datos para JS
    bencina_deals_json = json.dumps([d.to_dict() for d in bencinas_descuentos], ensure_ascii=False)
    estaciones_json = json.dumps([e.to_dict() for e in bencinas_estaciones], ensure_ascii=False)
    # Precios: todas las estaciones con precios (para comparador)
    precios_json = json.dumps([e.to_dict() for e in bencinas_precios_todas if e.precio_93 > 0 or e.precio_97 > 0 or e.precio_diesel > 0], ensure_ascii=False)
    # Regiones y comunas únicas para filtros de precios
    regiones_set = sorted(set(e.region for e in bencinas_precios_todas if e.region))
    comunas_set = sorted(set(e.comuna for e in bencinas_precios_todas if e.comuna))
    regiones_json = json.dumps(regiones_set, ensure_ascii=False)
    comunas_map_json = json.dumps({r: sorted(set(e.comuna for e in bencinas_precios_todas if e.region == r and e.comuna)) for r in regiones_set}, ensure_ascii=False)
    total_precios = len([e for e in bencinas_precios_todas if e.precio_93 > 0 or e.precio_97 > 0 or e.precio_diesel > 0])
    fecha_precios = bencinas_meta.get("fecha_precios", "")

    # Stats
    total_desc = len(bencinas_descuentos)
    total_est = len(bencinas_estaciones)
    cadenas = sorted(set(d.cadena for d in bencinas_descuentos))
    bancos_list = sorted(set(d.banco for d in bencinas_descuentos))
    max_dcto = max((d.descuento_por_litro for d in bencinas_descuentos), default=0)
    vigencia = bencinas_meta.get("vigencia_mes", datetime.now().strftime("%Y-%m"))

    # Mes en espanol
    meses_es = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
    try:
        y, m = vigencia.split('-')
        mes_texto = f"{meses_es[int(m)]} {y}"
    except Exception:
        mes_texto = vigencia

    bancos_json_list = json.dumps(bancos_list, ensure_ascii=False)
    cadenas_json_list = json.dumps(cadenas, ensure_ascii=False)

    page = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Descuentos Bencina Chile - {mes_texto}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
<style>
:root{{--bg:#f8f7f4;--panel:#fff;--panel2:#f3f1ed;--text:#1a1a2e;--muted:#6b7280;--line:#e5e2da;
--primary:#ea580c;--primary2:#dc2626;--ok:#16a34a;--warn:#ea580c;--radius:16px;
--shadow:0 4px 20px rgba(0,0,0,.06);}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text);}}
.container{{width:min(1260px,calc(100% - 24px));margin:0 auto;padding:20px 0 60px}}
.hero{{display:grid;grid-template-columns:1.4fr .8fr;gap:16px;margin-bottom:20px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}}
.hero-main{{padding:28px;background:linear-gradient(135deg,#fff7ed,#fef2f2)}}
.eyebrow{{display:inline-flex;align-items:center;gap:6px;background:rgba(234,88,12,.08);
border:1px solid rgba(234,88,12,.15);color:var(--primary);padding:6px 12px;border-radius:999px;font-size:12px;font-weight:600}}
h1{{margin:12px 0 6px;font-size:clamp(24px,4vw,38px);line-height:1.1;font-weight:800;
background:linear-gradient(135deg,var(--primary),var(--primary2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{color:var(--muted);font-size:14px;line-height:1.6}}
.stats-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:16px}}
.stat{{background:var(--panel2);border-radius:14px;padding:16px;text-align:center}}
.stat .val{{font-size:28px;font-weight:800;color:var(--primary)}}
.stat .lbl{{color:var(--muted);font-size:12px;margin-top:2px}}
/* View toggle */
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
.chip:hover{{border-color:var(--primary);background:#fff7ed}}
.chip.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));border-color:transparent;color:#fff}}
/* Day circle multi-select */
.day-select{{display:flex;align-items:center;gap:2px;flex-wrap:nowrap}}
.day-sel{{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-size:9px;font-weight:700;border:1.5px solid var(--line);color:var(--muted);background:var(--panel2);
cursor:pointer;transition:all .15s;user-select:none;flex-shrink:0}}
.day-sel:hover{{border-color:var(--primary);color:var(--primary)}}
.day-sel.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));border-color:transparent;color:#fff}}
.day-sel-all{{width:auto;padding:0 8px;border-radius:999px;font-size:9px;letter-spacing:.3px;flex-shrink:0}}
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
.deal-img{{height:200px;position:relative;overflow:hidden}}
.deal-img img.hero-bg{{width:100%;height:100%;object-fit:cover;filter:brightness(.85)}}
.deal-img .hero-overlay{{position:absolute;inset:0;background:linear-gradient(180deg,transparent 0%,transparent 40%,rgba(0,0,0,.45) 100%)}}
.deal-img .chain-logo-hero{{position:absolute;top:12px;left:12px;background:rgba(255,255,255,.95);padding:5px 8px;border-radius:10px;display:flex;align-items:center;gap:4px;box-shadow:0 2px 8px rgba(0,0,0,.15)}}
.deal-img .chain-logo-hero img{{height:36px;width:auto}}
.deal-img .badge{{position:absolute;top:14px;right:14px;background:linear-gradient(135deg,#00c853,#009624);
color:#fff;padding:8px 16px;border-radius:12px;font-weight:900;font-size:20px;letter-spacing:.5px;box-shadow:0 3px 12px rgba(0,0,0,.25)}}
.deal-header{{background:var(--panel);padding:10px 14px;border-bottom:1px solid var(--line)}}
.deal-header h3{{font-size:17px;font-weight:800;margin:0;color:var(--text)}}
.deal-header .hero-sub{{display:flex;align-items:center;gap:8px;margin-top:5px;flex-wrap:wrap}}
.deal-header .hero-sub img{{height:18px;border-radius:3px}}
.deal-header .hero-sub .sub-tag{{font-size:11px;padding:3px 8px;border-radius:6px;font-weight:600;display:flex;align-items:center;gap:4px}}
.deal-header .hero-sub .sub-tag.bank{{background:#f0f4ff;color:#1a56db}}
.deal-header .hero-sub .sub-tag.mode{{background:#fff7ed;color:#ea580c}}
.deal-header .hero-sub .sub-tag.chain{{background:#f0fdf4;color:#166534}}
.deal-body{{padding:12px 14px;flex:1;display:flex;flex-direction:column;gap:8px}}
.deal-title{{font-size:16px;font-weight:700;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.deal-desc{{color:var(--muted);font-size:13px;line-height:1.4}}
.day-bar{{display:flex;align-items:center;gap:5px;border:1px solid var(--line);border-radius:10px;padding:6px 8px;background:#fafafa}}
.day-circles{{display:flex;gap:3px;flex:1}}
.day-circle{{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-size:10px;font-weight:700;border:2px solid #e2e2e2;color:#ccc;background:#fff;transition:all .2s}}
.day-circle.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));border-color:transparent;color:#fff}}
.mode-badge{{font-size:11px;font-weight:600;padding:4px 8px;border-radius:6px;white-space:nowrap}}
.mode-badge.presencial{{background:#fff7ed;color:#ea580c}}
.deal-info{{display:flex;flex-direction:column;gap:4px}}
.deal-info-row{{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted)}}
.deal-info-row .info-icon{{width:15px;flex-shrink:0}}
.cta-row{{display:flex;justify-content:center;padding-top:8px}}
.link{{color:#fff;text-decoration:none;background:linear-gradient(135deg,var(--primary),var(--primary2));
padding:10px 24px;border-radius:12px;font-weight:700;font-size:14px;transition:all .2s}}
.link:hover{{opacity:.85;transform:translateY(-1px)}}
.deal-footer{{background:#fafaf9;border-top:1px solid var(--line);padding:8px 14px;display:flex;flex-direction:column;gap:2px}}
.deal-footer .validity{{color:var(--muted);font-size:10px}}
.deal-footer .disclaimer{{color:#bbb;font-size:9px;font-style:italic}}
.empty{{display:none;text-align:center;padding:40px;color:var(--muted);border:2px dashed var(--line);border-radius:var(--radius)}}
.no-img{{width:100%;height:100%;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center;font-size:48px}}
.deal-visuals{{display:flex;align-items:center;justify-content:space-between;padding:10px 18px;border-top:1px solid var(--line);background:#fafaf9;gap:8px}}
.deal-chain-logo{{height:32px;width:auto;object-fit:contain}}
.tarjeta-row{{display:flex;align-items:center;gap:12px;padding:8px 10px;border:1px solid var(--line);border-radius:10px;background:#fff;margin:3px 0}}
.tarjeta-row img{{height:30px;border-radius:4px;filter:drop-shadow(0 1px 3px rgba(0,0,0,.12))}}
.tarjeta-row .tarjeta-dcto{{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;padding:5px 12px;border-radius:8px;font-weight:800;font-size:15px;white-space:nowrap}}
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
padding:8px 6px 6px;border-radius:10px;background:var(--panel2);border:1px solid var(--line);
min-width:72px;max-width:100px;cursor:pointer;transition:all .15s;user-select:none}}
.summary-pill:hover{{border-color:var(--primary);background:#fff7ed}}
.summary-pill.active{{background:linear-gradient(135deg,rgba(234,88,12,.1),rgba(220,38,38,.1));
border-color:var(--primary);box-shadow:0 0 0 2px rgba(234,88,12,.2)}}
.summary-pill .sp-logo{{height:22px;display:flex;align-items:center;justify-content:center;flex:1}}
.summary-pill .sp-logo img{{height:100%;width:auto;max-width:64px;object-fit:contain}}
.summary-pill .sp-nologo{{font-size:8px;font-weight:700;color:var(--muted);
text-align:center;line-height:1.2;max-width:88px;overflow:hidden;
height:22px;display:flex;align-items:center;justify-content:center;word-break:break-word;white-space:normal}}
.summary-pill .sp-ct{{font-weight:800;font-size:14px;color:var(--primary);margin-top:4px}}
/* Map */
#bencina-map{{height:calc(100vh - 260px);min-height:450px;border-radius:var(--radius);border:1px solid var(--line)}}
.leaflet-popup-content{{font-family:Inter,sans-serif;font-size:13px;line-height:1.5}}
.popup-title{{font-weight:700;font-size:15px;margin-bottom:4px}}
.popup-bank{{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;margin-bottom:4px}}
.popup-bank img{{height:14px}}
.popup-desc{{color:var(--muted);margin:4px 0}}
.popup-link{{display:inline-block;background:var(--primary);color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-weight:600;font-size:12px;margin-top:4px}}
/* Geolocation */
.geo-bar{{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}}
.geo-btn{{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:10px;
border:1px solid var(--line);background:var(--panel2);color:var(--text);font-size:13px;
font-weight:600;cursor:pointer;transition:all .2s}}
.geo-btn:hover{{border-color:var(--primary);background:#fff7ed;color:var(--primary)}}
.geo-btn.active{{background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;border-color:transparent}}
.geo-btn.loading{{opacity:.7;cursor:wait}}
.geo-status{{font-size:12px;color:var(--muted)}}
.precios-filters{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}}
.precios-filter-row{{display:flex;gap:12px;flex-wrap:wrap;align-items:end}}
.pf-group{{flex:1;min-width:140px}}
.pf-group label{{display:block;font-size:11px;font-weight:600;color:var(--muted);margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px}}
.pf-select{{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px;background:#fff;color:var(--text);cursor:pointer}}
.pf-select:focus{{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(234,88,12,.1)}}
.fuel-chips{{display:flex;gap:6px;flex-wrap:wrap}}
.fuel-chip{{padding:6px 14px;border:2px solid var(--line);border-radius:20px;background:#fff;font-size:13px;font-weight:600;cursor:pointer;transition:all .2s;color:var(--text)}}
.fuel-chip:hover{{border-color:var(--primary);color:var(--primary)}}
.fuel-chip.active{{background:linear-gradient(135deg,#ea580c,#dc2626);color:#fff;border-color:transparent;box-shadow:0 2px 8px rgba(234,88,12,.3)}}
.precios-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}}
.ps-card{{background:linear-gradient(135deg,#f9fafb,#fff);border:1px solid var(--line);border-radius:10px;padding:10px 14px;text-align:center}}
.ps-label{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}}
.ps-value{{font-size:20px;font-weight:800;margin-top:2px}}
.ps-min{{color:#16a34a}}.ps-max{{color:#dc2626}}.ps-avg{{color:#ea580c}}.ps-count{{color:#6366f1}}
.precios-map-container{{margin-bottom:16px}}
.precios-list{{display:flex;flex-direction:column;gap:6px;max-height:500px;overflow-y:auto;padding-right:4px}}
.precio-row{{display:flex;align-items:center;gap:12px;padding:10px 14px;background:#fff;border:1px solid var(--line);border-radius:10px;transition:all .15s}}
.precio-row:hover{{border-color:var(--primary);box-shadow:0 2px 8px rgba(234,88,12,.08)}}
.precio-rank{{font-size:14px;font-weight:800;color:var(--muted);min-width:28px;text-align:center}}
.precio-rank.top3{{color:#ea580c}}
.precio-chain-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.precio-info{{flex:1;min-width:0}}
.precio-name{{font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.precio-addr{{font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.precio-value{{font-size:18px;font-weight:800;text-align:right;min-width:80px}}
.precio-value.cheapest{{color:#16a34a}}.precio-value.expensive{{color:#dc2626}}.precio-value.normal{{color:var(--text)}}
.precio-diff{{font-size:10px;color:var(--muted);text-align:right}}
@media(max-width:980px){{.hero,.layout,.grid{{grid-template-columns:1fr}}.stats-grid{{grid-template-columns:1fr}}
.filters{{position:static}}.deal-img{{height:140px}}#bencina-map{{height:60vh}}
.day-circle{{width:24px;height:24px;font-size:10px}}.day-bar{{gap:4px;padding:6px 8px}}
.precios-filter-row{{flex-direction:column}}.precios-stats{{grid-template-columns:repeat(2,1fr)}}}}
.deal-visuals{{display:flex;align-items:center;justify-content:space-between;padding:6px 14px;border-top:1px solid var(--line);background:#fafaf9;gap:6px;min-height:40px}}
.deal-chain-logo{{height:28px;width:auto;object-fit:contain}}
.deal-tarjeta{{height:38px;width:auto;max-width:120px;object-fit:contain;border-radius:4px;filter:drop-shadow(0 1px 3px rgba(0,0,0,.15))}}
.deal-chain-logo{{height:30px;width:auto;max-width:80px;object-fit:contain}}
.deal-tarjeta-placeholder{{font-size:10px;color:var(--muted);display:flex;align-items:center;gap:4px}}
</style>
</head>
<body>
<div class="container">
<nav style="display:flex;gap:4px;margin-bottom:20px;background:var(--panel);padding:4px;border-radius:14px;box-shadow:var(--shadow);width:fit-content">
<a href="/ver" style="text-decoration:none;padding:10px 24px;border-radius:10px;font-weight:700;font-size:14px;color:#6b7280;transition:all .2s">🍽️ Restaurantes</a>
<a href="/ver/bencinas" style="text-decoration:none;padding:10px 24px;border-radius:10px;font-weight:700;font-size:14px;background:linear-gradient(135deg,#ea580c,#dc2626);color:#fff;box-shadow:0 2px 8px rgba(234,88,12,.3)">⛽ Bencina</a>
</nav>
<section class="hero">
<div class="card hero-main">
<div class="eyebrow">⛽ Descuentos Bencina</div>
<h1>Descuentos en Combustible de Chile</h1>
<p class="sub">Todos los beneficios en estaciones Copec, Shell y Aramco, actualizados.
Filtra por cadena, banco, dia y descuento minimo.</p>
<p class="sub" style="margin-top:8px;font-weight:600;color:var(--primary)">Vigencia: {mes_texto}</p>
</div>
<div class="card stats-grid">
<div class="stat"><div class="val">{total_desc}</div><div class="lbl">Descuentos activos</div></div>
<div class="stat"><div class="val">${max_dcto}/L</div><div class="lbl">Mejor descuento</div></div>
<div class="stat"><div class="val">{total_est}</div><div class="lbl">Estaciones RM</div></div>
</div>
</section>
<section class="layout">
<aside class="card filters">
<h2>Filtros</h2>
<button class="btn-secondary" id="resetBtn" style="width:100%;margin-bottom:10px;font-size:12px;padding:7px 0">Limpiar filtros</button>
<div class="group"><label>Buscar</label>
<input id="search" class="input" type="text" placeholder="Ej: Copec, BCI..."></div>
<div class="group"><label>Banco / App</label>
<div class="multi-select" id="bankMS"></div></div>
<div class="group"><label>Dia</label>
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
<div class="group"><label>Cadena</label>
<div class="chips" id="cadenaChips">
<button class="chip active" data-cadena="all">Todas</button>
<button class="chip" data-cadena="Copec">Copec</button>
<button class="chip" data-cadena="Shell">Shell</button>
<button class="chip" data-cadena="Aramco">Aramco</button>
</div></div>
<div class="group"><label>Ordenar</label>
<select id="sortFilter">
<option value="desc-desc">Mayor descuento</option>
<option value="desc-asc">Menor descuento</option>
<option value="name">Cadena A-Z</option>
<option value="bank">Banco A-Z</option>
</select></div>
<button class="btn-secondary" id="resetBtn2" style="width:100%;margin-top:10px;font-size:12px;padding:7px 0">Limpiar filtros</button>
</aside>
<main class="card results">
<div class="view-toggle">
<button class="view-btn active" data-view="tarjetas">⛽ Tarjetas</button>
<button class="view-btn" data-view="mapa">📍 Mapa</button>
<button class="view-btn" data-view="precios">⛽ PU Bencina</button>
</div>
<div id="summaryBar" class="summary-bar"></div>
<div id="view-tarjetas" class="view-content active">
<div class="toolbar">
<h2>Resultados</h2>
<span class="pill" id="count">0</span>
</div>
<div class="grid" id="grid"></div>
<div class="empty" id="empty">No hay descuentos con esos filtros</div>
</div>
<div id="view-mapa" class="view-content">
<div class="toolbar">
<h2>Mapa</h2>
<span class="pill" id="mapCount">0 estaciones</span>
</div>
<div class="geo-bar">
<button class="geo-btn" id="geoBtn" onclick="toggleGeolocation()">📍 Mi ubicacion</button>
<span class="geo-status" id="geoStatus"></span>
</div>
<div id="bencina-map"></div>
<p style="color:var(--muted);font-size:11px;margin-top:8px;text-align:center">📍 Estaciones reales en la RM · Activa tu GPS para verte en el mapa</p>
</div>
<div id="view-precios" class="view-content">
<div class="toolbar">
<h2>Comparador de Precios</h2>
<span class="pill" id="preciosCount">0 estaciones</span>
</div>
<div class="precios-filters">
<div class="precios-filter-row">
<div class="pf-group">
<label>Combustible</label>
<div class="fuel-chips" id="fuelChips">
<button class="fuel-chip active" data-fuel="93">93</button>
<button class="fuel-chip" data-fuel="95">95</button>
<button class="fuel-chip" data-fuel="97">97</button>
<button class="fuel-chip" data-fuel="diesel">Diesel</button>
<button class="fuel-chip" data-fuel="kerosene">Kerosene</button>
</div>
</div>
<div class="pf-group">
<label>Region</label>
<select id="precioRegion" class="pf-select">
<option value="">Todas las regiones</option>
</select>
</div>
<div class="pf-group">
<label>Comuna</label>
<select id="precioComuna" class="pf-select">
<option value="">Todas las comunas</option>
</select>
</div>
<div class="pf-group">
<label>Cadena</label>
<select id="precioCadena" class="pf-select">
<option value="">Todas</option>
<option value="Copec">Copec</option>
<option value="Shell">Shell</option>
<option value="Aramco">Aramco</option>
<option value="otra">Otras</option>
</select>
</div>
</div>
<div class="precios-stats" id="preciosStats"></div>
</div>
<div class="precios-map-container">
<div id="precios-map" style="height:350px;border-radius:10px;border:1px solid var(--line)"></div>
</div>
<div class="precios-list" id="preciosList"></div>
<p style="color:var(--muted);font-size:10px;margin-top:12px;text-align:center;font-style:italic">
Fuente: Bencinas en Linea - Comision Nacional de Energia. Los precios publicados son de exclusiva responsabilidad de las estaciones de servicio informantes.
</p>
</div>
</main>
</section>
<div class="footer">
Vigencia: {mes_texto} · Beneficios Bancarios Chile
<br><span style="font-size:10px;color:#aaa">Precios: Bencinas en Línea - Comisión Nacional de Energía. Los precios publicados son de exclusiva responsabilidad de las estaciones de servicio informantes.</span>
</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
const deals={bencina_deals_json};
const stations={estaciones_json};
const allPrices={precios_json};
const REGIONES={regiones_json};
const COMUNAS_MAP={comunas_map_json};

const DIAS_SEMANA=['domingo','lunes','martes','miercoles','jueves','viernes','sabado'];
const HOY=DIAS_SEMANA[new Date().getDay()];

// ── Chain images ──
const CHAIN_IMAGES={{
'Copec':'/static/logos/copec_station.jpg',
'Shell':'/static/logos/shell_station.jpg',
'Aramco':'/static/logos/aramco_station.jpg'
}};
const CHAIN_COLORS={{Copec:'#dc2626',Shell:'#FFD500',Aramco:'#003B71'}};
const CHAIN_LOGOS={{
'Copec':'/static/logos/copec.svg',
'Shell':'/static/logos/shell.svg',
'Aramco':'/static/logos/aramco_logo.png'
}};
const TARJETA_IMAGES={{
'Visa Crédito Singular':'https://www.scotiabank.cl/content/dam/scotiabank/cl/images/tarjetas/visa-singular.png',
'Visa Crédito Platinum':'https://www.scotiabank.cl/content/dam/scotiabank/cl/images/tarjetas/visa-platinum.png',
'Visa Crédito Tradicional':'https://www.scotiabank.cl/content/dam/scotiabank/cl/images/tarjetas/visa-clasica.png',
'Black':'https://www.scotiabank.cl/content/dam/scotiabank/cl/images/tarjetas/cencosud-black.png',
'Crédito Consorcio':'https://www.bancoconsorcio.cl/assets/img/tarjetas/credito.png',
'Crédito Ripley Gold':'https://www.bancoripley.cl/assets/img/tarjetas/gold.png',
'Crédito Ripley Silver':'https://www.bancoripley.cl/assets/img/tarjetas/silver.png',
'Crédito Ripley Plus':'https://www.bancoripley.cl/assets/img/tarjetas/plus.png',
'Crédito BCI':'https://www.bci.cl/assets/img/tarjetas/bci-visa.png',
'Crédito Legend Itaú':'https://www.itau.cl/assets/img/tarjetas/legend.png',
'Limitless BICE':'https://www.bice.cl/assets/img/tarjetas/limitless.png',
'Crédito BICE':'https://www.bice.cl/assets/img/tarjetas/credito.png',
'Crédito Security':'https://www.bancosecurity.cl/assets/img/tarjetas/credito.png',
'Rutpay':'https://www.bancoestado.cl/assets/img/tarjetas/rutpay.png',
'Crédito MACHBANK':'https://www.machbank.cl/assets/img/tarjetas/credito.png',
'Jumbo Prime':'https://www.scotiabank.cl/content/dam/scotiabank/cl/images/tarjetas/jumbo-prime.png'
}};

// ── Bank logos ──
const BANK_LOGOS={{
'Banco de Chile':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Banco_de_Chile_Logotipo.svg/200px-Banco_de_Chile_Logotipo.svg.png',
'Banco Falabella':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Logotipo_Banco_Falabella.svg/200px-Logotipo_Banco_Falabella.svg.png',
'BCI':'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Bci_Logotype.svg/200px-Bci_Logotype.svg.png',
'Banco Itau':'https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Ita%C3%BA_Unibanco_logo_2023.svg/200px-Ita%C3%BA_Unibanco_logo_2023.svg.png',
'Itau':'https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Ita%C3%BA_Unibanco_logo_2023.svg/200px-Ita%C3%BA_Unibanco_logo_2023.svg.png',
'Scotiabank':'https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Scotiabank_logo.svg/200px-Scotiabank_logo.svg.png',
'Santander':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Banco_Santander_Logotipo.svg/200px-Banco_Santander_Logotipo.svg.png',
'Banco Consorcio':'/static/logos/consorcio.svg',
'BancoEstado':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Logo_BancoEstado.svg/200px-Logo_BancoEstado.svg.png',
'Banco Security':'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Logo_empresa_banco_security.png/200px-Logo_empresa_banco_security.png',
'Banco Ripley':'https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Logo_Ripley_banco_2.png/200px-Logo_Ripley_banco_2.png',
'Entel':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/EntelChile_Logo.svg/200px-EntelChile_Logo.svg.png',
'Tenpo':'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Logotipo_Tenpo.svg/200px-Logotipo_Tenpo.svg.png',
'Lider BCI':'https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Lider_2025.svg/200px-Lider_2025.svg.png',
'Banco BICE':'/static/logos/bice.svg',
'Mach':'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Logotipo_MACH.svg/200px-Logotipo_MACH.svg.png',
'MACHBANK':'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Logotipo_MACH.svg/200px-Logotipo_MACH.svg.png',
'Santander Consumer':'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Banco_Santander_Logotipo.svg/200px-Banco_Santander_Logotipo.svg.png',
'Cencosud Scotiabank':'/static/logos/cencosud_scotiabank.svg',
'Banco Internacional':'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Logo_banco_internacional.svg/200px-Logo_banco_internacional.svg.png',
'Mercado Pago':'/static/logos/mercadopago.svg',
'ABC Visa':'/static/logos/abcvisa.svg',
'SBPay':'https://play-lh.googleusercontent.com/SBPay-logo.png',
'SPIN':'https://play-lh.googleusercontent.com/SPIN-logo.png',
'Coopeuch':'/static/logos/coopeuch.svg',
'Copec Pay':'/static/logos/copecpay.svg',
'Jumbo Prime':'/static/logos/jumboprime.svg',
'Micopiloto':'/static/logos/micopiloto.svg'
}};
const BANK_COLORS={{
'Banco de Chile':'#003DA5','Banco Falabella':'#00B140',
'BCI':'#E31837','Banco Itau':'#003399','Itau':'#003399','Scotiabank':'#EC111A',
'Santander':'#EC0000','Banco Consorcio':'#003366','BancoEstado':'#00A651',
'Banco Security':'#1B3A5C','Banco Ripley':'#7B2D8E','Entel':'#FF6B00',
'Tenpo':'#00C389','Lider BCI':'#E31837','Banco BICE':'#002F6C','Mach':'#6B21A8',
'MACHBANK':'#6B21A8','Mercado Pago':'#009EE3','ABC Visa':'#1A1F71',
'SBPay':'#FF6B00','SPIN':'#00B8D4','Micopiloto':'#FF5722','Coopeuch':'#0D47A1',
'Copec Pay':'#dc2626','Jumbo Prime':'#E31837','Santander Consumer':'#EC0000',
'Banco Internacional':'#003366','Cencosud Scotiabank':'#EC111A','Rutpay':'#4CAF50'
}};
const BANK_URLS={{
'Banco Consorcio':'https://sitio.consorcio.cl/beneficios',
'Banco Ripley':'https://www.bancoripley.cl/beneficios',
'BCI':'https://www.bci.cl/beneficios',
'Scotiabank':'https://www.scotiabankchile.cl/Personas/beneficios-scotia',
'Cencosud Scotiabank':'https://www.tarjetacencosud.cl/publico/beneficios/landing/inicio',
'Tenpo':'https://www.tenpo.cl/beneficios',
'MACHBANK':'https://www.machbank.cl/beneficios',
'Mach':'https://www.machbank.cl/beneficios',
'Banco BICE':'https://banco.bice.cl/personas/beneficios',
'BancoEstado':'https://www.bancoestado.cl/beneficios',
'Banco Security':'https://www.bancosecurity.cl/beneficios',
'Lider BCI':'https://www.bci.cl/beneficios',
'Itau':'https://itaubeneficios.cl/',
'Banco Itau':'https://itaubeneficios.cl/',
'Mercado Pago':'https://www.mercadopago.cl/',
'ABC Visa':'https://www.visa.cl/es_CL/promociones/',
'SBPay':'https://www.sbpay.cl/beneficios/',
'SPIN':'https://www.spinbyoxxo.com.mx/',
'Micopiloto':'https://www.micopiloto.cl',
'Coopeuch':'https://www.coopeuch.cl/beneficios',
'Copec Pay':'https://appcopec.cl/',
'Jumbo Prime':'https://jumboprime.cl/',
'Santander Consumer':'https://banco.santander.cl/beneficios',
'Banco Internacional':'https://beneficios.internacional.cl/'
}};
// Cadena URLs (Shell, Copec, Aramco) as fallback
const CADENA_URLS={{
'Copec':'https://appcopec.cl/',
'Shell':'https://www.shell.cl/estaciones-de-servicio/promociones-y-campanas.html',
'Aramco':'https://www.aramcoestaciones.cl/'
}};

function bankBadgeHtml(banco){{
const logo=BANK_LOGOS[banco];
if(logo)return `<img src="${{logo}}" alt="${{banco}}" onerror="this.style.display='none';this.nextElementSibling.style.fontSize='11px'"><span>${{banco}}</span>`;
return `<span style="font-size:11px;font-weight:700">${{banco}}</span>`;
}}
function getBankUrl(banco,cadena){{
// Specific bank+chain combos first
const comboKey=banco+'||'+cadena;
const COMBO_URLS={{
'Banco BICE||Shell':'https://banco.bice.cl/personas/beneficios/micopiloto-shell',
'Banco BICE||Copec':'https://banco.bice.cl/personas/beneficios/copec',
'Scotiabank||Copec':'https://www.scotiabank.cl/personas/beneficios/copec',
'Cencosud Scotiabank||Copec':'https://www.cencosudscotiabank.cl/beneficios/copec',
'BCI||Copec':'https://www.bci.cl/beneficios/copec',
'Lider BCI||Shell':'https://www.bci.cl/beneficios/shell',
'Banco Security||Shell':'https://www.bancosecurity.cl/personas/beneficios',
'BancoEstado||Copec':'https://www.bancoestado.cl/beneficios/copec',
'Itaú||Copec':'https://www.bancoitau.cl/beneficios',
'MACHBANK||Copec':'https://www.machbank.cl/beneficios',
'Coopeuch||Copec':'https://www.coopeuch.cl/beneficios',
'Banco Consorcio||Aramco':'https://www.bancoconsorcio.cl/beneficios',
'Tenpo||Aramco':'https://www.tenpo.cl/beneficios',
'Banco Ripley||Aramco':'https://www.bancoripley.cl/beneficios',
}};
if(COMBO_URLS[comboKey])return COMBO_URLS[comboKey];
if(cadena&&CADENA_URLS[cadena])return CADENA_URLS[cadena];
return BANK_URLS[banco]||'#';
}}

// ── View toggle ──
let currentView='tarjetas';
document.querySelectorAll('.view-btn').forEach(btn=>{{btn.addEventListener('click',()=>{{
document.querySelectorAll('.view-btn').forEach(b=>b.classList.remove('active'));
document.querySelectorAll('.view-content').forEach(c=>c.classList.remove('active'));
btn.classList.add('active');
currentView=btn.dataset.view;
document.getElementById('view-'+currentView).classList.add('active');
if(currentView==='mapa'){{initMap();setTimeout(()=>{{if(mapObj)mapObj.invalidateSize();renderMapMarkers()}},80)}}
if(currentView==='precios'){{initPreciosView()}}
}})}});

// ── Card grid ──
const grid=document.getElementById('grid'),empty=document.getElementById('empty'),
countEl=document.getElementById('count'),search=document.getElementById('search'),
sortF=document.getElementById('sortFilter'),summaryBar=document.getElementById('summaryBar');

// ── Multi-Select Component ──
const bankOpts={bancos_json_list};
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
this._tags();renderAll()}})}});
const si=this.el.querySelector('.ms-search-input');
if(si){{si.addEventListener('input',()=>{{const q=si.value.toLowerCase();
this.el.querySelectorAll('.ms-option').forEach(o=>{{o.style.display=o.textContent.toLowerCase().includes(q)?'':'none'}})}});
si.addEventListener('click',e=>e.stopPropagation())}}
document.addEventListener('click',e=>{{if(!this.el.contains(e.target))this.el.classList.remove('open')}})}}
_tags(){{
const t=this.el.querySelector('.ms-tags');
if(!this.sel.size){{t.innerHTML=`<span class="ms-placeholder">${{this.ph}}</span>`;return}}
t.innerHTML=[...this.sel].map(v=>`<span class="ms-tag">${{v}}<span class="ms-remove" data-v="${{v}}">x</span></span>`).join('');
t.querySelectorAll('.ms-remove').forEach(x=>{{x.addEventListener('click',e=>{{
e.stopPropagation();this.sel.delete(x.dataset.v);
const c=[...this.el.querySelectorAll('input[type=checkbox]')].find(c=>c.value===x.dataset.v);
if(c)c.checked=false;this._tags();renderAll()}})}})}}
vals(){{return this.sel.size?[...this.sel]:null}}
reset(){{this.sel.clear();this.el.querySelectorAll('input[type=checkbox]').forEach(c=>c.checked=false);this._tags()}}
}}
const bankMS=new MS('bankMS',bankOpts,'Todos los bancos');

function chipVal(id,attr){{const a=document.querySelector('#'+id+' .chip.active');return a?a.dataset[attr]:'all'}}
function initChips(id,attr){{document.getElementById(id).addEventListener('click',e=>{{
const c=e.target.closest('.chip');if(!c)return;
document.querySelectorAll('#'+id+' .chip').forEach(x=>x.classList.remove('active'));c.classList.add('active')}})}}
initChips('cadenaChips','cadena');

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

// ── Normalize for search ──
function norm(s){{return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/[^a-z0-9\\s]/g,'')}}

function render(){{
const qRaw=search.value.trim();
const qWords=qRaw?norm(qRaw).split(/\\s+/).filter(w=>w.length>0):[];
const banks=bankMS.vals();
const sort=sortF.value,selDays=getSelectedDays(),cadena=chipVal('cadenaChips','cadena');
let f=deals.filter(d=>{{
const txt=norm([d.cadena,d.banco,d.tarjeta,d.condicion||'',d.descuento_texto||''].join(' '));
const mS=!qWords.length||qWords.every(w=>txt.includes(w));
const mB=!banks||banks.includes(d.banco);
const mCad=cadena==='all'||d.cadena===cadena;
const mDay=!selDays||d.dias_validos.includes('todos')||selDays.some(sd=>d.dias_validos.includes(sd));
return mS&&mB&&mCad&&mDay}});
f.sort((a,b)=>{{switch(sort){{case'desc-asc':return a.descuento_por_litro-b.descuento_por_litro;
case'name':return a.cadena.localeCompare(b.cadena);
case'bank':return a.banco.localeCompare(b.banco);
default:return b.descuento_por_litro-a.descuento_por_litro}}}});
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
if(cb){{cb.checked=!cb.checked;if(cb.checked)bankMS.sel.add(banco);else bankMS.sel.delete(banco);bankMS._tags();renderAll()}}
}})}});
}}else{{summaryBar.style.display='none';summaryBar.innerHTML=''}}
grid.innerHTML='';
if(!f.length){{empty.style.display='block';countEl.textContent='0 encontrados';return}}
empty.style.display='none';
// ── Group deals by banco+cadena+day (one card per group) ──
const groups={{}};
f.forEach(d=>{{
const dayKey=d.dias_validos.sort().join(',');
const key=d.banco+'||'+d.cadena+'||'+dayKey;
if(!groups[key])groups[key]={{deals:[],banco:d.banco,cadena:d.cadena,dias_validos:d.dias_validos,
condicion:d.condicion,valido_hasta:d.valido_hasta,vigencia_mes:d.vigencia_mes}};
groups[key].deals.push(d)}});
const grouped=Object.values(groups);
// Sort groups by best descuento
grouped.sort((a,b)=>{{
const aMax=Math.max(...a.deals.map(d=>d.descuento_por_litro));
const bMax=Math.max(...b.deals.map(d=>d.descuento_por_litro));
switch(sort){{case'desc-asc':return aMax-bMax;case'name':return a.cadena.localeCompare(b.cadena);
case'bank':return a.banco.localeCompare(b.banco);default:return bMax-aMax}}}});
countEl.textContent=grouped.length+' beneficios ('+f.length+' variantes)';
const DAY_MAP=[['lunes','L'],['martes','M'],['miercoles','X'],['jueves','J'],['viernes','V'],['sabado','S'],['domingo','D']];
grouped.forEach(g=>{{
const bestDeal=g.deals.reduce((a,b)=>b.descuento_por_litro>a.descuento_por_litro?b:a);
// Hero card with station background image
const chainImg=CHAIN_IMAGES[g.cadena];
const chainLg=CHAIN_LOGOS[g.cadena];
const bgHtml=chainImg?`<img class="hero-bg" src="${{chainImg}}" alt="${{g.cadena}}" loading="lazy" onerror="this.parentNode.querySelector('.hero-overlay').style.background='linear-gradient(135deg,#667eea,#764ba2)';this.style.display='none'">`:'';
const chainBadge=chainLg?`<div class="chain-logo-hero"><img src="${{chainLg}}" alt="${{g.cadena}}"></div>`:`<div class="chain-logo-hero"><span style="font-weight:800;font-size:14px">⛽ ${{g.cadena}}</span></div>`;
const bankLogo=BANK_LOGOS[g.banco];
const dayCircles=DAY_MAP.map(([k,l])=>{{
const on=g.dias_validos.includes(k)||g.dias_validos.includes('todos');
return `<div class="day-circle${{on?' active':''}}">${{l}}</div>`}}).join('');
const detailUrl=getBankUrl(g.banco,g.cadena);
const linkHtml=`<a class="link" href="${{detailUrl}}" target="_blank">Ver detalle</a>`;
// Badge: show range if multiple
const maxD=Math.max(...g.deals.map(d=>d.descuento_por_litro));
const minD=Math.min(...g.deals.map(d=>d.descuento_por_litro));
const badgeText=maxD===minD?'$'+maxD+'/L':'$'+minD+'-$'+maxD+'/L';
// Tarjeta breakdown rows
const tarjetaRows=g.deals.sort((a,b)=>b.descuento_por_litro-a.descuento_por_litro).map(d=>{{
const tImg=TARJETA_IMAGES[d.tarjeta];
const imgTag=tImg?`<img src="${{tImg}}" onerror="this.style.display='none'" alt="${{d.tarjeta}}">`:'<span style="font-size:22px">💳</span>';
let topeInfo='';
if(d.tope_monto)topeInfo=`<div style="color:var(--muted);font-size:11px;margin-top:2px">Tope ${{d.tope_monto.toLocaleString()}}/mes</div>`;
return `<div class="tarjeta-row">
${{imgTag}}
<div style="flex:1"><div style="font-size:14px;font-weight:600">${{d.tarjeta}}</div>${{topeInfo}}</div>
<div class="tarjeta-dcto">${{d.descuento_texto||'$'+d.descuento_por_litro+'/L'}}</div>
</div>`}}).join('');
const condText=g.condicion?`<div class="deal-desc">📱 ${{g.condicion}}</div>`:'';
// Chain logo
const chainLogo=CHAIN_LOGOS[g.cadena];
const chainLogoHtml=chainLogo?`<img class="deal-chain-logo" src="${{chainLogo}}" alt="${{g.cadena}}" onerror="this.style.display='none'">`
:`<span style="font-weight:700;font-size:13px">${{g.cadena}}</span>`;
const el=document.createElement('article');el.className='deal';
const bankLogoTag=bankLogo?`<img src="${{bankLogo}}" style="height:16px;border-radius:2px" onerror="this.style.display='none'">`:''
;const bankLogoSub=bankLogo?`<img src="${{bankLogo}}" onerror="this.style.display='none'">`:''
;const chainLogoSub=CHAIN_LOGOS[g.cadena]?`<img src="${{CHAIN_LOGOS[g.cadena]}}" onerror="this.style.display='none'">`:''
;el.innerHTML=`<div class="deal-img">${{bgHtml}}<div class="hero-overlay"></div>
${{chainBadge}}
<div class="badge">${{badgeText}}</div></div>
<div class="deal-header"><h3>${{g.cadena}} · ${{g.banco}}</h3>
<div class="hero-sub">
<span class="sub-tag bank">${{bankLogoSub}}${{g.banco}}</span>
<span class="sub-tag mode">⛽ Presencial</span>
<span class="sub-tag chain">${{chainLogoSub}}${{g.cadena}}</span>
</div></div>
<div class="deal-body">
<div class="day-bar"><div class="day-circles">${{dayCircles}}</div><span class="mode-badge presencial">⛽ Presencial</span></div>
<div style="display:flex;flex-direction:column;gap:4px">${{tarjetaRows}}</div>
<div class="cta-row">${{linkHtml}}</div></div>
<div class="deal-footer">
<div class="validity">⏳ Vigencia: ${{g.valido_hasta||g.vigencia_mes||'Sin fecha'}}</div>
<div class="disclaimer">⚠️ Condiciones sujetas al banco o app</div></div>`;
grid.appendChild(el)}})}}

function renderAll(){{render();if(currentView==='mapa'&&mapObj)renderMapMarkers()}}
function resetAll(){{
search.value='';bankMS.reset();
sortF.value='desc-desc';
document.querySelectorAll('#cadenaChips .chip').forEach(c=>c.classList.remove('active'));
document.querySelector('#cadenaChips .chip[data-cadena="all"]').classList.add('active');
dayAll.classList.add('active');daySels.forEach(s=>s.classList.remove('active'));renderAll()}}
document.getElementById('resetBtn').addEventListener('click',resetAll);
document.getElementById('resetBtn2').addEventListener('click',resetAll);
render();
search.addEventListener('input',renderAll);sortF.addEventListener('change',renderAll);
daySelect.addEventListener('click',()=>setTimeout(renderAll,10));
document.getElementById('cadenaChips').addEventListener('click',()=>setTimeout(renderAll,10));

// ── MAP ──
let mapObj=null,clusterGroup=null;
function initMap(){{
if(mapObj){{mapObj.invalidateSize();renderMapMarkers();return}}
mapObj=L.map('bencina-map').setView([-33.45,-70.65],11);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png',{{
attribution:'&copy; <a href="https://carto.com">CARTO</a>',maxZoom:19}}).addTo(mapObj);
clusterGroup=L.markerClusterGroup({{maxClusterRadius:40}});
mapObj.addLayer(clusterGroup);
renderMapMarkers();
}}
function renderMapMarkers(){{
if(!clusterGroup)return;
clusterGroup.clearLayers();
const cadena=chipVal('cadenaChips','cadena');
const banks=bankMS.vals();
const selDays=getSelectedDays();
const qRaw=search.value.trim();
const qWords=qRaw?norm(qRaw).split(/\\s+/).filter(w=>w.length>0):[];
// Filter stations by cadena
let filtSt=stations;
if(cadena!=='all')filtSt=filtSt.filter(s=>s.cadena===cadena);
// Filter deals
let filtDeals=deals.filter(d=>{{
const mB=!banks||banks.includes(d.banco);
const mCad=cadena==='all'||d.cadena===cadena;
const mDay=!selDays||d.dias_validos.includes('todos')||selDays.some(sd=>d.dias_validos.includes(sd));
const txt=norm([d.cadena,d.banco,d.tarjeta].join(' '));
const mS=!qWords.length||qWords.every(w=>txt.includes(w));
return mB&&mCad&&mDay&&mS}});
const dealsByChain={{}};
filtDeals.forEach(d=>{{if(!dealsByChain[d.cadena])dealsByChain[d.cadena]=[];dealsByChain[d.cadena].push(d)}});
let count=0;
filtSt.forEach(s=>{{
if(!s.latitud||!s.longitud)return;
const stDeals=dealsByChain[s.cadena]||[];
const color=CHAIN_COLORS[s.cadena]||'#6b7280';
const logo=CHAIN_LOGOS[s.cadena];
const iconHtml=logo
  ?`<div style="background:#fff;padding:3px;border-radius:50%;border:2px solid ${{color}};box-shadow:0 2px 6px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center"><img src="${{logo}}" style="height:16px;width:16px;object-fit:contain"></div>`
  :`<div style="background:${{color}};width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)"></div>`;
const icon=L.divIcon({{className:'',html:iconHtml,iconSize:[24,24],iconAnchor:[12,12]}});
const mapsUrl=`https://www.google.com/maps/dir/?api=1&destination=${{s.latitud}},${{s.longitud}}`;
let popup=`<div style="min-width:220px;font-family:Inter,sans-serif">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
${{logo?`<img src="${{logo}}" style="height:22px">`:''}}
<span class="popup-title">${{s.nombre}}</span>
</div>
<div style="font-size:12px;color:#6b7280">📍 ${{s.direccion}} - ${{s.comuna}}</div>`;
if(s.precio_93||s.precio_97||s.precio_diesel){{
popup+=`<div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">`;
if(s.precio_93)popup+=`<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">93: $${{s.precio_93.toLocaleString()}}</span>`;
if(s.precio_97)popup+=`<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">97: $${{s.precio_97.toLocaleString()}}</span>`;
if(s.precio_diesel)popup+=`<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">DI: $${{s.precio_diesel.toLocaleString()}}</span>`;
popup+=`</div>`}}
if(stDeals.length>0){{
popup+=`<hr style="margin:8px 0;border:0;border-top:1px solid #e5e2da">`;
popup+=`<div style="font-weight:600;font-size:12px;margin-bottom:4px">Descuentos:</div>`;
stDeals.forEach(d=>{{
const isToday=d.dias_validos.includes(HOY);
const blogo=BANK_LOGOS[d.banco]?`<img src="${{BANK_LOGOS[d.banco]}}" style="height:14px">`:'';
popup+=`<div style="padding:3px 0;font-size:12px;${{isToday?'color:#ea580c;font-weight:600':''}}">
<strong>${{d.descuento_texto}}</strong> ${{blogo}} ${{d.banco}} ${{isToday?'🎯 HOY':''}}</div>`}})}}
popup+=`<div style="margin-top:8px"><a href="${{mapsUrl}}" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;background:#4285F4;color:#fff;border-radius:8px;font-size:11px;font-weight:600;text-decoration:none">📍 Ir</a></div>`;
popup+=`</div>`;
L.marker([s.latitud,s.longitud],{{icon}}).bindPopup(popup,{{maxWidth:300}}).addTo(clusterGroup);
count++}});
document.getElementById('mapCount').textContent=count+' estaciones';
}}

// ── Geolocation ──
let geoMarker=null,geoActive=false;
function toggleGeolocation(){{
const btn=document.getElementById('geoBtn'),status=document.getElementById('geoStatus');
if(geoActive){{
  geoActive=false;btn.classList.remove('active');
  if(geoMarker){{mapObj.removeLayer(geoMarker);geoMarker=null}}
  status.textContent='';return;
}}
if(!navigator.geolocation){{status.textContent='Tu navegador no soporta geolocalizacion';return}}
btn.classList.add('loading');status.textContent='Obteniendo ubicacion...';
navigator.geolocation.getCurrentPosition(
  pos=>{{
    geoActive=true;btn.classList.remove('loading');btn.classList.add('active');
    const lat=pos.coords.latitude,lng=pos.coords.longitude;
    status.textContent=`📍 ${{lat.toFixed(4)}}, ${{lng.toFixed(4)}}`;
    if(!mapObj)initMap();
    if(geoMarker)mapObj.removeLayer(geoMarker);
    const geoIcon=L.divIcon({{className:'',html:`<div style="position:relative"><div style="width:18px;height:18px;background:#4285F4;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 8px rgba(66,133,244,.5)"></div><div style="position:absolute;top:-6px;left:-6px;width:30px;height:30px;border-radius:50%;background:rgba(66,133,244,.15);animation:geoPulse 2s infinite"></div></div>`,
    iconSize:[18,18],iconAnchor:[9,9]}});
    geoMarker=L.marker([lat,lng],{{icon:geoIcon,zIndex:9999}}).addTo(mapObj)
      .bindPopup('<div style="text-align:center"><strong>📍 Estas aqui</strong><br><span style="color:#6b7280;font-size:12px">Tu ubicacion actual</span></div>');
    mapObj.setView([lat,lng],14);
    geoMarker.openPopup();
  }},
  err=>{{
    btn.classList.remove('loading');
    const msgs={{1:'Permiso denegado',2:'Ubicacion no disponible',3:'Tiempo agotado'}};
    status.textContent='⚠️ '+(msgs[err.code]||'Error desconocido');
  }},
  {{enableHighAccuracy:true,timeout:10000,maximumAge:60000}}
);
}}
(function(){{const s=document.createElement('style');s.textContent='@keyframes geoPulse{{0%{{transform:scale(1);opacity:.6}}100%{{transform:scale(2.5);opacity:0}}}}';document.head.appendChild(s)}})();

// ── COMPARADOR DE PRECIOS ──
let preciosMapObj=null,preciosCluster=null,preciosInited=false;
const FUEL_FIELD={{'93':'precio_93','95':'precio_95','97':'precio_97','diesel':'precio_diesel','kerosene':'precio_kerosene'}};

function initPreciosView(){{
  if(!preciosInited){{
    preciosInited=true;
    const regSel=document.getElementById('precioRegion');
    REGIONES.forEach(r=>{{const o=document.createElement('option');o.value=r;o.textContent=r;regSel.appendChild(o)}});
    regSel.addEventListener('change',()=>{{
      const comSel=document.getElementById('precioComuna');
      comSel.innerHTML='<option value="">Todas las comunas</option>';
      const reg=regSel.value;
      if(reg&&COMUNAS_MAP[reg]){{COMUNAS_MAP[reg].forEach(c=>{{const o=document.createElement('option');o.value=c;o.textContent=c;comSel.appendChild(o)}})}}
      renderPrecios()
    }});
    document.getElementById('precioComuna').addEventListener('change',renderPrecios);
    document.getElementById('precioCadena').addEventListener('change',renderPrecios);
    document.getElementById('fuelChips').addEventListener('click',e=>{{
      if(!e.target.classList.contains('fuel-chip'))return;
      document.querySelectorAll('.fuel-chip').forEach(c=>c.classList.remove('active'));
      e.target.classList.add('active');renderPrecios()
    }});
  }}
  setTimeout(()=>{{
    if(!preciosMapObj){{
      preciosMapObj=L.map('precios-map').setView([-33.45,-70.65],10);
      L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png',{{attribution:'&copy; CARTO',maxZoom:19}}).addTo(preciosMapObj);
      preciosCluster=L.markerClusterGroup({{maxClusterRadius:35}});
      preciosMapObj.addLayer(preciosCluster)
    }}else{{preciosMapObj.invalidateSize()}}
    renderPrecios()
  }},100)
}}

function renderPrecios(){{
  const fuelBtn=document.querySelector('.fuel-chip.active');
  const fuel=fuelBtn?fuelBtn.dataset.fuel:'93';
  const field=FUEL_FIELD[fuel]||'precio_93';
  const region=document.getElementById('precioRegion').value;
  const comuna=document.getElementById('precioComuna').value;
  const cadena=document.getElementById('precioCadena').value;
  let filtered=allPrices.filter(e=>{{
    const precio=e[field]||0;
    if(precio<=0)return false;
    if(region&&!e.region.includes(region))return false;
    if(comuna&&e.comuna!==comuna)return false;
    if(cadena==='otra'){{if(['Copec','Shell','Aramco'].includes(e.cadena))return false}}
    else if(cadena&&e.cadena!==cadena)return false;
    return true
  }});
  filtered.sort((a,b)=>(a[field]||9999)-(b[field]||9999));
  const prices=filtered.map(e=>e[field]);
  const minP=prices.length?Math.min(...prices):0;
  const maxP=prices.length?Math.max(...prices):0;
  const avgP=prices.length?Math.round(prices.reduce((a,b)=>a+b,0)/prices.length):0;
  document.getElementById('preciosStats').innerHTML=`
    <div class="ps-card"><div class="ps-label">Mas barato</div><div class="ps-value ps-min">$${{minP.toLocaleString()}}</div></div>
    <div class="ps-card"><div class="ps-label">Mas caro</div><div class="ps-value ps-max">$${{maxP.toLocaleString()}}</div></div>
    <div class="ps-card"><div class="ps-label">Promedio</div><div class="ps-value ps-avg">$${{avgP.toLocaleString()}}</div></div>
    <div class="ps-card"><div class="ps-label">Estaciones</div><div class="ps-value ps-count">${{filtered.length}}</div></div>`;
  document.getElementById('preciosCount').textContent=filtered.length+' estaciones';
  // Ranking list with logos
  const list=document.getElementById('preciosList');
  const top=filtered.slice(0,50);
  list.innerHTML=top.map((e,i)=>{{
    const precio=e[field];const diff=precio-minP;
    const color=CHAIN_COLORS[e.cadena]||'#6b7280';
    const cls=i<3?'cheapest':(precio>=maxP-10?'expensive':'normal');
    const rankCls=i<3?'top3':'';
    const logo=CHAIN_LOGOS[e.cadena]||'';
    const logoHtml=logo?`<img src="${{logo}}" style="height:22px;width:auto;object-fit:contain">`:`<div class="precio-chain-dot" style="background:${{color}}"></div>`;
    const mapsUrl=`https://www.google.com/maps/dir/?api=1&destination=${{e.latitud}},${{e.longitud}}`;
    return `<div class="precio-row">
      <span class="precio-rank ${{rankCls}}">#${{i+1}}</span>
      ${{logoHtml}}
      <div class="precio-info" onclick="precioZoom(${{e.latitud}},${{e.longitud}})" style="cursor:pointer">
        <div class="precio-name">${{e.cadena}} - ${{e.direccion||'Sin direccion'}}</div>
        <div class="precio-addr">${{e.comuna}}, ${{e.region}}</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <div>
          <div class="precio-value ${{cls}}">$${{precio.toLocaleString()}}</div>
          ${{diff>0?`<div class="precio-diff">+$${{diff.toLocaleString()}}</div>`:`<div class="precio-diff" style="color:#16a34a;font-weight:600">Mejor precio</div>`}}
        </div>
        <a href="${{mapsUrl}}" target="_blank" rel="noopener" style="display:flex;align-items:center;gap:3px;padding:6px 10px;background:#4285F4;color:#fff;border-radius:8px;font-size:11px;font-weight:600;text-decoration:none;white-space:nowrap" title="Abrir en Google Maps">Ir</a>
      </div>
    </div>`}}).join('');
  // Map markers with chain logos and colors
  if(preciosCluster){{
    preciosCluster.clearLayers();
    filtered.slice(0,300).forEach((e,i)=>{{
      if(!e.latitud||!e.longitud)return;
      const precio=e[field];
      const color=CHAIN_COLORS[e.cadena]||'#6b7280';
      const logo=CHAIN_LOGOS[e.cadena];
      const iconHtml=logo
        ?`<div style="display:flex;align-items:center;gap:3px;background:#fff;padding:3px 6px;border-radius:10px;border:2px solid ${{color}};box-shadow:0 2px 6px rgba(0,0,0,.25);white-space:nowrap"><img src="${{logo}}" style="height:16px;width:auto"><span style="font-size:10px;font-weight:700;color:${{color}}">$${{precio.toLocaleString()}}</span></div>`
        :`<div style="background:${{color}};color:#fff;font-size:10px;font-weight:700;padding:3px 6px;border-radius:10px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.25);white-space:nowrap">$${{precio.toLocaleString()}}</div>`;
      const icon=L.divIcon({{className:'',html:iconHtml,iconSize:[null,null],iconAnchor:[30,12]}});
      const mapsUrl=`https://www.google.com/maps/dir/?api=1&destination=${{e.latitud}},${{e.longitud}}`;
      const popup=`<div style="font-family:Inter,sans-serif;min-width:200px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          ${{logo?`<img src="${{logo}}" style="height:24px">`:''}}
          <span style="font-weight:700;font-size:14px">${{e.cadena}}</span>
        </div>
        <div style="font-size:12px;color:#374151">${{e.direccion}}</div>
        <div style="font-size:11px;color:#9ca3af">${{e.comuna}}, ${{e.region}}</div>
        <hr style="margin:8px 0;border:0;border-top:1px solid #e5e7eb">
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">
        ${{e.precio_93?`<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">93: $${{e.precio_93.toLocaleString()}}</span>`:''}}
        ${{e.precio_97?`<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">97: $${{e.precio_97.toLocaleString()}}</span>`:''}}
        ${{e.precio_diesel?`<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">DI: $${{e.precio_diesel.toLocaleString()}}</span>`:''}}
        </div>
        <a href="${{mapsUrl}}" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:4px;padding:6px 14px;background:#4285F4;color:#fff;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none">📍 Ir</a>
      </div>`;
      L.marker([e.latitud,e.longitud],{{icon}}).bindPopup(popup,{{maxWidth:300}}).addTo(preciosCluster)
    }})
  }}
}}
function precioZoom(lat,lng){{if(preciosMapObj)preciosMapObj.setView([lat,lng],15)}}
</script>
</body></html>"""

    return HTMLResponse(page)


@app.post("/webhook")
async def webhook_whatsapp(From: str = Form(""), Body: str = Form("")):
    """Webhook para Twilio WhatsApp Sandbox"""
    from twilio.twiml.messaging_response import MessagingResponse

    usuario = From.replace("whatsapp:", "")
    print(f"  WhatsApp de {usuario}: {Body}")

    respuesta = await procesar_comando_whatsapp(Body, usuario=usuario)

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

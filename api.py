"""
API REST - BENEFICIOS BANCARIOS
================================
FastAPI + OpenAI RAG
"""

from fastapi import FastAPI, HTTPException, Query, Form, Response
from fastapi.middleware.cors import CORSMiddleware
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
    if texto in ['/', 'help', 'menu', 'comandos']:
        return """*Beneficios Bancarios Chile* 🇨🇱

Puedes escribirme lo que quieras, por ejemplo:
• "descuentos para hoy"
• "donde comer sushi con descuento"
• "mejores descuentos banco falabella"
• "restaurantes con 30% o mas"

*Atajos rapidos:*
/top - Top 5 restaurantes
/stats - Estadisticas"""

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
        for banco_nombre in ['falabella', 'banco de chile', 'chile']:
            if banco_nombre in texto:
                banco_filtro = 'Falabella' if 'falabella' in banco_nombre else 'Banco de Chile'
                break

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
                        "- SIEMPRE agrupa los resultados por banco con esta jerarquía:\n"
                        "  *🏦 Nombre del Banco* (X descuentos)\n"
                        "  • Restaurante - descuento - ubicación\n"
                        "- Incluye TODOS los restaurantes del contexto, no omitas ninguno\n"
                        "- Usa formato WhatsApp: *negrita* para bancos y restaurantes\n"
                        "- Máximo 3800 caracteres\n"
                        "- Si hay muchos resultados, lista todos pero de forma compacta\n"
                        "- Termina con un resumen del total\n"
                        "- Responde en español chileno casual con emojis"
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
            max_tokens=1000,
        )
        respuesta = response.choices[0].message.content
        return respuesta[:4000]  # WhatsApp soporta hasta 4096 chars

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

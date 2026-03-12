"""
BOT WHATSAPP - BENEFICIOS BANCARIOS
====================================
Integración con Twilio WhatsApp
"""

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os
import json
from datetime import datetime
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Importar modelo
from scrapers import Beneficio

# ============================================
# CONFIGURACIÓN
# ============================================

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")

# Solo inicializar Twilio client si hay credenciales
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    from twilio.rest import Client
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Base de datos de beneficios
beneficios_db: List[Beneficio] = []

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def cargar_beneficios():
    """Carga beneficios desde JSON"""
    global beneficios_db
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "beneficios.json")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            beneficios_db = [Beneficio(**item) for item in data]
            print(f"  Cargados {len(beneficios_db)} beneficios")
    except FileNotFoundError:
        print("  Archivo beneficios.json no encontrado")


def buscar_beneficios(restaurante=None, banco=None, dia=None):
    """Busca beneficios con filtros"""
    resultados = beneficios_db

    if restaurante:
        r = restaurante.lower()
        resultados = [b for b in resultados if r in b.restaurante.lower()]

    if banco:
        b_lower = banco.lower()
        resultados = [b for b in resultados if b_lower in b.banco.lower()]

    if dia:
        d = dia.lower()
        resultados = [
            b for b in resultados
            if d in [x.lower() for x in b.dias_validos]
            or 'todos' in [x.lower() for x in b.dias_validos]
        ]

    return resultados


def formatear_beneficios(beneficios, max_items=3):
    """Formatea beneficios para WhatsApp (max 1600 chars)"""
    if not beneficios:
        return "No encontre beneficios para esa busqueda. Intenta con otro nombre."

    texto = f"*{len(beneficios)} beneficios encontrados:*\n\n"
    for i, b in enumerate(beneficios[:max_items], 1):
        dias = ", ".join(b.dias_validos) if b.dias_validos else "Consultar"
        texto += f"{i}. *{b.restaurante}*\n"
        texto += f"   {b.banco}\n"
        texto += f"   {b.descuento_texto}\n"
        texto += f"   Dias: {dias}\n"
        if b.ubicacion:
            texto += f"   {b.ubicacion}\n"
        if b.restricciones_texto:
            restriccion = b.restricciones_texto[:80]
            texto += f"   {restriccion}...\n"
        texto += "\n"

    if len(beneficios) > max_items:
        texto += f"... y {len(beneficios) - max_items} mas.\n"

    return texto[:1500]


def procesar_comando(texto, usuario_id):
    """Procesa comandos del usuario"""
    texto = texto.strip().lower()

    # Menu principal
    if texto in ['/', 'hola', 'hi', 'help', 'menu', 'inicio']:
        return """Bienvenido a *Beneficios Bancarios Chile*

Que quieres buscar?

*Comandos:*
/restaurante [nombre] - Buscar restaurante
/banco [banco] - Descuentos de un banco
/dia [dia] - Descuentos para un dia
/top - Top 5 restaurantes
/stats - Estadisticas

*Ejemplo:*
/restaurante pizza
/banco falabella
/dia lunes"""

    # Busqueda por restaurante
    if texto.startswith('/restaurante '):
        nombre = texto.replace('/restaurante ', '').strip()
        resultados = buscar_beneficios(restaurante=nombre)
        return formatear_beneficios(resultados)

    # Busqueda por banco
    if texto.startswith('/banco '):
        nombre = texto.replace('/banco ', '').strip().replace('"', '')
        resultados = buscar_beneficios(banco=nombre)
        return formatear_beneficios(resultados, max_items=5)

    # Busqueda por dia
    if texto.startswith('/dia '):
        dia = texto.replace('/dia ', '').strip()
        resultados = buscar_beneficios(dia=dia)
        return formatear_beneficios(resultados, max_items=5)

    # Top restaurantes
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

    # Estadisticas
    if texto == '/stats':
        total_bancos = len(set(b.banco for b in beneficios_db))
        total_rest = len(set(b.restaurante for b in beneficios_db))
        vals = [b.descuento_valor for b in beneficios_db if b.descuento_valor > 0]
        promedio = sum(vals) / len(vals) if vals else 0

        return f"""*Estadisticas*

Total Beneficios: {len(beneficios_db)}
Total Bancos: {total_bancos}
Total Restaurantes: {total_rest}
Descuento Promedio: {promedio:.1f}%
Descuento Maximo: {max(vals) if vals else 0}%
Ultima actualizacion: {datetime.now().strftime('%d/%m/%Y')}"""

    # Busqueda libre
    if len(texto) > 2:
        resultados = buscar_beneficios(restaurante=texto)
        if resultados:
            return formatear_beneficios(resultados)

    return "No entiendo el comando.\n\nEscribe */* para ver el menu."


# ============================================
# RUTAS WEBHOOK
# ============================================

@app.route("/", methods=["GET"])
def index():
    return {
        "status": "Bot WhatsApp funcionando",
        "total_beneficios": len(beneficios_db),
        "webhook": "POST /webhook"
    }


@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook de Twilio WhatsApp"""
    sender = request.values.get("From", "")
    mensaje_texto = request.values.get("Body", "").strip()
    usuario_id = sender.replace("whatsapp:", "")

    print(f"  Mensaje de {usuario_id}: {mensaje_texto}")

    respuesta = procesar_comando(mensaje_texto, usuario_id)

    resp = MessagingResponse()
    resp.message(respuesta)

    return str(resp)


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    return {"status": "ok"}


@app.route("/test", methods=["GET"])
def test_bot():
    """Endpoint para probar comandos sin WhatsApp"""
    comando = request.args.get("cmd", "/")
    respuesta = procesar_comando(comando, "test")
    return {"comando": comando, "respuesta": respuesta}


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("  Cargando beneficios...")
    cargar_beneficios()

    print(f"  Bot WhatsApp iniciado")
    print(f"  Servidor en http://localhost:5000")
    print(f"  Webhook en http://localhost:5000/webhook")
    print(f"  Test en http://localhost:5000/test?cmd=/stats\n")

    app.run(debug=True, port=5000)

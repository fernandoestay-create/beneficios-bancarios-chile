# 🚀 Guía de Setup Completa

> Actualizado: 15 Marzo 2026 · v_01

---

## 📋 Índice

1. [Requisitos](#-requisitos)
2. [Instalación local](#-instalación-local)
3. [Configuración de APIs](#-configuración-de-apis)
4. [Ejecución paso a paso](#-ejecución-paso-a-paso)
5. [Deploy en Render](#-deploy-en-render)
6. [Configurar WhatsApp (Twilio)](#-configurar-whatsapp-twilio)
7. [Actualización de datos](#-actualización-de-datos)
8. [Troubleshooting](#-troubleshooting)

---

## 📦 Requisitos

### Software
- **Python 3.9+** (recomendado 3.11+)
- **Git**
- **pip** (gestor de paquetes Python)

### Cuentas necesarias

| Servicio | Para qué | ¿Obligatorio? |
|----------|----------|----------------|
| GitHub | Repo + deploy automático | ✅ Sí |
| Render | Hosting en producción | ✅ Sí |
| OpenAI | RAG con GPT-4o-mini | ⚠️ Solo para IA del bot |
| Pinecone | Búsqueda semántica | ⚠️ Solo para RAG |
| Twilio | Bot WhatsApp | ⚠️ Solo para WhatsApp |

> Sin OpenAI/Pinecone: la página web funciona 100%. El bot funciona con flujo de 3 pasos pero NO con consultas libres de IA.

---

## 🔧 Instalación local

### Paso 1: Clonar repositorio

```bash
git clone https://github.com/fernandoestay-create/beneficios-bancarios-chile.git
cd beneficios-bancarios-chile
```

### Paso 2: Crear entorno virtual

```bash
# Mac/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

**Dependencias instaladas:**
```
# Scraping
requests          → HTTP requests a los bancos
beautifulsoup4    → Parsear HTML
lxml              → Parser rápido para BS4
playwright        → Para sitios con JS (no usado actualmente)

# API REST
fastapi           → Framework web
uvicorn           → Servidor ASGI
pydantic          → Validación de datos
python-multipart  → Parsear form data (Twilio webhook)

# Bot WhatsApp
twilio            → SDK de Twilio
flask             → Framework para bot alternativo
python-dotenv     → Leer .env

# RAG / IA
openai            → GPT-4o-mini + embeddings
pinecone          → Base de datos vectorial

# Deploy
gunicorn          → Servidor WSGI (para Flask bot)
```

### Paso 4: Configurar variables de entorno

```bash
# Crear archivo .env en la raíz del proyecto
cat > .env << 'EOF'
# OpenAI (para RAG del bot)
OPENAI_API_KEY=sk-...

# Pinecone (para búsqueda semántica)
PINECONE_API_KEY=...
PINECONE_ENV=us-east-1
PINECONE_INDEX=beneficios-bancarios
PINECONE_HOST=beneficios-bancarios-XXXXX.svc.aped-4627-b74a.pinecone.io

# Twilio (solo si usas whatsapp_bot.py)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+...
EOF
```

> ⚠️ El archivo `.env` NO se sube a Git (está en `.gitignore`).

---

## ⚙️ Configuración de APIs

### 🟢 OpenAI

1. Ir a https://platform.openai.com/api-keys
2. Crear nueva API Key
3. Copiar y pegar en `.env` como `OPENAI_API_KEY=sk-...`

**Uso en el proyecto:**
- Modelo: `gpt-4o-mini` (respuestas del bot WhatsApp)
- Embeddings: `text-embedding-3-small` (vectorización para Pinecone)
- Costo estimado: ~$0.50/mes con uso moderado

### 🟣 Pinecone

1. Ir a https://www.pinecone.io/ → crear cuenta (free tier)
2. Crear índice:
   - Nombre: `beneficios-bancarios`
   - Dimensión: `1536` (para text-embedding-3-small)
   - Métrica: `cosine`
3. Copiar: API Key + Host del índice
4. Pegar en `.env`

**Uso en el proyecto:**
- Namespace: `beneficios-bancarios`
- Vectores: 985 (uno por beneficio)
- Búsqueda semántica top_k=15

### 🔵 Twilio (WhatsApp)

1. Crear cuenta en https://www.twilio.com/
2. Ir a Messaging > WhatsApp > Sandbox
3. Unirse al sandbox siguiendo instrucciones
4. Configurar webhook URL:
   ```
   https://api-beneficios-chile.onrender.com/webhook
   ```
   Método: POST
5. Copiar Account SID + Auth Token

> El webhook de Twilio apunta a `api.py` (FastAPI), NO a `whatsapp_bot.py`.

---

## ▶️ Ejecución paso a paso

### 1. Scrapear beneficios (genera los datos)

```bash
python scrapers.py
```

**Output esperado:**
```
==================================================
🚀 INICIANDO SCRAPING DE BENEFICIOS BANCARIOS
==================================================

📡 Scrapeando Banco de Chile (API CMS)...
✅ Banco de Chile: 229 beneficios extraídos

📡 Scrapeando Banco Falabella (API CMS v2)...
✅ Banco Falabella: 150 beneficios extraídos

📡 Scrapeando BCI (HTML)...
✅ BCI: 98 beneficios extraídos

... (15 bancos en total)

🔧 Normalizando datos...

==================================================
✅ TOTAL BENEFICIOS EXTRAÍDOS: 985
   • Banco de Chile: 229
   • Banco Falabella: 150
   • BCI: 98
   • Scotiabank: 61
   • ... (11 bancos más)
==================================================

💾 Datos guardados en: beneficios.json (985 beneficios)
💾 Datos guardados en: beneficios.csv
```

**Archivos generados:**
- `beneficios.json` — 985 beneficios (~1.2MB)
- `beneficios.csv` — mismo data para Excel/BI

### 2. (Opcional) Subir vectores a Pinecone

```bash
python upload_pinecone.py
```

**Output esperado:**
```
🚀 Subiendo beneficios a Pinecone...
📦 985 beneficios cargados
🗑️  Namespace anterior limpiado
   ✅ 50/985 vectores subidos
   ✅ 100/985 vectores subidos
   ...
   ✅ 985/985 vectores subidos

✅ COMPLETADO: 985 vectores en Pinecone
   Index: beneficios-bancarios
   Namespace: beneficios-bancarios
```

> Solo necesario si quieres usar RAG (consultas libres con IA en el bot).

### 3. Iniciar API (servidor web + bot)

```bash
uvicorn api:app --reload --port 8000
```

**Output esperado:**
```
INFO:     Started server process
INFO:     Waiting for application startup
  Cargados 985 beneficios desde beneficios.json
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Abrir en navegador

| URL | Qué es |
|-----|--------|
| `http://localhost:8000/ver` | Página web con filtros + mapa |
| `http://localhost:8000/docs` | Swagger API docs |
| `http://localhost:8000/` | Health check (JSON) |
| `http://localhost:8000/beneficios` | Todos los beneficios (JSON) |

### 5. Probar API desde terminal

```bash
# Health check
curl http://localhost:8000/

# Buscar sushi en BCI
curl "http://localhost:8000/beneficios/buscar?restaurante=sushi&banco=BCI"

# Estadísticas
curl http://localhost:8000/estadisticas

# Consultar con IA
curl -X POST http://localhost:8000/rag \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "mejores descuentos para hoy"}'
```

### 6. Probar bot sin WhatsApp

```bash
# Simular mensaje de WhatsApp
curl -X POST http://localhost:8000/webhook \
  -d "From=whatsapp:+56912345678" \
  -d "Body=hola"
```

---

## 🌐 Deploy en Render

### Paso 1: Preparar repo en GitHub

```bash
git add .
git commit -m "Ready for deploy"
git push origin main
```

### Paso 2: Crear servicio en Render

1. Ir a https://render.com → Sign in con GitHub
2. **New +** → **Web Service**
3. Conectar repo `beneficios-bancarios-chile`
4. Configurar:
   - **Name**: `api-beneficios-chile`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`

### Paso 3: Variables de entorno en Render

En el dashboard del servicio → **Environment**:

```
OPENAI_API_KEY    = sk-...
PINECONE_API_KEY  = ...
PINECONE_ENV      = us-east-1
PINECONE_INDEX    = beneficios-bancarios
PINECONE_HOST     = beneficios-bancarios-XXXXX.svc.aped-4627-b74a.pinecone.io
```

### Paso 4: Deploy automático

Cada `git push origin main` → Render despliega automáticamente (~2-3 min).

### URLs de producción

```
https://api-beneficios-chile.onrender.com/          ← API health check
https://api-beneficios-chile.onrender.com/ver        ← Página web
https://api-beneficios-chile.onrender.com/webhook    ← WhatsApp bot
https://api-beneficios-chile.onrender.com/docs       ← Swagger
```

### render.yaml (ya incluido en el repo)

```yaml
services:
  - type: web
    name: api-beneficios-chile
    runtime: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn api:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: PINECONE_API_KEY
        sync: false
      - key: PINECONE_ENV
        value: us-east-1
      - key: PINECONE_INDEX
        value: beneficios-bancarios
      - key: PINECONE_HOST
        value: beneficios-bancarios-XXXXX.svc.aped-4627-b74a.pinecone.io
```

---

## 📱 Configurar WhatsApp (Twilio)

### Con Twilio Sandbox (desarrollo/testing)

1. **Twilio Console** → Messaging → WhatsApp → Sandbox
2. Escanear QR o enviar mensaje de activación al número sandbox
3. Configurar webhook:
   - **WHEN A MESSAGE COMES IN**: `https://api-beneficios-chile.onrender.com/webhook`
   - **Method**: POST

### Para desarrollo local (ngrok)

```bash
# Terminal 1: iniciar API
uvicorn api:app --reload --port 8000

# Terminal 2: tunelizar con ngrok
ngrok http 8000
# Te da: https://abc123.ngrok-free.app

# En Twilio Sandbox: poner URL de ngrok
# https://abc123.ngrok-free.app/webhook (POST)
```

### Probar el flujo

1. Enviar "hola" al número de WhatsApp
2. Bot pregunta: ¿Qué banco(s)?
3. Responder: "Falabella, BCI"
4. Bot pregunta: ¿Qué día?
5. Responder: "viernes"
6. Bot pregunta: ¿Tipo de comida?
7. Responder: "sushi" (o "todos")
8. Bot muestra resultados + link a la web

---

## 🔄 Actualización de datos

### Proceso completo

```bash
# 1. Activar entorno
source venv/bin/activate

# 2. Re-scrapear (toma ~2-3 minutos)
python scrapers.py

# 3. (Opcional) Actualizar vectores en Pinecone
python upload_pinecone.py

# 4. Commit y push (Render despliega automáticamente)
git add beneficios.json beneficios.csv
git commit -m "Actualizar datos $(date +%d-%m-%Y)"
git push origin main

# 5. Esperar ~2-3 min para que Render despliegue
```

### Frecuencia recomendada

- **Datos (scrapers)**: cada 1-2 semanas
- **Pinecone**: cada vez que se re-scrapea
- **Documentación (.md)**: cada vez que se hacen cambios al código

---

## 🐛 Troubleshooting

### "No se ve nada en /ver"

```bash
# Verificar que beneficios.json existe y tiene datos
python -c "import json; d=json.load(open('beneficios.json')); print(f'{len(d)} beneficios')"

# Verificar que la API carga los datos
curl http://localhost:8000/ | python -m json.tool
# Debe mostrar "total_beneficios": 985
```

### "El bot no responde en WhatsApp"

1. Verificar webhook URL en Twilio → debe ser `https://api-beneficios-chile.onrender.com/webhook`
2. Verificar método → POST
3. Probar webhook directo:
   ```bash
   curl -X POST https://api-beneficios-chile.onrender.com/webhook \
     -d "From=whatsapp:+56912345678" -d "Body=hola"
   ```
4. Ver logs en Render Dashboard → servicio → Logs

### "Error 403 al scrapear"

Algunos bancos bloquean requests. Las clases scraper ya incluyen User-Agent y headers apropiados. Si falla:
```bash
# Ver qué banco falló
python scrapers.py 2>&1 | grep "❌"
```
El OrquestadorScrapers continúa con los demás bancos si uno falla.

### "Render no despliega"

1. Verificar que `requirements.txt` está actualizado
2. Ver Build Logs en Render Dashboard
3. Error común: paquete no encontrado → verificar nombre en requirements.txt

### "Los filtros no funcionan"

1. Abrir DevTools del navegador (F12) → Console
2. Buscar errores JS (rojo)
3. Verificar que `deals` tiene datos: escribir `deals.length` en console
4. Verificar que los Multi-Select (MS) se inicializaron: `bankMS.vals()`

### "El mapa no muestra markers"

- El mapa usa coordenadas aproximadas por región, NO geocoding real
- Solo muestra restaurantes que tienen `ubicacion` definida
- Si todos los markers se agrupan en un punto: es porque son de la misma región
- Zoom in para ver markers individuales

---

**Última actualización**: 15 Marzo 2026
**Versión**: v_01

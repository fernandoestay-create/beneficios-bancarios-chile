# 🚀 GUÍA COMPLETA: SISTEMA DE SCRAPING DE BENEFICIOS BANCARIOS CHILE

## 📋 ÍNDICE
1. [Requisitos](#requisitos)
2. [Instalación Local](#instalación-local)
3. [Configuración de APIs](#configuración-de-apis)
4. [Ejecución](#ejecución)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)

---

## 📦 REQUISITOS

### Software
- Python 3.9+
- Git
- pip (gestor de paquetes Python)

### Cuentas necesarias
- GitHub (para repo + Actions)
- Twilio (para WhatsApp) - OPCIONAL
- OpenAI (para ChatGPT RAG) - OPCIONAL
- Pinecone (para vectores) - OPCIONAL

---

## 🔧 INSTALACIÓN LOCAL

### PASO 1: Clonar o descargar el proyecto

```bash
# Si tienes Git
git clone https://github.com/tuusuario/beneficios-bancarios.git
cd beneficios-bancarios

# O descargar ZIP y extraer
unzip beneficios-bancarios.zip
cd beneficios-bancarios
```

### PASO 2: Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### PASO 3: Instalar dependencias

```bash
# Dependencias básicas
pip install requests beautifulsoup4 lxml

# Para API REST
pip install fastapi uvicorn

# Para WhatsApp Bot
pip install twilio flask

# Para RAG (OpenAI + Pinecone)
pip install openai pinecone-client

# Todas juntas
pip install -r requirements.txt
```

### PASO 4: Estructura de carpetas

```
beneficios-bancarios/
├── scrapers.py              # Scrapers de Banco Chile + Falabella
├── api.py                   # API REST FastAPI
├── whatsapp_bot.py          # Bot WhatsApp
├── requirements.txt         # Dependencias
├── .env.example             # Variables de entorno ejemplo
├── .github/
│   └── workflows/
│       └── scraper.yml      # GitHub Actions
├── beneficios.json          # Base de datos (generado)
└── README.md
```

---

## ⚙️ CONFIGURACIÓN DE APIs

### 🟦 TWILIO (WhatsApp Bot)

#### 1. Crear cuenta
- Ir a https://www.twilio.com/
- Crear cuenta gratuita
- Verificar número de teléfono

#### 2. Obtener credenciales
```
Dashboard > Account > API Keys & Tokens
Copiar:
- Account SID
- Auth Token
```

#### 3. Configurar WhatsApp Sandbox
```
Messaging > WhatsApp > Sandbox
Guardar número: whatsapp:+XXXXXXXXXXXX
```

#### 4. Variables de entorno
```bash
# Crear archivo .env
cat > .env << EOF
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcn-...
EOF
```

#### 5. Cargar en Python
```python
from dotenv import load_dotenv
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
```

### 🟪 OPENAI (ChatGPT RAG)

#### 1. Crear API Key
- https://platform.openai.com/api-keys
- Crear nueva key
- Copiar y guardar

#### 2. Agregar a .env
```bash
OPENAI_API_KEY=sk-your-key-here
```

#### 3. Usar en código
```python
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "tu pregunta"}]
)
```

### 🟦 PINECONE (Vector Database)

#### 1. Crear cuenta
- https://www.pinecone.io/
- Crear proyecto gratuito

#### 2. Obtener credenciales
```
Settings > API Keys
Copiar:
- API Key
- Environment (p.ej: gcp-starter)
```

#### 3. Script de upload
```python
# scripts/upload_pinecone.py
import pinecone
from openai.embeddings_utils import get_embedding

pinecone.init(api_key=os.getenv("PINECONE_API_KEY"))
index = pinecone.Index("beneficios")

for beneficio in beneficios_db:
    embedding = get_embedding(beneficio.restaurante)
    index.upsert([(beneficio.id, embedding)])
```

---

## ▶️ EJECUCIÓN

### 1️⃣ Ejecutar Scrapers

```bash
python scrapers.py
```

**Output esperado:**
```
==================================================
🚀 INICIANDO SCRAPING DE BENEFICIOS BANCARIOS
==================================================

📡 Scrapeando Banco de Chile...
✅ Encontrados: 229 beneficios disponibles
🔍 Procesando 229 beneficios...
   ✓ 10/229
   ✓ 20/229
   ...
✅ Scraping completado: 229 beneficios

📡 Scrapeando Banco Falabella...
✅ Restaurantes (71)
🔍 Procesando 71 elementos...
✅ Scraping completado: 71 beneficios

==================================================
✅ TOTAL BENEFICIOS EXTRAÍDOS: 300
   • Banco de Chile: 229
   • Banco Falabella: 71
==================================================
```

**Archivos generados:**
- `beneficios.json` - Base de datos completa
- `beneficios.csv` - Backup en CSV

### 2️⃣ Ejecutar API REST

```bash
python api.py
```

**Output esperado:**
```
🚀 Iniciando API en http://localhost:8000
📖 Documentación en http://localhost:8000/docs
```

**Pruebas rápidas:**
```bash
# Health check
curl http://localhost:8000/

# Listar beneficios
curl http://localhost:8000/beneficios

# Buscar
curl "http://localhost:8000/beneficios/buscar?restaurante=starbucks"

# Estadísticas
curl http://localhost:8000/estadisticas

# RAG Query
curl -X POST http://localhost:8000/rag \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Qué descuentos hay los lunes?"}'
```

### 3️⃣ Ejecutar Bot WhatsApp

```bash
python whatsapp_bot.py
```

**Output esperado:**
```
🚀 Cargando beneficios...
✅ Cargados 300 beneficios
📱 Bot WhatsApp iniciado
🌐 Servidor en http://localhost:5000
🔗 Webhook en http://localhost:5000/webhook
```

**Para tunelizar a internet (desarrollo):**
```bash
# Instalar ngrok
# https://ngrok.com/download

ngrok http 5000
# Te da una URL pública: https://xxxx-xx-xxx-xx-x.ngrok.io

# En Twilio Sandbox:
# Webhook URL: https://xxxx-xx-xxx-xx-x.ngrok.io/webhook
```

**Probar en WhatsApp:**
1. Ir a https://www.twilio.com/console/sms/whatsapp/learn
2. Seguir instrucciones para unirse al sandbox
3. Enviar mensaje a tu número de Twilio
4. Probar comandos:
   - `/`
   - `/restaurante starbucks`
   - `/banco "Banco de Chile"`
   - `/dia lunes`
   - `/stats`

---

## 🌐 DEPLOYMENT

### En Render (Gratuito)

#### 1. Preparar proyecto

```bash
# Crear requirements.txt
pip freeze > requirements.txt

# Crear Procfile
cat > Procfile << EOF
web: python api.py
worker: python whatsapp_bot.py
EOF

# Crear render.yaml
cat > render.yaml << EOF
services:
  - type: web
    name: api-beneficios
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python api.py"
    envVars:
      - key: OPENAI_API_KEY
        sync: false

  - type: web
    name: whatsapp-bot
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python whatsapp_bot.py"
    envVars:
      - key: TWILIO_ACCOUNT_SID
        sync: false
      - key: TWILIO_AUTH_TOKEN
        sync: false
      - key: TWILIO_WHATSAPP_NUMBER
        sync: false
EOF
```

#### 2. Subir a GitHub
```bash
git add .
git commit -m "Prep for Render deployment"
git push origin main
```

#### 3. Deployer en Render
- Ir a https://render.com
- Crear cuenta
- "New +" > "Web Service"
- Conectar GitHub repo
- Configurar variables de entorno
- Deploy

**URLs después del deploy:**
- API: `https://api-beneficios-xxxx.onrender.com`
- Bot: `https://whatsapp-bot-xxxx.onrender.com`

### En GitHub Actions (Scraping automático)

#### 1. Copiar workflow
```bash
mkdir -p .github/workflows
cp .github_workflows_scraper.yml .github/workflows/scraper.yml
```

#### 2. Subir a GitHub
```bash
git add .github/workflows/scraper.yml
git commit -m "Add daily scraper workflow"
git push origin main
```

#### 3. Configurar secretos
En GitHub:
- Settings > Secrets and variables > Actions
- Agregar secretos:
  - `PINECONE_API_KEY`
  - `OPENAI_API_KEY`

#### 4. El workflow se ejecutará automáticamente:
- **Diariamente a las 5 AM UTC** (2 AM Chile)
- **Manualmente**: Actions > Scraping Diario > Run workflow

---

## 🐛 TROUBLESHOOTING

### ❌ Error: "ModuleNotFoundError: No module named 'requests'"

```bash
pip install requests beautifulsoup4
```

### ❌ Error: "Connection refused" en puerto 5000/8000

```bash
# El puerto ya está en uso. Cambiar en código:
# api.py: uvicorn.run(app, host="0.0.0.0", port=8001)
# whatsapp_bot.py: app.run(debug=True, port=5001)
```

### ❌ Error: "403 Forbidden" al hacer scrape

Algunos sitios bloquean scrapers. Soluciones:

```python
# 1. Cambiar User-Agent
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# 2. Usar delays
import time
time.sleep(2)

# 3. Usar proxies (si está disponible)
proxies = {"https": "https://proxy.example.com:8080"}
response = session.get(url, proxies=proxies)
```

### ❌ WhatsApp: "No estoy recibiendo mensajes"

1. Verificar que el webhook URL esté correcto en Twilio
2. Usar ngrok para tunelar (desarrollo)
3. Revisar logs: `twilio logs`
4. Probar el webhook:
   ```bash
   curl -X POST http://localhost:5000/webhook \
     -d "From=whatsapp:+56912345678" \
     -d "Body=/help"
   ```

### ❌ GitHub Actions: Workflow no ejecuta

1. Verificar que `.github/workflows/scraper.yml` exista
2. Ir a Actions tab y habilitar workflows
3. Ejecutar manualmente primero: "Run workflow"
4. Revisar logs de ejecución

---

## 📈 MONITOREO

### Ver logs en Render
```bash
# API
Render Dashboard > api-beneficios > Logs

# Bot
Render Dashboard > whatsapp-bot > Logs
```

### Ver ejecuciones de GitHub Actions
```
GitHub > Actions > Scraping Diario > Ver workflow
```

### Monitorear API
```bash
# Health check
curl -s http://api-beneficios-xxxx.onrender.com/ | jq

# Estadísticas
curl -s http://api-beneficios-xxxx.onrender.com/estadisticas | jq
```

---

## 🔐 SEGURIDAD

### En Producción:
```python
# 1. NO guardar secrets en código
import os
api_key = os.environ.get("API_KEY")

# 2. Usar .env solo en desarrollo
from dotenv import load_dotenv
load_dotenv()  # Solo en desarrollo

# 3. En Render/GitHub: usar Secrets

# 4. Validar entrada de usuarios
from fastapi import Query
@app.get("/search")
def search(q: str = Query(..., min_length=1, max_length=100)):
    ...

# 5. Rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.get("/beneficios")
@limiter.limit("100/minute")
def get_beneficios(request: Request):
    ...
```

---

## 📞 SOPORTE

### Recursos útiles:
- [Documentación FastAPI](https://fastapi.tiangolo.com/)
- [Documentación Twilio](https://www.twilio.com/docs)
- [Documentación OpenAI](https://platform.openai.com/docs)
- [Documentación Pinecone](https://docs.pinecone.io/)

### Contacto:
- Email: soporte@beneficiosbancarios.cl
- Issues: GitHub Issues
- Discussions: GitHub Discussions

---

**Última actualización**: Marzo 2026
**Versión**: 1.0.0
**Autores**: Equipo de Desarrollo

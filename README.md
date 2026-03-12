# 🏦 SISTEMA DE SCRAPING DE BENEFICIOS BANCARIOS CHILE

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Un sistema completo para **scrapear, almacenar y consultar** descuentos bancarios en restaurantes de Chile mediante **API REST, WhatsApp Bot y ChatGPT RAG**.

## 📸 Demo Rápida

```
SCRAPERS DIARIOS
    ↓
Banco de Chile (229 beneficios)
Banco Falabella (71 beneficios)
    ↓
JSON + Pinecone + GitHub
    ↓
🔹 API REST (FastAPI)
    GET /beneficios
    GET /beneficios/buscar?banco=Falabella
    POST /rag (ChatGPT)

🔹 BOT WhatsApp
    /restaurante starbucks
    /banco "Banco de Chile"
    /dia lunes
    
🔹 DASHBOARD (opcional)
    Mostrar top restaurantes
    Estadísticas en tiempo real
```

---

## ✨ CARACTERÍSTICAS

### 🤖 Scrapers Inteligentes
- ✅ **Banco de Chile**: 229+ restaurantes
- ✅ **Banco Falabella**: 71+ restaurantes  
- ✅ Actualización automática diaria con GitHub Actions
- ✅ Manejo de JavaScript y sitios complejos

### 🔌 API REST
- ✅ FastAPI con OpenAPI docs
- ✅ Búsqueda avanzada (banco, restaurante, día)
- ✅ Integración ChatGPT RAG
- ✅ Paginación y filtros
- ✅ CORS habilitado

### 💬 Bot WhatsApp
- ✅ Búsqueda por restaurante
- ✅ Filtrar por banco y día
- ✅ Ver top restaurantes
- ✅ Estadísticas en tiempo real
- ✅ Menú interactivo

### 🧠 RAG + IA
- ✅ Integración OpenAI ChatGPT
- ✅ Vectorización con Pinecone
- ✅ Respuestas contextuales
- ✅ Búsqueda semántica

### ⚡ Deployment
- ✅ GitHub Actions para scraping automático
- ✅ Deploy en Render (gratuito)
- ✅ CI/CD completo

---

## 🚀 INICIO RÁPIDO (5 minutos)

### 1. Descargar archivos
```bash
git clone https://github.com/tuusuario/beneficios-bancarios.git
cd beneficios-bancarios
```

### 2. Instalar dependencias
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# o
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 3. Ejecutar scrapers
```bash
python scrapers.py
```

Verás:
```
🚀 INICIANDO SCRAPING...
📡 Scrapeando Banco de Chile...
✅ 229 beneficios

📡 Scrapeando Banco Falabella...
✅ 71 beneficios

✅ TOTAL: 300 BENEFICIOS
```

### 4. Iniciar API
```bash
python api.py
```

Abre: http://localhost:8000/docs

### 5. (Opcional) WhatsApp Bot
```bash
python whatsapp_bot.py
```

---

## 📚 ESTRUCTURA DEL PROYECTO

```
beneficios-bancarios/
├── 📄 scrapers.py              # Scrapers (Banco Chile + Falabella)
├── 📄 api.py                   # API REST FastAPI + RAG
├── 📄 whatsapp_bot.py          # Bot WhatsApp/Twilio
├── 📄 requirements.txt          # Dependencias Python
│
├── 📁 .github/workflows/
│   └── scraper.yml             # GitHub Actions (cron diario)
│
├── 📄 SETUP_GUIDE.md           # Guía detallada de instalación
├── 📄 README.md                # Este archivo
│
├── 📁 scripts/ (opcional)
│   ├── upload_pinecone.py      # Upload a Pinecone
│   ├── generate_dashboard.py   # Dashboard HTML
│   └── sync_github.py          # Sync con GitHub
│
├── beneficios.json             # Base de datos (generado)
└── beneficios.csv              # Backup CSV (generado)
```

---

## 🔌 ENDPOINTS API

### Listar beneficios
```bash
curl http://localhost:8000/beneficios?limit=10
```

### Buscar
```bash
curl "http://localhost:8000/beneficios/buscar?restaurante=starbucks&banco=Falabella&min_descuento=30"
```

### Estadísticas
```bash
curl http://localhost:8000/estadisticas
```

### Consultar con IA
```bash
curl -X POST http://localhost:8000/rag \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Qué restaurantes tienen 40% descuento?"}'
```

### Top restaurantes
```bash
curl http://localhost:8000/restaurantes/top?limit=10
```

---

## 💬 COMANDOS BOT WhatsApp

```
/              - Mostrar menú
/restaurante   - Buscar por nombre
  /restaurante starbucks

/banco         - Ver beneficios de banco
  /banco "Banco de Chile"

/dia           - Ver descuentos del día
  /dia lunes

/top           - Top 5 restaurantes
/stats         - Estadísticas generales
```

---

## ⚙️ CONFIGURACIÓN

### Variables de entorno (.env)
```bash
# Twilio WhatsApp
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890

# OpenAI
OPENAI_API_KEY=sk-your-api-key

# Pinecone
PINECONE_API_KEY=your_api_key
PINECONE_ENV=gcp-starter
```

### GitHub Secrets (Para Actions)
```
PINECONE_API_KEY=***
OPENAI_API_KEY=***
```

---

## 📊 DATOS & ESTADÍSTICAS

### Volumen actual
```
Total Beneficios:     300+
Bancos Incluidos:     2 (Banco Chile, Falabella)
Restaurantes únicos:  250+
Descuento máximo:     40-50%
Descuento promedio:   25-30%
```

### Actualización
- 🔄 **Diaria** a las 5 AM UTC (2 AM Chile)
- 📤 Backup automático en GitHub
- ☁️ Sincronización con Pinecone (opcional)

---

## 🌐 DEPLOYMENT

### Opción 1: Render (Recomendado - Gratuito)
```bash
# Ver: SETUP_GUIDE.md > Deployment > Render
```

**Resultado:**
- API: `https://api-beneficios-xxxx.onrender.com`
- Bot: `https://bot-beneficios-xxxx.onrender.com`

### Opción 2: Vercel
```bash
# Funciona solo para API sin servidores
vercel deploy
```

### Opción 3: Heroku/Railway
```bash
# Ver guía de setup
```

---

## 🧪 TESTING

```bash
# Instalar pytest
pip install pytest

# Ejecutar tests
pytest tests/

# Coverage
pytest --cov=.
```

---

## 🐛 TROUBLESHOOTING

### "No se conecta a Banco de Chile"
```python
# Aumentar timeout
session.get(url, timeout=20)

# O usar proxy
proxies = {"https": "http://proxy:8080"}
session.get(url, proxies=proxies)
```

### "WhatsApp no recibe mensajes"
```bash
# 1. Verificar webhook en Twilio
# 2. Usar ngrok para tunelizar
ngrok http 5000

# 3. Copiar URL de ngrok a Twilio webhook
```

### "Error de rate limit"
```python
import time
time.sleep(2)  # Agregar delay entre requests
```

---

## 📈 ROADMAP

### ✅ COMPLETADO
- [x] Scrapers Banco Chile + Falabella
- [x] API REST FastAPI
- [x] Bot WhatsApp
- [x] GitHub Actions
- [x] Deploy Render

### 🚧 EN PROGRESO
- [ ] Dashboard web
- [ ] Más bancos (Santander, Itaú, BCI)
- [ ] Filtros avanzados (región, ciudad)
- [ ] Notificaciones push
- [ ] Mobile app

### 📋 PLANEADO
- [ ] Integración con Telegram
- [ ] Telegram Bot
- [ ] Cache distribuido (Redis)
- [ ] Analytics avanzados
- [ ] Recomendaciones personalizadas

---

## 🤝 CONTRIBUIR

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📜 LICENCIA

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE`.

---

## 📞 CONTACTO

- 💬 **Issues**: GitHub Issues
- 💌 **Email**: soporte@beneficiosbancarios.cl
- 🐦 **Twitter**: @BeneficiosChile

---

## ⭐ CRÉDITOS

Desarrollado con ❤️ para ayudarte a encontrar los mejores descuentos bancarios en Chile.

```
Banco de Chile   📊
Banco Falabella  💳
FastAPI         🚀
OpenAI          🧠
Pinecone        🔍
Twilio          💬
```

---

**Última actualización**: Marzo 2026  
**Versión**: 1.0.0  
**Estado**: ✅ Producción

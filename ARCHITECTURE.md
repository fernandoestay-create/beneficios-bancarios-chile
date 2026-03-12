# 🏗️ ARQUITECTURA DEL SISTEMA

## 📐 DIAGRAMA COMPLETO

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FUENTES DE DATOS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  🌐 Banco de Chile              🌐 Banco Falabella                       │
│  sitiospublicos.bancochile.cl   www.bancofalabella.cl/descuentos         │
│  /sabores/restaurantes          /restaurantes                            │
│                                                                           │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAPA DE SCRAPING                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────┐          ┌──────────────────────┐             │
│  │ ScraperBancoChile    │          │ ScraperBancoFalabella│             │
│  ├──────────────────────┤          ├──────────────────────┤             │
│  │ • HTML Parser        │          │ • HTML Parser        │             │
│  │ • Parseador datos    │          │ • Parseador datos    │             │
│  │ • Validación         │          │ • Validación         │             │
│  └──────────┬───────────┘          └────────────┬─────────┘             │
│             │                                   │                       │
│             └───────────────┬───────────────────┘                       │
│                             ▼                                           │
│                   ┌──────────────────────┐                              │
│                   │  OrquestadorScrapers │                              │
│                   ├──────────────────────┤                              │
│                   │ • Ejecuta todos      │                              │
│                   │ • Normaliza datos    │                              │
│                   │ • Valida resultados  │                              │
│                   └──────────┬───────────┘                              │
│                              │                                          │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ALMACENAMIENTO DE DATOS                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  📄 beneficios.json      💾 GitHub Repo      🔍 Pinecone Vector DB     │
│  ├─ 300+ beneficios      ├─ Backup          ├─ Embeddings            │
│  ├─ Estructura JSON      ├─ Versión         ├─ Búsqueda semántica    │
│  └─ Base local           └─ Control         └─ RAG ready             │
│                                                                           │
│  📊 Esquema de datos:                                                    │
│  {                                                                       │
│    "id": "banchile_starbucks",                                          │
│    "banco": "Banco de Chile",                                           │
│    "restaurante": "Starbucks",                                          │
│    "descuento_valor": 30,                                               │
│    "descuento_tipo": "porcentaje",                                      │
│    "descuento_texto": "30% dto.",                                       │
│    "dias_validos": ["lunes", "martes"],                                 │
│    "presencial": true,                                                  │
│    "fecha_scrape": "2026-03-12T02:15:00Z"                              │
│  }                                                                       │
│                                                                           │
└──────────┬──────────────┬──────────────────────────────┬────────────────┘
           │              │                              │
           ▼              ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        CAPA DE APLICACIÓN                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │   API REST          │  │  BOT WhatsApp    │  │  RAG Chatbot     │   │
│  │   (FastAPI)         │  │  (Twilio/Flask)  │  │  (OpenAI)        │   │
│  ├─────────────────────┤  ├──────────────────┤  ├──────────────────┤   │
│  │ GET /beneficios     │  │ /restaurante     │  │ POST /rag        │   │
│  │ GET /buscar         │  │ /banco           │  │ Preguntas libres │   │
│  │ GET /estadisticas   │  │ /dia             │  │ Respuestas IA    │   │
│  │ GET /top            │  │ /stats           │  │ Contexto         │   │
│  │ POST /rag           │  │                  │  │                  │   │
│  │                     │  │ Interactivo      │  │ Integrado en API │   │
│  │ Documentación:      │  │ Amigable         │  │ y Bot            │   │
│  │ /docs               │  │ 24/7             │  │                  │   │
│  └──────────┬──────────┘  └────────┬─────────┘  └────────┬─────────┘   │
│             │                      │                     │              │
└─────────────┼──────────────────────┼─────────────────────┼──────────────┘
              │                      │                     │
              ▼                      ▼                     ▼
    ┌────────────────┐      ┌──────────────┐     ┌──────────────────┐
    │ HTTP Requests  │      │ WhatsApp Msgs│     │ OpenAI API       │
    │ JSON/REST      │      │ Twilio Queue │     │ GPT-3.5-turbo    │
    └────────┬───────┘      └──────┬───────┘     └────────┬─────────┘
             │                     │                      │
             └─────────────────────┴──────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │    USUARIOS FINALES      │
                    ├──────────────────────────┤
                    │ 🌐 Web Browser           │
                    │ 💬 WhatsApp              │
                    │ 🤖 Chat Integrations     │
                    │ 📱 Mobile Apps           │
                    └──────────────────────────┘
```

---

## 🔄 FLUJOS DE DATOS

### 1️⃣ FLUJO DE SCRAPING (Diario - 5 AM UTC)

```
GitHub Actions Trigger (cron: 0 5 * * *)
    │
    ▼
Python Environment Setup
    │
    ▼
┌─────────────────────────────────┐
│ scrapers.py                     │
│ ├─ ScraperBancoChile()          │
│ │  └─ GET bancochile.cl         │
│ │     └─ Parse HTML → JSON      │
│ ├─ ScraperBancoFalabella()      │
│ │  └─ GET bancofalabella.cl     │
│ │     └─ Parse HTML → JSON      │
│ └─ OrquestadorScrapers()        │
│    └─ Merge & Normalize         │
└────────┬────────────────────────┘
         │
         ▼
   Validate Data
         │
         ▼
┌─────────────────────────────────┐
│ beneficios.json (300+ items)    │
│ beneficios.csv (backup)         │
└─────────┬───────────────────────┘
          │
          ▼
   Git Commit & Push
          │
          ▼
   GitHub Repo Updated
          │
          ▼
   (Opcional) Pinecone Upload
```

### 2️⃣ FLUJO DE CONSULTA API

```
User Request
    │
    ▼
GET http://localhost:8000/beneficios/buscar?restaurante=starbucks
    │
    ▼
┌──────────────────────────────────┐
│ FastAPI Endpoint                 │
│ ├─ Validate parameters           │
│ ├─ Search in memory DB           │
│ └─ Filter results                │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ beneficios.json (in memory)      │
│ - Beneficio 1 (match)            │
│ - Beneficio 2 (match)            │
│ - Beneficio 3 (match)            │
└────────┬─────────────────────────┘
         │
         ▼
    Paginación
    (skip/limit)
         │
         ▼
┌──────────────────────────────────┐
│ JSON Response                    │
│ ├─ Status: 200                   │
│ ├─ Data: [...]                   │
│ └─ Timestamp                     │
└────────┬─────────────────────────┘
         │
         ▼
    Browser/Client
```

### 3️⃣ FLUJO DE BOT WhatsApp

```
WhatsApp User Message
    │
    ▼
Twilio Webhook
    │
    ▼
POST /webhook (whatsapp_bot.py)
    │
    ▼
┌──────────────────────────────────┐
│ Procesar Comando                 │
│ ├─ Parse comando                 │
│ ├─ Extraer parámetros            │
│ └─ Validar entrada               │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Ejecutar búsqueda                │
│ ├─ beneficios.json (in memory)   │
│ ├─ Filter by restaurante/banco   │
│ └─ Limit results (3)             │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Formatear respuesta              │
│ ├─ Markdown format               │
│ ├─ Emojis                        │
│ └─ Límite 1600 chars             │
└────────┬─────────────────────────┘
         │
         ▼
  Twilio SMS API
         │
         ▼
  WhatsApp Delivery
         │
         ▼
  User receives message
```

### 4️⃣ FLUJO RAG (ChatGPT)

```
User Question
    │
    ▼
POST /rag {"pregunta": "..."}
    │
    ▼
┌──────────────────────────────────┐
│ Buscar beneficios relevantes     │
│ ├─ beneficios.json               │
│ ├─ Filter por contexto           │
│ └─ Top 5-10 resultados           │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Construir prompt para IA         │
│ ├─ System: "Eres experto..."     │
│ ├─ Context: beneficios           │
│ └─ User: pregunta original       │
└────────┬─────────────────────────┘
         │
         ▼
  OpenAI API Call
  (GPT-3.5-turbo)
         │
         ▼
┌──────────────────────────────────┐
│ Response JSON                    │
│ ├─ Pregunta original             │
│ ├─ Respuesta IA                  │
│ ├─ Beneficios encontrados        │
│ └─ Timestamp                     │
└────────┬─────────────────────────┘
         │
         ▼
  Retornar a usuario
```

---

## 🏗️ COMPONENTES PRINCIPALES

### Modelo de datos (Beneficio)
```python
@dataclass
class Beneficio:
    id: str                      # UUID único
    banco: str                   # "Banco de Chile" / "Banco Falabella"
    tarjeta: str                 # "Tarjetas del Chile" / "CMR"
    restaurante: str             # "Starbucks"
    descuento_valor: float       # 30
    descuento_tipo: str          # "porcentaje"
    descuento_texto: str         # "30% dto"
    dias_validos: List[str]      # ["lunes", "martes"]
    horario_inicio: str          # "11:00"
    horario_fin: str             # "22:00"
    valido_desde: str            # "2025-06-01"
    valido_hasta: str            # "2025-08-31"
    ubicacion: str               # "Región Metropolitana"
    ciudad: str                  # "Santiago"
    locales: List[str]           # ["Las Condes", "Providencia"]
    compra_minima: int           # 15000
    tope_descuento: int          # 50000
    restricciones_texto: str     # "No aplica propina"
    online: bool                 # true/false
    presencial: bool             # true/false
    fecha_scrape: str            # ISO timestamp
    url_fuente: str              # URL de origen
    activo: bool                 # true/false
```

---

## 📊 VOLUMEN DE DATOS

### Almacenamiento actual
```
Beneficios por banco:
├─ Banco de Chile:      229 beneficios
├─ Banco Falabella:      71 beneficios
└─ TOTAL:              300+ beneficios

Datos por beneficio:
├─ Restaurante:         250+ únicos
├─ Días válidos:        7 días
├─ Descuentos:          10-50%
└─ Tamaño JSON:         ~150 KB

Con historial 1 año:
├─ Registros diarios:   300+ × 365
├─ Total registros:     ~110,000
└─ Tamaño estimado:     ~50 MB
```

---

## 🔐 SEGURIDAD

```
┌─────────────────────────────────────┐
│      NIVELES DE SEGURIDAD           │
├─────────────────────────────────────┤
│                                     │
│  Nivel 1: Input Validation          │
│  ├─ Query parameters validados      │
│  ├─ Length limits (max_length)      │
│  └─ Type checking (Pydantic)        │
│                                     │
│  Nivel 2: API Keys                  │
│  ├─ Variables de entorno            │
│  ├─ Secrets en GitHub               │
│  └─ No hardcoded credentials        │
│                                     │
│  Nivel 3: Rate Limiting             │
│  ├─ 100 requests/min por IP         │
│  └─ Slowapi middleware              │
│                                     │
│  Nivel 4: CORS                      │
│  ├─ Whitelist de origins            │
│  └─ Control de métodos              │
│                                     │
│  Nivel 5: HTTPS                     │
│  ├─ SSL/TLS en producción           │
│  └─ Render auto-HTTPS               │
│                                     │
└─────────────────────────────────────┘
```

---

## 🚀 ESCALABILIDAD

### Horizontal Scaling
```
                    Load Balancer
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
    API Server 1     API Server 2     API Server 3
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
                    Shared Database
                  (PostgreSQL/MongoDB)
```

### Vertical Scaling
```
Current (Single Instance):
├─ 1 API server (512MB RAM)
├─ In-memory beneficios.json
├─ ~500 requests/sec capacity
└─ Cost: $5-10/mes

Escalado:
├─ API: 2GB RAM + PostgreSQL
├─ Cache: Redis (5GB)
├─ DB: Pinecone vectors
├─ ~5000 requests/sec capacity
└─ Cost: $50-100/mes
```

---

## 📈 MONITOREO Y LOGS

```
Monitoreo por componente:

1. GitHub Actions
   └─ Logs: Actions > Scraping Diario > Workflow

2. Render API
   └─ Logs: Dashboard > api-beneficios > Logs
   
3. Render Bot
   └─ Logs: Dashboard > whatsapp-bot > Logs

4. Pinecone (opcional)
   └─ Logs: Console > Indexes > Logs

5. OpenAI API
   └─ Logs: Platform > Usage > Logs
```

---

**Diagrama actualizado**: Marzo 2026  
**Versión**: 1.0.0

# 🍽️ Beneficios Bancarios Chile

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Deploy](https://img.shields.io/badge/Render-Deployed-success.svg)](https://api-beneficios-chile.onrender.com/ver)

Sistema completo que **scrapea descuentos bancarios en restaurantes de Chile** y los expone a través de una **página web interactiva**, un **bot de WhatsApp con IA**, y una **API REST**.

> **v_01** — 985 beneficios · 15 bancos · Página web con filtros + mapa · Bot WhatsApp conversacional

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                  SCRAPERS  (scrapers.py)                     │
│   15 bancos → requests + BeautifulSoup → Beneficio objects   │
│   Normalización: fechas, regiones, comunas, textos           │
│   Output: beneficios.json (985 dctos) + beneficios.csv       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    API REST  (api.py)                         │
│   FastAPI + Uvicorn                                          │
│                                                              │
│   ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│   │  Página Web  │  │  Bot WhatsApp │  │  API JSON         │  │
│   │  GET /ver    │  │  POST /webhook│  │  GET /beneficios  │  │
│   │  Filtros     │  │  Twilio       │  │  POST /rag        │  │
│   │  Tarjetas    │  │  3 pasos      │  │  GET /bancos      │  │
│   │  Mapa        │  │  + RAG (IA)   │  │  GET /estadisticas│  │
│   └─────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Pinecone      OpenAI       Twilio
         (vectores)   (GPT-4o-mini) (WhatsApp)
```

---

## 📊 Estado actual

| Métrica | Valor |
|---------|-------|
| Beneficios activos | **985** |
| Bancos scrapeados | **15** |
| Restaurantes únicos | **~700+** |
| Mejor descuento | **50%** |
| Regiones cubiertas | **16** |

---

## 🏦 Bancos scrapeados (15)

| # | Banco | Método | Beneficios |
|---|-------|--------|------------|
| 1 | Banco de Chile | API CMS interna | ~200 |
| 2 | Banco Falabella | API CMS v2 | ~150 |
| 3 | BCI | HTML scraping | ~100 |
| 4 | Banco Itaú | API JSON | ~50 |
| 5 | Scotiabank | JS embebido (arrays) | ~61 |
| 6 | Santander | HTML scraping | ~80 |
| 7 | Banco Consorcio | HTML scraping | ~40 |
| 8 | BancoEstado | API/HTML | ~60 |
| 9 | Banco Security | HTML scraping | ~50 |
| 10 | Banco Ripley | HTML scraping | ~40 |
| 11 | Entel | HTML scraping | ~30 |
| 12 | Tenpo | API/HTML | ~20 |
| 13 | Lider BCI | HTML scraping | ~25 |
| 14 | Banco BICE | HTML scraping | ~30 |
| 15 | Mach | HTML scraping | ~20 |

Cada scraper extrae: restaurante, descuento (% y texto), días válidos, ubicación, dirección, comuna, imagen, link, vigencia, restricciones, modalidad (presencial/online).

---

## 📂 Estructura del proyecto

```
beneficios-bancarios-chile/
├── api.py                  # FastAPI: API + página web + bot WhatsApp (1586 líneas)
├── scrapers.py             # 15 scrapers + modelo Beneficio + Orquestador (3162 líneas)
├── whatsapp_bot.py          # Bot WhatsApp alternativo (Flask, sin IA) (239 líneas)
├── upload_pinecone.py       # Sube vectores a Pinecone para RAG (106 líneas)
├── beneficios.json          # Data scrapeada (985 beneficios, ~1.2MB)
├── beneficios.csv           # Mismo data en CSV
├── render.yaml              # Config deploy Render (2 servicios)
├── requirements.txt         # Dependencias Python
├── DOCUMENTACION_V01.md     # Documentación técnica detallada
└── .env                     # Variables de entorno (no en Git)
```

---

## 🌐 Página Web (`/ver`)

Página interactiva server-rendered (SPA embebida en api.py).

### Layout

```
┌──────────────────────────────────────────────────────┐
│   Hero: título + stats (total, bancos, mejor dcto)   │
├────────────────┬─────────────────────────────────────┤
│   FILTROS      │   [🍽️ Tarjetas]  [📍 Mapa]          │
│                │                                     │
│  🔍 Buscar     │   Vista Tarjetas:                   │
│  💳 Banco      │    Summary bar (logos clickeables)  │
│  📅 Día        │    Grid 2 columnas de cards         │
│  📍 Zona       │    Imagen, dcto, banco, días, link  │
│  🏘️ Comuna     │                                     │
│  💰 Dcto mín.  │   Vista Mapa:                       │
│  🏪 Modalidad  │    Mapa Leaflet con markers         │
│  ↕️ Ordenar    │    Coloreados por banco              │
│                │    Popups con detalle                │
│  [Limpiar]     │                                     │
└────────────────┴─────────────────────────────────────┘
```

### Filtros disponibles

| Filtro | Tipo | Detalle |
|--------|------|---------|
| Buscar | Texto libre | Busca en restaurante, banco, descripción, dirección |
| Banco | Multi-select | Dropdown con checkboxes, tags, búsqueda interna |
| Día | 7 círculos + "Todos" | L M X J V S D, multi-selección |
| Zona | Multi-select | Regiones de Chile. Metropolitana aparece primero |
| Comuna | Multi-select | Solo visible si Zona = Metropolitana |
| Descuento mínimo | Slider | 0% a 50% |
| Modalidad | Chips | Todas / Presencial / Online |
| Ordenar | Dropdown | Mayor dcto / Menor dcto / Nombre / Banco |

**Un solo panel de filtros** controla ambas vistas (tarjetas y mapa).

### Componente Multi-Select (JS)

Clase `MS` custom — genera dropdowns con checkboxes, tags removibles y búsqueda interna:

```javascript
const bankMS = new MS('bankMS', bankOpts, 'Todos los bancos');
bankMS.vals();   // → ["BCI", "Scotiabank"] o null
bankMS.reset();  // limpia selección
```

### Mapa

- **Leaflet** con tiles CARTO (light)
- Markers circulares coloreados por banco con % de descuento
- Popups con: nombre, banco, descuento, dirección, link
- Coordenadas aproximadas por región (no geocoding real)

---

## 🤖 Bot WhatsApp

El bot funciona vía Twilio en el endpoint `POST /webhook` de api.py.

### Flujo conversacional (3 pasos)

```
👤 "hola"
🤖 "¿Qué banco(s) tienes?"
   Ej: Falabella, BCI o "todos"
   (lista los 15 bancos disponibles)

👤 "Falabella, BCI"
🤖 "✅ Banco(s): Falabella, BCI"
   "¿Qué día?"
   Ej: lunes, viernes, hoy o "todos"

👤 "viernes"
🤖 "✅ Día: Viernes"
   "¿Qué tipo de comida?"
   Ej: sushi, pizza, italiana o "todos"

👤 "sushi"
🤖 🍽️ 12 descuentos encontrados
   💳 Falabella, BCI | 📅 Viernes | 🍕 sushi

   🏦 BCI (5 dctos)
     • Sushi Express — 30% dcto.
     • Sushi Home — 40% dcto.

   🏦 Banco Falabella (7 dctos)
     • Sushi Master — 25% dcto.
     ...y 5 más

   📋 Ver todos: https://api-beneficios-chile.onrender.com/ver?dia=viernes&q=sushi
```

### Comandos rápidos

| Comando | Qué hace |
|---------|----------|
| `hola` / `hi` / `inicio` | Inicia flujo conversacional de 3 preguntas |
| `/top` | Top 5 restaurantes por descuento |
| `/stats` | Estadísticas generales |
| Cualquier texto libre | Consulta con IA (RAG) |

### Consulta libre con IA (RAG)

Si el usuario escribe algo fuera del flujo (ej: *"donde comer sushi con descuento hoy"*):

1. Detecta filtros implícitos: día ("hoy"), banco ("falabella"), keywords ("sushi")
2. Busca en **Pinecone** (semántico) o filtra en memoria
3. Agrupa resultados por banco
4. **GPT-4o-mini** genera respuesta en formato WhatsApp
5. Agrega link a `/ver` con filtros pre-aplicados

### Estado conversacional

```python
user_flow = {}  # {"+56912345678": {"step": "ask_banco", "bancos": [], ...}}
```

Se mantiene en memoria por usuario. Se limpia al completar el flujo.

---

## 🔌 API REST

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check — estado y total de beneficios |
| `GET` | `/beneficios` | Todos los beneficios (JSON) |
| `GET` | `/beneficios/buscar` | Buscar con filtros: `?banco=BCI&dia=lunes&restaurante=sushi` |
| `GET` | `/beneficios/{id}` | Beneficio por ID |
| `GET` | `/bancos` | Lista de bancos con conteo de beneficios |
| `GET` | `/estadisticas` | Stats: total, promedio, máximo |
| `GET` | `/restaurantes/top` | Top restaurantes por descuento |
| `POST` | `/rag` | Consulta IA: `{"pregunta": "sushi con descuento hoy"}` |
| `POST` | `/scrape/ejecutar` | Ejecuta scrapers manualmente |
| `GET` | `/scrape/status` | Estado del último scrape |
| `GET` | `/ver` | Página web completa |
| `POST` | `/webhook` | Webhook WhatsApp (Twilio) |

### Ejemplos de uso

```bash
# Todos los beneficios
curl https://api-beneficios-chile.onrender.com/beneficios

# Buscar sushi en BCI
curl "https://api-beneficios-chile.onrender.com/beneficios/buscar?restaurante=sushi&banco=BCI"

# Consultar con IA
curl -X POST https://api-beneficios-chile.onrender.com/rag \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "mejores descuentos para hoy viernes"}'

# Estadísticas
curl https://api-beneficios-chile.onrender.com/estadisticas
```

---

## 🧠 RAG (Retrieval-Augmented Generation)

### Pipeline

```
Pregunta usuario
    │
    ▼
OpenAI Embeddings (text-embedding-3-small)
    │
    ▼
Pinecone (búsqueda vectorial, top 15 resultados)
    │
    ▼
Contexto: beneficios relevantes agrupados por banco
    │
    ▼
GPT-4o-mini (genera respuesta concisa, formato WhatsApp)
    │
    ▼
Respuesta + link a /ver con filtros
```

### Vectorización

```bash
python upload_pinecone.py
# Vectoriza 985 beneficios → Pinecone (text-embedding-3-small)
# Index: beneficios-bancarios
# Namespace: beneficios-bancarios
```

Cada beneficio se convierte a texto para embedding:
```
"La Mar - Banco de Chile - 30% dcto. - Días: lunes, martes - Providencia, Metropolitana - Tope $30.000"
```

---

## ⚙️ Scrapers — Detalle técnico

### Modelo de datos (Beneficio)

```python
@dataclass
class Beneficio:
    id: str                    # "banco_chile_123"
    banco: str                 # "Banco de Chile"
    tarjeta: str               # "Tarjetas Banco de Chile"
    restaurante: str           # "La Mar"
    descuento_valor: float     # 30.0
    descuento_tipo: str        # "porcentaje"
    descuento_texto: str       # "30% dcto."
    dias_validos: List[str]    # ["lunes", "martes"]
    ubicacion: str             # "Metropolitana"
    comuna: str                # "Providencia"
    direccion: str             # "Av. Nueva Costanera 123"
    presencial: bool           # True
    online: bool               # False
    url_fuente: str            # link al banco
    imagen_url: str            # imagen del restaurante
    valido_hasta: str          # "31-Mar-2026"
    restricciones_texto: str   # "Tope $30.000"
    descripcion: str           # texto descriptivo
    # + más campos opcionales
```

### OrquestadorScrapers

Ejecuta los 15 scrapers secuencialmente y normaliza:

| Normalización | Ejemplo |
|---------------|---------|
| Fechas → `DD-MMM-AAAA` | "31 de marzo de 2026" → "31-Mar-2026" |
| Regiones unificadas | "santiago", "rm", "R.M." → "Metropolitana" |
| Comunas RM extraídas | Detecta "Providencia" desde la dirección |
| Textos limpios | Elimina HTML, trunca, normaliza "dto" → "dcto" |

### Ejecución

```bash
python scrapers.py

# Output:
# 🚀 INICIANDO SCRAPING DE BENEFICIOS BANCARIOS
# 📡 Scrapeando Banco de Chile (API CMS)...
# ✅ Banco de Chile: 229 beneficios extraídos
# 📡 Scrapeando Banco Falabella (API CMS v2)...
# ✅ Banco Falabella: 150 beneficios extraídos
# ... (15 bancos)
# ✅ TOTAL BENEFICIOS EXTRAÍDOS: 985
# 💾 Datos guardados en: beneficios.json (985 beneficios)
```

---

## 🚀 Instalación y uso local

### 1. Clonar

```bash
git clone https://github.com/fernandoestay-create/beneficios-bancarios-chile.git
cd beneficios-bancarios-chile
```

### 2. Entorno virtual + dependencias

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 3. Variables de entorno

Crear archivo `.env`:

```bash
# OpenAI (para RAG)
OPENAI_API_KEY=sk-...

# Pinecone (para búsqueda semántica)
PINECONE_API_KEY=...
PINECONE_ENV=us-east-1
PINECONE_INDEX=beneficios-bancarios
PINECONE_HOST=beneficios-bancarios-xxxxx.svc.aped-4627-b74a.pinecone.io

# Twilio (solo si usas whatsapp_bot.py aparte)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+...
```

### 4. Scrapear

```bash
python scrapers.py
# Genera: beneficios.json + beneficios.csv
```

### 5. (Opcional) Subir a Pinecone

```bash
python upload_pinecone.py
# Vectoriza y sube 985 beneficios a Pinecone
```

### 6. Iniciar API

```bash
uvicorn api:app --reload --port 8000
```

### 7. Abrir

```
http://localhost:8000/ver     ← Página web
http://localhost:8000/docs    ← Swagger API docs
```

---

## 🌐 Deploy en Render

### Configuración (render.yaml)

```yaml
services:
  - type: web
    name: api-beneficios-chile            # Servicio principal
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
        value: beneficios-bancarios-xxxxx.svc.aped-4627-b74a.pinecone.io

  - type: web
    name: whatsapp-bot-beneficios          # Bot alternativo (Flask)
    runtime: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn whatsapp_bot:app --bind 0.0.0.0:$PORT"
```

### URLs de producción

```
https://api-beneficios-chile.onrender.com/          ← API
https://api-beneficios-chile.onrender.com/ver        ← Página web
https://api-beneficios-chile.onrender.com/webhook    ← WhatsApp (Twilio)
```

### Deploy automático

Push a `main` → Render despliega automáticamente.

---

## 🔄 Actualización de datos

```bash
# 1. Re-scrapear (985 beneficios)
python scrapers.py

# 2. Subir nuevos vectores a Pinecone (opcional, para RAG)
python upload_pinecone.py

# 3. Commit y push → Render despliega automáticamente
git add beneficios.json beneficios.csv
git commit -m "Actualizar datos de beneficios"
git push origin main
```

---

## 🔒 Sistema de acceso temporal

Para compartir la página con acceso restringido:

```python
# En api.py:
ACCESO_PUBLICO = False   # Activar login

TOKENS_ACCESO = {
    "prueba": datetime(2026, 3, 20, 23, 59, 59),  # caduca 20 marzo
    "demo":   datetime(2026, 4, 1, 23, 59, 59),   # caduca 1 abril
}
```

Link para compartir: `https://api-beneficios-chile.onrender.com/ver?key=prueba`

Actualmente **desactivado** (`ACCESO_PUBLICO = True`).

---

## 🏷️ Versionamiento

| Tag | Fecha | Descripción |
|-----|-------|-------------|
| `v_01` | 14-Mar-2026 | Versión inicial completa. 15 scrapers, 985 beneficios, web con filtros + mapa, bot WhatsApp con flujo conversacional, RAG. |

```bash
# Ver versión
git show v_01

# Restaurar esta versión
git checkout v_01

# Crear rama desde esta versión
git checkout -b hotfix v_01
```

---

## 🧩 Decisiones técnicas

| Decisión | Razón |
|----------|-------|
| HTML embebido en api.py (f-string) | No necesita archivos estáticos, simplifica deploy |
| `{{` y `}}` en JS | Escapar llaves dentro de f-strings Python |
| Multi-select custom (clase MS) | No hay framework frontend, componente ligero |
| Coordenadas por región (no geocoding) | Evita dependencia de API de geocoding |
| Comunas solo Metropolitana | Mayor concentración de datos |
| RAG dual (memoria + Pinecone) | Consultas por día/banco: memoria. Consultas libres: semántico |
| Estado del bot en memoria | Suficiente para MVP, se pierde al reiniciar |

---

## 📋 Dependencias

```
# Scraping
requests, beautifulsoup4, lxml, playwright

# API
fastapi, uvicorn, pydantic, python-multipart

# Bot WhatsApp
twilio, flask, python-dotenv

# RAG / IA
openai, pinecone

# Deploy
gunicorn
```

---

**Versión**: v_01
**Última actualización**: Marzo 2026
**Autor**: Fernando Estay Pérez
**Estado**: ✅ En producción

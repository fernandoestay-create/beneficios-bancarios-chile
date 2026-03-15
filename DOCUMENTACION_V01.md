# BENEFICIOS BANCARIOS CHILE — Documentación v_01
## Backup: tag `v_01` (14 marzo 2026)

---

## 1. QUÉ ES ESTE PROYECTO

Sistema completo que **scrapea descuentos bancarios en restaurantes de Chile**, los almacena, y los expone a través de:

1. **Página web** (`/ver`) — con filtros interactivos, tarjetas y mapa
2. **Bot de WhatsApp** — vía Twilio, con flujo conversacional + IA (RAG)
3. **API REST** — endpoints JSON para consultar beneficios programáticamente

---

## 2. ARQUITECTURA GENERAL

```
┌──────────────────────────────────────────────────────────┐
│                    SCRAPERS (scrapers.py)                 │
│  15 bancos → requests/BeautifulSoup → Beneficio objects  │
│  Normalización: fechas, regiones, comunas, textos        │
│  Output: beneficios.json + beneficios.csv                │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│                   API REST (api.py)                       │
│  FastAPI + Uvicorn                                       │
│  ├── GET  /ver          → Página web completa (HTML/JS)  │
│  ├── GET  /beneficios   → JSON con todos los beneficios  │
│  ├── GET  /bancos       → Lista de bancos                │
│  ├── POST /rag          → Consulta IA (Pinecone+OpenAI)  │
│  ├── POST /webhook      → WhatsApp bot (Twilio)          │
│  └── ...más endpoints                                    │
└───────────────────────┬──────────────────────────────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
       Página Web    WhatsApp    Pinecone
       (/ver)        Bot         (RAG)
```

---

## 3. ARCHIVOS DEL PROYECTO

| Archivo | Líneas | Qué hace |
|---------|--------|----------|
| `scrapers.py` | 3162 | 15 scrapers de bancos + modelo `Beneficio` + `OrquestadorScrapers` |
| `api.py` | 1586 | FastAPI: API REST + página web `/ver` + webhook WhatsApp |
| `whatsapp_bot.py` | 239 | Bot WhatsApp alternativo (Flask, más simple, sin IA) |
| `upload_pinecone.py` | 106 | Sube beneficios vectorizados a Pinecone para búsqueda semántica |
| `beneficios.json` | ~1.2MB | 985 beneficios scrapeados (última ejecución) |
| `beneficios.csv` | ~1.2MB | Mismo data en CSV |
| `render.yaml` | ~30 | Configuración de deploy en Render (2 servicios) |
| `requirements.txt` | 25 | Dependencias Python |
| `.env` | — | Variables de entorno (no en Git) |

---

## 4. SCRAPERS (scrapers.py)

### 4.1 Modelo de datos

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
    url_fuente: str            # "https://..."
    imagen_url: str            # "https://..."
    valido_hasta: str          # "31-Mar-2026"
    restricciones_texto: str   # "Tope $30.000"
    # ...más campos
```

### 4.2 Los 15 scrapers

| # | Clase | Banco | Método de scraping | Beneficios |
|---|-------|-------|--------------------|------------|
| 1 | `ScraperBancoChile` | Banco de Chile | API CMS interna (`/api/beneficios`) | ~200 |
| 2 | `ScraperBancoFalabella` | Banco Falabella | API CMS (`/api/v2/benefits`) | ~150 |
| 3 | `ScraperBCI` | BCI | HTML scraping + regex | ~100 |
| 4 | `ScraperItau` | Banco Itaú | API JSON interna | ~50 |
| 5 | `ScraperScotiabank` | Scotiabank | JS embebido (`sitiosSantiago`/`sitiosRegiones`) | ~61 |
| 6 | `ScraperSantander` | Santander | HTML scraping | ~80 |
| 7 | `ScraperConsorcio` | Banco Consorcio | HTML scraping | ~40 |
| 8 | `ScraperBancoEstado` | BancoEstado | API/HTML | ~60 |
| 9 | `ScraperBancoSecurity` | Banco Security | HTML scraping | ~50 |
| 10 | `ScraperBancoRipley` | Banco Ripley | HTML scraping | ~40 |
| 11 | `ScraperEntel` | Entel | HTML scraping | ~30 |
| 12 | `ScraperTenpo` | Tenpo | API/HTML | ~20 |
| 13 | `ScraperLiderBCI` | Lider BCI | HTML scraping | ~25 |
| 14 | `ScraperBICE` | Banco BICE | HTML scraping | ~30 |
| 15 | `ScraperMach` | Mach | HTML scraping | ~20 |

### 4.3 OrquestadorScrapers

Coordina los 15 scrapers y normaliza datos:

- **Fechas** → formato `DD-MMM-AAAA` (ej: "31-Mar-2026")
- **Regiones** → nombres unificados (ej: "santiago", "rm", "R.M." → "Metropolitana")
- **Comunas** → extrae comuna de la dirección para Región Metropolitana
- **Textos** → limpia HTML residual, normaliza "dto" → "dcto", trunca textos largos

### 4.4 Ejecución

```bash
python scrapers.py
# Output: beneficios.json (985 beneficios) + beneficios.csv
```

---

## 5. API REST (api.py)

### 5.1 Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Health check (JSON con estado) |
| GET | `/beneficios` | Lista todos los beneficios |
| GET | `/beneficios/buscar` | Buscar con filtros (query params) |
| GET | `/beneficios/{id}` | Obtener un beneficio por ID |
| GET | `/bancos` | Lista de bancos con conteo |
| GET | `/estadisticas` | Stats generales |
| GET | `/restaurantes/top` | Top restaurantes por descuento |
| POST | `/rag` | Consulta IA con contexto (RAG) |
| POST | `/scrape/ejecutar` | Ejecuta scrapers manualmente |
| GET | `/scrape/status` | Estado del último scrape |
| GET | `/ver` | **Página web completa** |
| POST | `/webhook` | Webhook WhatsApp (Twilio) |
| GET | `/webhook` | Verificación webhook |

### 5.2 RAG (Retrieval-Augmented Generation)

```
Usuario pregunta → OpenAI genera embedding → Pinecone busca similares
→ Contexto + pregunta → GPT-4o-mini genera respuesta
```

- **Embeddings**: `text-embedding-3-small` (OpenAI)
- **Vector DB**: Pinecone (índice `beneficios-bancarios`, namespace `beneficios-bancarios`)
- **LLM**: `gpt-4o-mini` (respuestas concisas para WhatsApp)

---

## 6. PÁGINA WEB (/ver)

### 6.1 Estructura

La página es un SPA (Single Page Application) server-rendered. Todo el HTML, CSS y JS está embebido en `api.py` como un f-string gigante.

```
┌──────────────────────────────────────────────┐
│  Hero (título + stats: total, bancos, max%)  │
├──────────────────────────────────────────────┤
│  Layout: Sidebar Filtros │ Contenido         │
│  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Limpiar      │  │ [Tarjetas] [Mapa]    │  │
│  │ Buscar       │  │                      │  │
│  │ Banco (MS)   │  │ Vista Tarjetas:      │  │
│  │ Día (7+Todos)│  │  Summary bar (logos)  │  │
│  │ Zona (MS)    │  │  Grid de cards       │  │
│  │ Comuna (MS)  │  │                      │  │
│  │ Dcto mínimo  │  │ Vista Mapa:          │  │
│  │ Modalidad    │  │  Leaflet map         │  │
│  │ Ordenar      │  │  Markers por banco   │  │
│  │ Limpiar      │  │                      │  │
│  └──────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 6.2 Filtros (panel izquierdo, 280px)

| Filtro | Tipo | Detalle |
|--------|------|---------|
| Buscar | Text input | Búsqueda libre en restaurante, banco, descripción, dirección |
| Banco | Multi-select (MS class) | Dropdown con checkboxes, tags, búsqueda interna |
| Día | 7 círculos + "Todos" | Multi-select visual (L M X J V S D) |
| Zona | Multi-select (MS class) | Regiones; Metropolitana aparece primera |
| Comuna | Multi-select (MS class) | Solo aparece si Zona = Metropolitana. Solo comunas de RM |
| Descuento mínimo | Range slider | 0-50% |
| Modalidad | Chips | Todas / Presencial / Online |
| Ordenar | Select | Mayor dcto / Menor dcto / Nombre A-Z / Banco A-Z |

**Importante**: UN solo panel de filtros. Ambas vistas (Tarjetas y Mapa) usan los mismos filtros.

### 6.3 Vista Tarjetas

- Grid de 2 columnas con cards
- Cada card: imagen, badge descuento, logo banco, nombre, descripción, días (círculos), ubicación, dirección, link "Ver detalle"
- Summary bar arriba: pills con logo de cada banco + conteo (clickeables para filtrar)

### 6.4 Vista Mapa

- Mapa Leaflet con tiles de CARTO
- Markers circulares coloreados por banco con % de descuento
- Popups con detalle del restaurante
- Usa coordenadas aproximadas por región (no geocoding real)

### 6.5 Componente JS: Multi-Select (MS)

```javascript
class MS {
    constructor(id, opts, placeholder)
    // Genera: trigger con tags + dropdown con checkboxes + búsqueda
    // Métodos: vals(), reset(), _tags()
}
```

### 6.6 Sistema de acceso temporal

```python
TOKENS_ACCESO = {"prueba": datetime(2026, 3, 15, 23, 59, 59)}
ACCESO_PUBLICO = True  # True = sin clave, False = pide clave
```

- Si `ACCESO_PUBLICO = False`: muestra página de login o acepta `?key=prueba` en URL
- Cookie de sesión por 24h
- Actualmente **desactivado** (público)

---

## 7. BOT WHATSAPP

### 7.1 Flujo conversacional (api.py — webhook activo)

```
Usuario: "hola"
Bot: "¿Qué banco(s) tienes?" (lista bancos disponibles)
    ↓
Usuario: "Falabella, BCI"
Bot: "¿Qué día?" (ej: lunes, hoy, todos)
    ↓
Usuario: "viernes"
Bot: "¿Qué tipo de comida?" (ej: sushi, pizza, todos)
    ↓
Usuario: "sushi"
Bot: 🍽️ 12 descuentos encontrados
     💳 Falabella, BCI | 📅 Viernes | 🍕 sushi
     🏦 BCI (5 dctos)
       • Sushi Express — 30% dcto.
     📋 Ver todos: https://api-beneficios-chile.onrender.com/ver?dia=viernes&q=sushi
```

### 7.2 Comandos rápidos

| Comando | Qué hace |
|---------|----------|
| `hola`, `hi`, `hello`, `inicio` | Inicia flujo de 3 preguntas |
| `/top` | Top 5 restaurantes por descuento |
| `/stats` | Estadísticas generales |
| Cualquier texto libre | Consulta IA (RAG) con GPT-4o-mini |

### 7.3 Consulta libre (RAG)

Si el usuario escribe algo que no es un comando (ej: "donde comer sushi con descuento hoy"):

1. Detecta filtros implícitos: día ("hoy" → sábado), banco ("falabella"), keywords ("sushi")
2. Busca en Pinecone (semántico) o filtra en memoria (por día/banco)
3. Agrupa resultados por banco, limita contexto
4. Envía a GPT-4o-mini con prompt de formato WhatsApp
5. Agrega link a `/ver` con filtros pre-aplicados

### 7.4 Estado conversacional

```python
user_flow = {}  # {phone: {"step": "ask_banco|ask_dia|ask_comida", "bancos": [], "dia": "", "comida": ""}}
```

- Se mantiene en memoria (se pierde si el servidor reinicia)
- Cada usuario tiene su propio estado
- El flujo se limpia automáticamente al completarse

---

## 8. DEPLOY (Render)

### 8.1 render.yaml — 2 servicios

```yaml
services:
  - name: api-beneficios-chile          # ← Servicio principal
    runtime: python
    startCommand: "uvicorn api:app --host 0.0.0.0 --port $PORT"

  - name: whatsapp-bot-beneficios       # ← Bot alternativo (Flask)
    runtime: python
    startCommand: "gunicorn whatsapp_bot:app --bind 0.0.0.0:$PORT"
```

**El webhook de Twilio está apuntado al servicio `api-beneficios-chile`** (FastAPI), no al Flask bot.

### 8.2 Variables de entorno necesarias

```
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENV=us-east-1
PINECONE_INDEX=beneficios-bancarios
PINECONE_HOST=beneficios-bancarios-96gaajy.svc.aped-4627-b74a.pinecone.io
TWILIO_ACCOUNT_SID=...      (solo para whatsapp_bot.py)
TWILIO_AUTH_TOKEN=...        (solo para whatsapp_bot.py)
TWILIO_WHATSAPP_NUMBER=...   (solo para whatsapp_bot.py)
```

### 8.3 URL de producción

```
https://api-beneficios-chile.onrender.com/
https://api-beneficios-chile.onrender.com/ver     ← Página web
https://api-beneficios-chile.onrender.com/webhook  ← WhatsApp bot
```

---

## 9. CÓMO EJECUTAR LOCALMENTE

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear .env con las API keys
cp .env.example .env  # y llenar las keys

# 3. Correr scrapers (genera beneficios.json)
python scrapers.py

# 4. (Opcional) Subir a Pinecone para RAG
python upload_pinecone.py

# 5. Iniciar API
uvicorn api:app --reload --port 8000

# 6. Abrir en navegador
open http://localhost:8000/ver
```

---

## 10. CÓMO ACTUALIZAR DATOS

```bash
# Re-scrapear todos los bancos
python scrapers.py

# Subir nuevos vectores a Pinecone
python upload_pinecone.py

# Commit y push (Render despliega automáticamente)
git add beneficios.json beneficios.csv
git commit -m "Actualizar datos de beneficios"
git push origin main
```

---

## 11. CÓMO RESTAURAR ESTA VERSIÓN

```bash
# Ver el tag
git show v_01

# Volver a esta versión exacta
git checkout v_01

# O crear una rama desde esta versión
git checkout -b fix-desde-v01 v_01
```

---

## 12. VISTA MAPA (Leaflet)

### 12.1 Tecnología
- **Leaflet** 1.9.4 (librería JS de mapas open-source)
- **Tiles**: CARTO light (`basemaps.cartocdn.com`)
- Vista inicial: Chile centrado (-33.45, -70.65), zoom 6

### 12.2 Markers
- Círculos coloreados por banco (28px)
- Color: cada banco tiene un color asignado en `BANK_COLORS`
- Texto: % de descuento dentro del círculo
- Popup al click: restaurante, banco (logo), descuento, dirección, días, link

### 12.3 Coordenadas
- **NO usa geocoding real** (no depende de Google Maps ni otra API)
- Coordenadas aproximadas mapeadas por región en `REGION_COORDS`
- Random offset (±0.02°) para evitar que markers se superpongan
- Ejemplo: "Metropolitana" → [-33.4489, -70.6693] + jitter random

### 12.4 Filtros del mapa
- **Usa los mismos filtros** que la vista de tarjetas (panel izquierdo)
- `renderMapMarkers()` lee: search, bankMS, regionMS, comunaMS, minDisc, days, mode
- Cuando cambia un filtro → `renderAll()` actualiza tarjetas Y mapa simultáneamente

### 12.5 Coordenadas por región (REGION_COORDS)
```
Metropolitana:    -33.4489, -70.6693
Valparaíso:       -33.0472, -71.6127
Biobío:           -36.8201, -73.0444
Araucanía:        -38.7359, -72.5904
Antofagasta:      -23.6509, -70.3954
Coquimbo:         -29.9533, -71.3395
Maule:            -35.4264, -71.6554
Los Lagos:        -41.4693, -72.9424
Los Ríos:         -39.8142, -73.2459
Atacama:          -27.3668, -70.3323
Tarapacá:         -20.2133, -69.9553
Arica:            -18.4783, -70.3126
Magallanes:       -53.1548, -70.9113
Aysén:            -45.5712, -72.0685
Ñuble:            -36.6096, -72.1034
O'Higgins:        -34.1654, -70.7399
```

---

## 13. FILTROS UNIFICADOS (diseño actual)

### 13.1 Diseño
- **UN solo panel de filtros** a la izquierda (280px)
- **Toggle arriba del contenido**: [🍽️ Tarjetas] [📍 Mapa]
- Ambas vistas usan los MISMOS filtros
- No hay filtros duplicados para el mapa

### 13.2 Componente Multi-Select (MS)
```javascript
class MS {
    constructor(id, opts, placeholder)
    // Genera: trigger (box con tags) + dropdown (checkboxes + búsqueda)
    vals()    // → ["BCI", "Scotiabank"] o null si ninguno seleccionado
    reset()   // Limpia toda la selección
    _tags()   // Regenera los tags visuales
}
```

### 13.3 Selector de días
- 7 círculos (L M X J V S D) + pill "Todos"
- Multi-selección: click activa/desactiva cada día
- Si ninguno seleccionado → vuelve a "Todos" automáticamente
- CSS: 24px círculos, gap 2px, nowrap (no se desborda del panel)

### 13.4 Renderizado
```
Filtro cambia → renderAll()
    ├── render()           → regenera grid de cards + summary bar
    └── renderMapMarkers() → limpia y re-crea markers del mapa
```

---

## 14. DECISIONES TÉCNICAS IMPORTANTES

1. **HTML embebido en api.py**: Toda la página `/ver` es un f-string Python (~600 líneas de HTML/CSS/JS). Esto simplifica el deploy (no necesita archivos estáticos) pero hace el archivo grande (~1586 líneas total).

2. **f-strings con `{{` y `}}`**: Como el JS está dentro de un f-string Python, todas las llaves JS deben duplicarse: `{{` para `{` literal. Esto aplica a TODO el JavaScript de la página.

3. **Multi-Select (MS class) en JS**: Componente custom porque no hay framework frontend. Construye dropdowns con checkboxes, tags, búsqueda interna. Si el elemento HTML no existe, el constructor crashea (lección aprendida al quitar el sidebar del mapa).

4. **Coordenadas del mapa aproximadas**: No se usa geocoding real. Las coordenadas se mapean por región con un random offset para que no se superpongan. Esto evita dependencia de APIs externas.

5. **Comunas solo Metropolitana**: El filtro de comunas solo muestra comunas de RM (filtrado: `b.ubicacion == 'Metropolitana'`). Es donde se concentran los datos.

6. **RAG dual**: Para consultas por día/banco usa búsqueda en memoria (más rápido). Para consultas generales/semánticas usa Pinecone + OpenAI embeddings.

7. **Estado conversacional en memoria**: El flujo de 3 pasos del bot (`user_flow` dict) se pierde si el servidor reinicia. Aceptable para MVP.

8. **Filtros unificados**: Un solo panel controla tarjetas Y mapa. Intentos anteriores con filtros separados causaron bugs (MS class crasheaba al no encontrar elementos, desincronización de filtros).

9. **Logos de bancos**: URLs de Wikipedia Commons. Fallback con `onerror` a texto si la imagen no carga.

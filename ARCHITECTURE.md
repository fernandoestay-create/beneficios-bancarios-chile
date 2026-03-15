# 🏗️ Arquitectura del Sistema

> Actualizado: 15 Marzo 2026 · v_01

---

## 📐 Diagrama general

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FUENTES DE DATOS (15 bancos)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Banco de Chile    Banco Falabella    BCI          Banco Itaú               │
│  (API CMS)         (API CMS v2)      (HTML)       (API JSON)               │
│                                                                             │
│  Scotiabank        Santander          Consorcio    BancoEstado              │
│  (JS embebido)     (HTML)             (HTML)       (API/HTML)               │
│                                                                             │
│  Banco Security    Banco Ripley       Entel        Tenpo                    │
│  (HTML)            (HTML)             (HTML)       (API/HTML)               │
│                                                                             │
│  Lider BCI         Banco BICE         Mach                                  │
│  (HTML)            (HTML)             (HTML)                                │
│                                                                             │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPA DE SCRAPING (scrapers.py)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    15 Clases Scraper                                │    │
│  │  ScraperBancoChile · ScraperBancoFalabella · ScraperBCI            │    │
│  │  ScraperItau · ScraperScotiabank · ScraperSantander                │    │
│  │  ScraperConsorcio · ScraperBancoEstado · ScraperBancoSecurity      │    │
│  │  ScraperBancoRipley · ScraperEntel · ScraperTenpo                  │    │
│  │  ScraperLiderBCI · ScraperBICE · ScraperMach                       │    │
│  └────────────────────────────────┬────────────────────────────────────┘    │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    OrquestadorScrapers                              │    │
│  │  • Ejecuta 15 scrapers secuencialmente                             │    │
│  │  • Normaliza fechas → DD-MMM-AAAA                                 │    │
│  │  • Unifica regiones → "Metropolitana", "Valparaíso", etc.         │    │
│  │  • Extrae comunas para Región Metropolitana                        │    │
│  │  • Limpia textos (HTML residual, truncado)                         │    │
│  │  • Normaliza descuentos → "30% dcto."                             │    │
│  └────────────────────────────────┬────────────────────────────────────┘    │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ALMACENAMIENTO                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📄 beneficios.json         📊 beneficios.csv         🔍 Pinecone          │
│  ├─ 985 beneficios          ├─ Mismo data             ├─ Embeddings         │
│  ├─ ~1.2 MB                 ├─ Para Excel/BI          │  (text-embedding-   │
│  └─ Carga en memoria        └─ Backup                 │   3-small)          │
│     al iniciar API                                     ├─ Búsqueda          │
│                                                        │  semántica          │
│  🐙 GitHub                                            └─ Namespace:         │
│  ├─ Control de versión                                   beneficios-        │
│  ├─ Tag v_01 (backup)                                    bancarios          │
│  └─ Auto-deploy a Render                                                    │
│                                                                             │
└────────────┬──────────────────────┬─────────────────────┬───────────────────┘
             │                      │                     │
             ▼                      ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CAPA DE APLICACIÓN (api.py · FastAPI)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐   │
│  │  PÁGINA WEB     │  │  BOT WHATSAPP        │  │  API REST            │   │
│  │  GET /ver       │  │  POST /webhook       │  │  GET /beneficios     │   │
│  ├─────────────────┤  ├──────────────────────┤  ├──────────────────────┤   │
│  │ HTML/CSS/JS     │  │ Flujo 3 pasos:       │  │ GET /buscar          │   │
│  │ embebido en     │  │  1. ¿Banco(s)?       │  │ GET /bancos          │   │
│  │ f-string Python │  │  2. ¿Día?            │  │ GET /estadisticas    │   │
│  │                 │  │  3. ¿Comida?         │  │ GET /restaurantes/top│   │
│  │ Filtros:        │  │ → Resultado + link   │  │ POST /rag            │   │
│  │ • Buscar        │  │                      │  │ POST /scrape/ejecutar│   │
│  │ • Banco (MS)    │  │ Consulta libre:      │  │                      │   │
│  │ • Día (7+Todos) │  │ → RAG (Pinecone +    │  │ Swagger docs:        │   │
│  │ • Zona (MS)     │  │   GPT-4o-mini)       │  │ GET /docs            │   │
│  │ • Comuna (MS)   │  │                      │  │                      │   │
│  │ • Dcto mínimo   │  │ Estado por usuario:  │  │ JSON responses       │   │
│  │ • Modalidad     │  │ user_flow dict       │  │ CORS habilitado      │   │
│  │ • Ordenar       │  │ (en memoria)         │  │                      │   │
│  │                 │  │                      │  │                      │   │
│  │ Vistas:         │  │ Atajos:              │  │                      │   │
│  │ • Tarjetas      │  │ /top · /stats        │  │                      │   │
│  │ • Mapa Leaflet  │  │                      │  │                      │   │
│  └────────┬────────┘  └──────────┬───────────┘  └──────────┬───────────┘   │
│           │                      │                         │                │
└───────────┼──────────────────────┼─────────────────────────┼────────────────┘
            │                      │                         │
            ▼                      ▼                         ▼
  ┌──────────────────┐   ┌──────────────────┐     ┌──────────────────┐
  │  🌐 Navegador    │   │  💬 WhatsApp     │     │  🔌 Integraciones│
  │  Desktop/Mobile  │   │  vía Twilio      │     │  curl / apps     │
  └──────────────────┘   └──────────────────┘     └──────────────────┘
```

---

## 🔄 Flujos de datos

### 1. Flujo de scraping

```
python scrapers.py
    │
    ├── ScraperBancoChile()     → requests GET API CMS → parse JSON → ~200 Beneficio
    ├── ScraperBancoFalabella() → requests GET API v2  → parse JSON → ~150 Beneficio
    ├── ScraperBCI()            → requests GET HTML    → BeautifulSoup → ~100 Beneficio
    ├── ScraperItau()           → requests GET API     → parse JSON → ~50 Beneficio
    ├── ScraperScotiabank()     → requests GET HTML    → regex JS arrays → ~61 Beneficio
    ├── ScraperSantander()      → requests GET HTML    → BeautifulSoup → ~80 Beneficio
    ├── ScraperConsorcio()      → requests GET HTML    → BeautifulSoup → ~40 Beneficio
    ├── ScraperBancoEstado()    → requests GET         → parse → ~60 Beneficio
    ├── ScraperBancoSecurity()  → requests GET HTML    → BeautifulSoup → ~50 Beneficio
    ├── ScraperBancoRipley()    → requests GET HTML    → BeautifulSoup → ~40 Beneficio
    ├── ScraperEntel()          → requests GET HTML    → BeautifulSoup → ~30 Beneficio
    ├── ScraperTenpo()          → requests GET         → parse → ~20 Beneficio
    ├── ScraperLiderBCI()       → requests GET HTML    → BeautifulSoup → ~25 Beneficio
    ├── ScraperBICE()           → requests GET HTML    → BeautifulSoup → ~30 Beneficio
    └── ScraperMach()           → requests GET HTML    → BeautifulSoup → ~20 Beneficio
    │
    ▼
OrquestadorScrapers._normalizar_todos()
    ├── Fechas:    "31 de marzo de 2026" → "31-Mar-2026"
    ├── Regiones:  "santiago", "rm", "R.M." → "Metropolitana"
    ├── Comunas:   Extraer de dirección para RM → "Providencia"
    ├── Textos:    Limpiar HTML, "dto" → "dcto", truncar
    └── Descuento: "50% de descuento" → "50% dcto."
    │
    ▼
beneficios.json (985 beneficios) + beneficios.csv
```

### 2. Flujo de la página web (/ver)

```
GET /ver
    │
    ▼
api.py genera HTML completo (f-string)
    ├── Python: serializa beneficios → JSON embebido en <script>
    ├── Python: genera listas de bancos, regiones, comunas
    ├── HTML: hero + layout (sidebar filtros + main contenido)
    ├── CSS: estilos embebidos (variables CSS, responsive)
    └── JS: lógica de filtros, rendering, mapa
    │
    ▼
Navegador recibe HTML completo
    │
    ├── JS: crea componentes Multi-Select (MS class)
    ├── JS: render() filtra deals en memoria y genera cards
    ├── JS: Leaflet inicializa mapa con markers
    └── JS: event listeners → auto-apply filtros
    │
    ▼
Usuario interactúa con filtros
    ├── Cambio filtro → render() + renderMapMarkers()
    ├── Click summary pill → toggle banco
    ├── Click [Tarjetas/Mapa] → cambiar vista
    └── Ambas vistas usan los MISMOS filtros
```

### 3. Flujo del bot WhatsApp

```
Usuario envía mensaje en WhatsApp
    │
    ▼
Twilio recibe → POST /webhook (api.py)
    │
    ▼
procesar_comando_whatsapp(texto, usuario)
    │
    ├── ¿Usuario en flujo activo? (user_flow dict)
    │   ├── step="ask_banco" → parsear bancos → ask_dia
    │   ├── step="ask_dia"   → parsear día → ask_comida
    │   └── step="ask_comida"→ parsear comida → RESULTADO
    │                              │
    │                              ▼
    │                    _generar_resultado_flow()
    │                    ├── Filtrar por banco(s)
    │                    ├── Filtrar por día
    │                    ├── Filtrar por keyword comida
    │                    ├── Agrupar por banco (top 3 cada uno)
    │                    └── Generar link a /ver con filtros
    │
    ├── "hola" / "inicio" → Iniciar flujo (ask_banco)
    ├── "/top" → Top 5 restaurantes
    ├── "/stats" → Estadísticas
    │
    └── Texto libre → RAG
        ├── Detectar: día, banco, keywords
        ├── Pinecone búsqueda semántica (top 15)
        ├── GPT-4o-mini genera respuesta
        └── Agregar link a /ver
    │
    ▼
Twilio envía respuesta al usuario
```

### 4. Flujo RAG (Retrieval-Augmented Generation)

```
Pregunta: "donde comer sushi con descuento hoy"
    │
    ▼
Detectar filtros implícitos
    ├── "hoy" → dia_filtro = "sabado"
    ├── "sushi" → keyword
    └── banco no mencionado → null
    │
    ▼
¿Tiene día/banco explícito?
    │
    ├── SÍ → Búsqueda en memoria (beneficios_db)
    │        Filtrar por día + banco + keyword
    │
    └── NO → Búsqueda semántica en Pinecone
             ├── OpenAI text-embedding-3-small(pregunta)
             ├── Pinecone.query(vector, top_k=15)
             └── Retorna beneficios relevantes
    │
    ▼
Agrupar por banco, limitar contexto
    │
    ▼
GPT-4o-mini (prompt WhatsApp)
    ├── System: "Eres experto en descuentos... formato WhatsApp..."
    ├── Context: beneficios agrupados
    └── User: pregunta original
    │
    ▼
Respuesta + link a /ver
```

---

## 📊 Modelo de datos

```python
@dataclass
class Beneficio:
    # Identificación
    id: str                    # "banco_chile_123"
    banco: str                 # "Banco de Chile"
    tarjeta: str               # "Tarjetas Banco de Chile"

    # Restaurante
    restaurante: str           # "La Mar"
    descripcion: str           # "Cocina nikkei..."
    imagen_url: str            # URL de imagen
    logo_url: str              # URL del logo del banco

    # Descuento
    descuento_valor: float     # 30.0
    descuento_tipo: str        # "porcentaje"
    descuento_texto: str       # "30% dcto."

    # Temporalidad
    dias_validos: List[str]    # ["lunes", "martes"]
    valido_desde: str          # "01-Mar-2026"
    valido_hasta: str          # "31-Mar-2026"

    # Ubicación
    ubicacion: str             # "Metropolitana"
    comuna: str                # "Providencia"
    direccion: str             # "Av. Nueva Costanera 123"

    # Modalidad
    presencial: bool           # True
    online: bool               # False

    # Links y metadata
    url_fuente: str            # link al banco
    restricciones_texto: str   # "Tope $30.000"
    activo: bool               # True
    fecha_scrape: str          # ISO timestamp
    tags: List[str]            # etiquetas
```

---

## 🌐 Deploy en producción

```
┌─────────────────────────────────────────────────────────┐
│                      RENDER.COM                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Servicio 1: api-beneficios-chile                       │
│  ├── Runtime: Python                                    │
│  ├── Build: pip install -r requirements.txt             │
│  ├── Start: uvicorn api:app --host 0.0.0.0 --port $PORT│
│  ├── Env: OPENAI_API_KEY, PINECONE_*                    │
│  └── URL: api-beneficios-chile.onrender.com             │
│      ├── /ver        → Página web                       │
│      ├── /webhook    → Bot WhatsApp (Twilio)            │
│      ├── /beneficios → API JSON                         │
│      └── /docs       → Swagger                          │
│                                                          │
│  Servicio 2: whatsapp-bot-beneficios (alternativo)      │
│  ├── Runtime: Python                                    │
│  ├── Start: gunicorn whatsapp_bot:app                   │
│  └── URL: whatsapp-bot-beneficios.onrender.com          │
│      └── Bot Flask simple (sin IA)                      │
│                                                          │
│  Deploy: push a main → auto-deploy                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
          │                          │
          ▼                          ▼
┌──────────────────┐       ┌──────────────────┐
│  Servicios ext.  │       │  Twilio          │
│  ├── Pinecone    │       │  ├── Webhook URL │
│  ├── OpenAI      │       │  │   /webhook    │
│  └── GitHub      │       │  └── WhatsApp    │
└──────────────────┘       └──────────────────┘
```

---

## 🔐 Seguridad

| Capa | Implementación |
|------|----------------|
| Input validation | Pydantic models + FastAPI Query params |
| API Keys | Variables de entorno (.env), nunca hardcoded |
| CORS | FastAPI CORSMiddleware habilitado |
| HTTPS | Render auto-HTTPS en producción |
| Acceso temporal | Sistema de tokens con expiración (desactivable) |
| Cookies | httponly=True para sesión de acceso |

---

## 📈 Capacidad actual

```
Instancia actual (Render free tier):
├── 1 servidor (512MB RAM)
├── beneficios_db en memoria (~1.2MB JSON)
├── Estado bot en memoria (dict por usuario)
├── ~500 requests/sec capacity
└── Costo: $0/mes (free tier)

Datos:
├── 985 beneficios de 15 bancos
├── ~700 restaurantes únicos
├── 16 regiones cubiertas
└── Actualización: manual (python scrapers.py)
```

---

**Última actualización**: 15 Marzo 2026
**Versión**: v_01

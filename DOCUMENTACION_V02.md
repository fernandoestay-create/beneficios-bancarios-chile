# BENEFICIOS BANCARIOS CHILE — Documentación v_03
## Actualización: 01 abril 2026

---

## 1. QUÉ ES ESTE PROYECTO

Sistema que **scrapea descuentos bancarios en restaurantes y bencinas de Chile**, los almacena y los expone a través de:

1. **Página web restaurantes** (`/ver`) — filtros, tarjetas y mapa
2. **Página web bencinas** (`/ver/bencinas`) — 3 vistas: Tarjetas descuentos, Mapa con logos, **PU Bencina** (comparador de precios)
3. **Comparador de precios** — 1,750+ estaciones de todo Chile con precios reales (CNE)
4. **Bot de WhatsApp** — menús numerados (restaurantes o bencinas)
5. **API REST** — endpoints JSON (incluye precios de combustible)
6. **Reporte por email** — Gmail automático después de cada scraping

---

## 2. ARQUITECTURA GENERAL

```
┌──────────────────────────────────────────────────────────┐
│                    SCRAPERS (scrapers.py)                 │
│  15 bancos restaurantes → beneficios.json (~914)         │
│  Bencinas → bencinas.json:                               │
│    28 descuentos bancarios (descuentosrata.com)           │
│    1,462 estaciones Copec/Shell/Aramco con precios        │
│    1,815 estaciones totales con precios (todo Chile)      │
│  Fuente precios: bencinaenlinea.cl (CNE)                 │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│                   API REST (api.py ~2,600 líneas)        │
│  FastAPI + Uvicorn                                       │
│  ├── GET  /ver           → Web restaurantes (HTML/JS)    │
│  ├── GET  /ver/bencinas  → Web bencinas (HTML/JS)        │
│  ├── GET  /beneficios    → Lista paginada JSON           │
│  ├── GET  /bencinas      → Descuentos bencina JSON       │
│  ├── GET  /bencinas/precios → Comparador precios JSON    │
│  ├── GET  /bencinas/precios/mejores → Top baratas JSON   │
│  ├── GET  /bencinas/precios/resumen → Stats por cadena   │
│  ├── POST /webhook       → Bot WhatsApp (Twilio)         │
│  ├── POST /rag           → Consulta IA                   │
│  ├── GET  /static/logos/ → SVGs y fotos locales          │
│  └── GET  /docs          → Swagger UI                    │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│                      DEPLOY                              │
│  Render (free tier) → auto-deploy desde main             │
│  GitHub Actions → scraping + precios L/J + email Gmail   │
│  Twilio Sandbox → WhatsApp gratis                        │
└──────────────────────────────────────────────────────────┘
```

---

## 3. URLs DE PRODUCCIÓN

| Recurso | URL |
|---------|-----|
| Web Restaurantes | https://api-beneficios-chile.onrender.com/ver |
| Web Bencinas | https://api-beneficios-chile.onrender.com/ver/bencinas |
| API REST | https://api-beneficios-chile.onrender.com/ |
| Swagger | https://api-beneficios-chile.onrender.com/docs |
| WhatsApp Webhook | https://api-beneficios-chile.onrender.com/webhook |

---

## 4. ESTADÍSTICAS

| Métrica | Valor |
|---------|-------|
| Beneficios restaurantes | ~914 |
| Bancos scrapeados | 15 |
| Descuentos bencina | 28 |
| Cadenas principales | 3 (Copec, Shell, Aramco) |
| Estaciones con descuentos | 1,462 |
| Estaciones totales (todo Chile) | 1,815 |
| Estaciones con precios | 1,750 |
| Marcas de combustible | 120+ |
| Regiones | 16 |
| Fuente precios | bencinaenlinea.cl (CNE) |
| Logos locales | 13 SVGs + 4 imágenes |

---

## 5. STACK TECNOLÓGICO

| Componente | Tecnología |
|-----------|-----------|
| Backend | Python 3.9+, FastAPI, Uvicorn |
| Scraping | requests, BeautifulSoup4, lxml, Playwright |
| IA/Búsqueda | OpenAI GPT-4o-mini, text-embedding-3-small, Pinecone |
| WhatsApp | Twilio (sandbox) |
| Frontend | HTML/CSS/JS embebido, Leaflet (mapa) |
| Hosting | Render (free tier) |
| CI/CD | GitHub Actions |
| Email | Gmail SMTP via GitHub Actions |
| Logos | SVGs locales en /static/logos/ |

---

## 6. ARCHIVOS PRINCIPALES

| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `api.py` | ~2,800 | FastAPI: 2 webs (3 vistas bencinas) + API precios + webhook + RAG |
| `scrapers.py` | ~3,700 | 15 scrapers restaurantes + ScraperBencinaEnLinea + modelo |
| `whatsapp_bot.py` | 239 | Bot alternativo Flask (sin IA) |
| `upload_pinecone.py` | 106 | Carga vectores a Pinecone |
| `beneficios.json` | ~1.2 MB | 985 beneficios restaurantes |
| `bencinas.json` | ~3.5 MB | 28 descuentos + 1,462 estaciones + 1,815 precios |
| `static/logos/` | — | 13 SVGs + 3 JPGs estaciones + 1 PNG |
| `.github/workflows/scraper.yml` | — | Scraping automático + email |
| `render.yaml` | — | Config deploy (2 servicios) |

---

## 7. SCRAPERS

### 7a. Restaurantes (15 bancos)

| # | Banco | Método | ~Beneficios |
|---|-------|--------|-------------|
| 1 | Banco de Chile | API CMS interna | ~200 |
| 2 | Banco Falabella | Contentful CMS API | ~150 |
| 3 | BCI | HTML + regex | ~100 |
| 4 | Banco Itaú | JSON API | ~50 |
| 5 | Scotiabank | JS arrays embebidos | ~61 |
| 6 | Santander | HTML scraping | ~80 |
| 7 | Banco Consorcio | HTML scraping | ~40 |
| 8 | BancoEstado | API/HTML híbrido | ~60 |
| 9 | Banco Security | HTML scraping | ~50 |
| 10 | Banco Ripley | HTML scraping | ~40 |
| 11 | Entel | HTML scraping | ~30 |
| 12 | Tenpo | API/HTML híbrido | ~20 |
| 13 | Lider BCI | HTML scraping | ~25 |
| 14 | BICE | HTML scraping | ~30 |
| 15 | Mach | HTML scraping | ~20 |

### 7b. Bencinas — Descuentos bancarios

- **Fuente descuentos:** descuentosrata.com/bencina (HTML scraping + fallback)
- **Datos:** banco, tarjeta, descuento/litro, día, cadena, tope, condición
- **Cadenas con descuentos:** Copec, Shell, Aramco

### 7c. Bencinas — Estaciones y precios (NUEVO v_03)

- **Fuente:** `api.bencinaenlinea.cl` (Comisión Nacional de Energía - CNE)
- **Clase:** `ScraperBencinaEnLinea` (reemplaza `ScraperEstacionesCNE` / Overpass API)
- **Endpoint:** `GET /api/busqueda_estacion_filtro` (público, sin autenticación)
- **Datos por estación:** cadena, dirección, comuna, región, lat/lon, precios 93/95/97/diesel/kerosene
- **Estaciones totales:** 1,815 (todo Chile, 120+ marcas)
- **Estaciones con precios:** 1,750
- **Estaciones con descuentos (Copec/Shell/Aramco):** 1,462
- **Actualización:** lunes y jueves 10AM Chile (GitHub Actions)
- **Disclaimer:** Los precios son de exclusiva responsabilidad de las estaciones informantes

---

## 8. PÁGINAS WEB

### 8a. Restaurantes (`/ver`)
- Responsive mobile-first
- Vista dual: Cards (grid) + Mapa (Leaflet)
- Filtros 100% client-side: texto, bancos (multi-select), días, región, comuna, descuento mín
- Componente Multi-Select custom (JS puro)
- Navegación entre restaurantes y bencinas

### 8b. Bencinas (`/ver/bencinas`) — 3 vistas

**Vista 1: Tarjetas** (descuentos bancarios)
- Cards hero con fotos reales de estaciones
- Logos de cadenas y bancos en cada card
- Cards agrupadas por banco+cadena+día
- Links "Ver detalle" a páginas oficiales de bancos

**Vista 2: Mapa** (estaciones con descuentos)
- 1,462 estaciones Copec/Shell/Aramco con logos de cadena en marcadores
- Popups con: nombre, dirección, precios (93/97/Diesel), descuentos bancarios, botón "Ir" (Google Maps)
- Geolocalización "Mi ubicación"

**Vista 3: PU Bencina** (comparador de precios — NUEVO v_03)
- 1,750+ estaciones de todo Chile con precios reales
- Mapa con marcadores: logo cadena + precio (verde=barato, rojo=caro)
- Ranking de las 50 más baratas en la zona visible del mapa
- Stats: más barato, más caro, promedio, total en vista
- Filtros: combustible (93/95/97/Diesel/Kerosene), botón "Ir" (Google Maps)
- Ranking se sincroniza con viewport del mapa (mover/zoom actualiza lista)
- Geolocalización "Mi ubicación"

**Filtros compartidos (sidebar izquierdo, aplican a las 3 vistas):**
- Buscar (texto libre)
- Banco/App (multi-select)
- Día de la semana
- Cadena (Todas/Copec/Shell/Aramco/Otras)
- Región (dropdown, centra el mapa automáticamente)
- Comuna (dinámico según región)
- Ordenar
- Limpiar filtros (resetea todo incluyendo PU Bencina)

---

## 9. BOT WHATSAPP

**Costo OpenAI: $0** (flujo 100% Python con menús numerados)

### Flujo:
```
Cualquier mensaje → "¡Hola! ¿En qué quieres ahorrar? 1.Restaurantes 2.Bencinas"

RESTAURANTES (3 pasos):
  Paso 1: ¿Qué día? → 1.Hoy 2.Lunes ... 7.Domingo
  Paso 2: ¿Qué banco(s)? → 1.BCI 2.Santander... (ej: "1,3,5" para varios)
  Paso 3: Resultado + link filtrado a /ver?dia=X&banco=Y&banco=Z

BENCINAS (2 pasos):
  Paso 1: ¿Qué día? → 1.Hoy 2.Lunes ... 7.Domingo
  Paso 2: Resultado + link a /ver/bencinas?dia=X
```

### Texto libre (RAG):
- Solo si el usuario escribe algo que no matchea ningún número/comando
- Usa Pinecone + GPT-4o-mini
- Costo: ~$0.002 por consulta

---

## 10. AUTOMATIZACIÓN

### GitHub Actions (`scraper.yml`)
- **Días 1-4 del mes:** scraping completo a las 2 AM Chile (beneficios + bencinas + precios)
- **Días 10, 20, 30:** actualización quincenal
- **Lunes y jueves:** actualización de precios combustible a las 10 AM Chile (NUEVO v_03)
- **Total:** ~15 ejecuciones/mes
- **Pipeline:** scrapers.py → upload_pinecone.py → commit → push → email
- **Ejecución manual:** disponible desde GitHub Actions

### Email de reporte (Gmail)
- Se envía a `fernando.estay@gmail.com` después de cada scraping exitoso
- Incluye: total beneficios, bancos, descuentos bencina, estaciones con descuentos, **estaciones con precios** (NUEVO)
- Links directos a /ver y /ver/bencinas
- Email de error si falla el scraping

---

## 11. COSTOS

| Servicio | Costo |
|----------|-------|
| Render (hosting) | $0/mes (free tier, 512MB RAM) |
| GitHub Actions (scraping) | $0 (2,000 min/mes gratis) |
| Gmail SMTP (reportes) | $0 |
| Twilio WhatsApp (sandbox) | $0 |
| OpenAI (solo texto libre RAG) | ~$0.002/consulta |
| Pinecone (vectores) | $0 (free tier) |
| **Total mensual estimado** | **$0 - $0.50** |

---

## 12. VARIABLES DE ENTORNO

### Render:
- `OPENAI_API_KEY` - API key de OpenAI
- `PINECONE_API_KEY` - API key de Pinecone
- `PINECONE_ENV`, `PINECONE_HOST`, `PINECONE_INDEX`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`

### GitHub Actions (5 secrets configurados ✅):
- `OPENAI_API_KEY` ✅
- `PINECONE_API_KEY` ✅
- `PINECONE_HOST` ✅
- `GMAIL_USER` ✅
- `GMAIL_APP_PASSWORD` ✅ (contraseña de aplicación de Google)

---

## 13. ENDPOINTS API — PRECIOS (NUEVO v_03)

| Endpoint | Parámetros | Descripción |
|----------|-----------|-------------|
| `GET /bencinas/precios` | `combustible`, `comuna`, `region`, `cadena`, `orden`, `limite` | Buscar estaciones por precio |
| `GET /bencinas/precios/mejores` | `combustible`, `region`, `limite` | Top N más baratas |
| `GET /bencinas/precios/resumen` | — | Promedio/min/max por cadena |
| `GET /bencinas/estaciones` | `cadena`, `comuna` | Lista estaciones con coordenadas |
| `GET /bencinas/mapa` | — | Estaciones + descuentos combinados |

---

## 14. PENDIENTES / MEJORAS FUTURAS

- [ ] Twilio producción (cuando se necesite WhatsApp público)
- [ ] Dashboard de métricas (cuántas consultas, bancos más buscados)
- [ ] Notificaciones push cuando hay descuentos nuevos
- [ ] Cache de consultas RAG para reducir costos OpenAI
- [ ] Integrar precios de bencina en bot WhatsApp ("¿dónde está la 93 más barata?")

---

## 15. CHANGELOG

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v_01 | 14-Mar-2026 | Lanzamiento: 15 scrapers, web, bot, RAG, Pinecone |
| v_02 | 26-Mar-2026 | Bencinas, cards hero, bot v2 (menús $0), email Gmail, logos locales |
| v_02.1 | 27-Mar-2026 | GitHub Actions 100% operativo |
| v_02.2 | 30-Mar-2026 | Verificación datos bencinas, URLs "Ver detalle" por banco+cadena |
| **v_03** | **01-Abr-2026** | **Comparador de precios combustible (PU Bencina):** |
| | | - Nuevo `ScraperBencinaEnLinea` reemplaza Overpass API (1,815 estaciones, 1,750 con precios) |
| | | - Fuente: bencinaenlinea.cl (Comisión Nacional de Energía) |
| | | - Tab "PU Bencina": mapa con logos+precios, ranking sincronizado con viewport |
| | | - 3 endpoints API nuevos: /bencinas/precios, /mejores, /resumen |
| | | - Logos de cadena en marcadores del mapa (Copec/Shell/Aramco) |
| | | - Botón "Ir" en popups y ranking (abre Google Maps con dirección) |
| | | - Geolocalización "Mi ubicación" en ambos mapas |
| | | - Filtros compartidos sidebar: Región/Comuna/Cadena aplican a las 3 vistas |
| | | - Al seleccionar región, mapas se centran automáticamente |
| | | - Chip "Otras" para cadenas que no son Copec/Shell/Aramco |
| | | - GitHub Actions: nuevo cron lunes/jueves 10AM para actualizar precios |
| | | - Email report incluye "Estaciones con precios" |
| | | - Disclaimer CNE en footer |

---

*Documentación v_03 — 01 Abril 2026*

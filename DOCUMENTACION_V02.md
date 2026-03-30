# BENEFICIOS BANCARIOS CHILE — Documentación v_02
## Actualización: 26 marzo 2026

---

## 1. QUÉ ES ESTE PROYECTO

Sistema que **scrapea descuentos bancarios en restaurantes y bencinas de Chile**, los almacena y los expone a través de:

1. **Página web restaurantes** (`/ver`) — filtros, tarjetas y mapa
2. **Página web bencinas** (`/ver/bencinas`) — cards hero con fotos, logos, mapa estaciones
3. **Bot de WhatsApp** — menús numerados (restaurantes o bencinas)
4. **API REST** — endpoints JSON
5. **Reporte por email** — Gmail automático después de cada scraping

---

## 2. ARQUITECTURA GENERAL

```
┌──────────────────────────────────────────────────────────┐
│                    SCRAPERS (scrapers.py)                 │
│  15 bancos restaurantes → beneficios.json (985)          │
│  3 cadenas bencina → bencinas.json (28 dctos + 367 est) │
│  Fuentes: sitios bancos + descuentosrata + OpenStreetMap │
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
│  GitHub Actions → scraping automático + email Gmail      │
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
| Beneficios restaurantes | 985 |
| Bancos scrapeados | 15 |
| Descuentos bencina | 28 |
| Cadenas bencina | 3 (Copec, Shell, Aramco) |
| Estaciones mapeadas | 367 (OpenStreetMap) |
| Restaurantes únicos | ~700 |
| Regiones | 16 |
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
| `api.py` | ~2,600 | FastAPI: 2 webs + API + webhook + RAG |
| `scrapers.py` | ~3,600 | 15 scrapers restaurantes + bencinas + modelo |
| `whatsapp_bot.py` | 239 | Bot alternativo Flask (sin IA) |
| `upload_pinecone.py` | 106 | Carga vectores a Pinecone |
| `beneficios.json` | ~1.2 MB | 985 beneficios restaurantes |
| `bencinas.json` | ~200 KB | 28 descuentos + 367 estaciones |
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

### 7b. Bencinas (3 cadenas)

- **Fuente:** descuentosrata.com/bencina (HTML scraping)
- **Datos:** banco, tarjeta, descuento/litro, día, cadena, tope, condición
- **Estaciones:** OpenStreetMap Overpass API (367 ubicaciones reales)
- **Cadenas:** Copec, Shell, Aramco

---

## 8. PÁGINAS WEB

### 8a. Restaurantes (`/ver`)
- Responsive mobile-first
- Vista dual: Cards (grid) + Mapa (Leaflet)
- Filtros 100% client-side: texto, bancos (multi-select), días, región, comuna, descuento mín
- Componente Multi-Select custom (JS puro)
- Navegación entre restaurantes y bencinas

### 8b. Bencinas (`/ver/bencinas`)
- Cards hero con fotos reales de estaciones
- Logos de cadenas (Copec/Shell/Aramco) y bancos en cada card
- Cards agrupadas por banco+cadena+día (evita duplicados)
- Desglose de tarjetas con descuento individual
- Mapa con 367 estaciones reales
- Links "Ver detalle" a páginas oficiales de bancos

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
- **Días 1-4 del mes:** scraping diario a las 2 AM Chile (obligatorio)
- **Días 10, 20, 30:** actualización quincenal (3 veces al mes)
- **Total:** 7 ejecuciones/mes
- **Pipeline:** scrapers.py → upload_pinecone.py → commit → push → email
- **Ejecución manual:** disponible desde GitHub Actions

### Email de reporte (Gmail)
- Se envía a `fernando.estay@gmail.com` después de cada scraping exitoso
- Incluye: total beneficios, bancos, descuentos bencina, estaciones
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

## 13. PENDIENTES / MEJORAS FUTURAS

- [ ] Twilio producción (cuando se necesite WhatsApp público)
- [ ] Más cadenas bencina si aparecen nuevas
- [ ] Dashboard de métricas (cuántas consultas, bancos más buscados)
- [ ] Notificaciones push cuando hay descuentos nuevos
- [ ] Cache de consultas RAG para reducir costos OpenAI

---

## 14. CHANGELOG

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v_01 | 14-Mar-2026 | Lanzamiento: 15 scrapers, web, bot, RAG, Pinecone |
| v_02 | 26-Mar-2026 | Bencinas, cards hero, bot v2 (menús $0), email Gmail, logos locales |
| v_02.1 | 27-Mar-2026 | GitHub Actions 100% operativo: secrets configurados, permisos write, scraping+Pinecone+commit+email funcionando. Schedule: días 1-4 + 10,20,30 |

---

*Documentación v_02 — 26 Marzo 2026*

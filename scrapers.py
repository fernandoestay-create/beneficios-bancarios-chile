"""
SCRAPERS DE BENEFICIOS BANCARIOS CHILE
======================================
Extrae descuentos de Banco de Chile y Banco Falabella
usando sus APIs internas (CMS).
"""

import requests
from datetime import datetime
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field


# ============================================
# MODELOS DE DATOS
# ============================================

@dataclass
class Beneficio:
    """Modelo de un beneficio bancario"""
    id: str
    banco: str
    tarjeta: str
    restaurante: str
    descuento_valor: float
    descuento_tipo: str
    descuento_texto: str
    dias_validos: List[str]
    horario_inicio: str = ""
    horario_fin: str = ""
    valido_desde: str = ""
    valido_hasta: str = ""
    ubicacion: str = ""
    ciudad: str = ""
    comuna: str = ""
    locales: List[str] = field(default_factory=list)
    compra_minima: int = 0
    tope_descuento: int = 0
    restricciones_texto: str = ""
    online: bool = False
    presencial: bool = True
    fecha_scrape: str = ""
    url_fuente: str = ""
    imagen_url: str = ""
    logo_url: str = ""
    direccion: str = ""
    activo: bool = True
    tags: List[str] = field(default_factory=list)
    descripcion: str = ""

    def __post_init__(self):
        self.fecha_scrape = self.fecha_scrape or datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)


@dataclass
class DescuentoBencina:
    """Modelo de un descuento de combustible"""
    id: str
    cadena: str              # "Copec", "Shell", "Aramco"
    banco: str               # "Banco Consorcio", "Mercado Pago", etc.
    tarjeta: str             # nombre de tarjeta/app
    descuento_por_litro: int # CLP por litro (ej: 100)
    descuento_texto: str     # "$100/L", "$50-$300/L"
    dias_validos: List[str]  # ["lunes"], ["lunes","martes","miercoles","jueves","viernes"]
    condicion: str = ""      # "App Aramco", "Micopiloto", etc.
    tope_litros: int = 0     # max litros por transaccion
    tope_monto: int = 0      # max CLP por mes
    combustible: str = ""    # "Bencina", "Diesel", "Todos"
    vigencia_mes: str = ""   # "2026-03" (YYYY-MM)
    valido_hasta: str = ""   # "31-Mar-2026"
    restricciones_texto: str = ""
    url_fuente: str = ""
    fecha_scrape: str = ""
    activo: bool = True
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.fecha_scrape = self.fecha_scrape or datetime.now().isoformat()
        if not self.vigencia_mes:
            self.vigencia_mes = datetime.now().strftime("%Y-%m")

    def to_dict(self):
        return asdict(self)


@dataclass
class EstacionBencina:
    """Ubicacion de una estacion de servicio con precios de combustible"""
    id: str
    nombre: str           # "Copec Av. Providencia"
    cadena: str           # "Copec", "Shell", "Aramco"
    direccion: str = ""
    comuna: str = ""
    region: str = ""
    latitud: float = 0.0
    longitud: float = 0.0
    servicios: List[str] = field(default_factory=list)
    # Precios de combustible (CLP por litro, 0 = no disponible)
    precio_93: int = 0
    precio_95: int = 0
    precio_97: int = 0
    precio_diesel: int = 0
    precio_kerosene: int = 0
    precio_fecha: str = ""    # Fecha ultima actualizacion de precios

    def to_dict(self):
        return asdict(self)


# ============================================
# SCRAPER BANCO DE CHILE (API CMS)
# ============================================

class ScraperBancoChile:
    """Scraper de Banco de Chile via API CMS interna"""

    API_URL = "https://sitiospublicos.bancochile.cl/api/content/spaces/personas/types/beneficios/entries"
    CATEGORY = "beneficios/sabores/restaurantes-y-bares"
    BANCO = "Banco de Chile"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae todos los beneficios de restaurantes via API"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (API CMS)...")

            # Primera página para saber el total
            page = 1
            per_page = 100
            total_pages = 1

            while page <= total_pages:
                params = {
                    'per_page': per_page,
                    'page': page,
                    'meta.category': self.CATEGORY,
                }
                response = self.session.get(self.API_URL, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

                meta = data.get('meta', {})
                total_pages = meta.get('total_pages', 1)
                total_entries = meta.get('total_entries', 0)

                if page == 1:
                    print(f"   Total beneficios disponibles: {total_entries}")

                entries = data.get('entries', [])
                for entry in entries:
                    beneficio = self._parsear_entry(entry)
                    if beneficio:
                        self.beneficios.append(beneficio)

                print(f"   Página {page}/{total_pages} procesada ({len(entries)} entries)")
                page += 1

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_entry(self, entry: dict) -> Optional[Beneficio]:
        """Parsea una entry del CMS a Beneficio"""
        try:
            meta = entry.get('meta', {})
            fields = entry.get('fields', {})

            nombre = fields.get('Titulo', meta.get('name', 'Desconocido'))
            tags = meta.get('tags', [])

            # Extraer descuento
            tipo_beneficio = fields.get('Tipo Beneficio', '')
            descuento_valor, descuento_texto = self._parsear_descuento(tipo_beneficio)

            # Extraer días de los tags
            dias_validos = self._extraer_dias(tags)

            # Extraer ubicación de sucursales
            sucursales_html = fields.get('Sucursales', '')
            locales, regiones, direcciones = self._parsear_sucursales(sucursales_html)

            # Extraer región de tags
            ubicacion = self._extraer_region(tags) or (regiones[0] if regiones else '')

            # Dirección del local
            direccion = direcciones[0] if direcciones else ''

            # Imágenes
            logo_data = fields.get('Logo', {})
            portada_data = fields.get('Portada', {})
            logo_url = logo_data.get('url', '') if isinstance(logo_data, dict) else ''
            imagen_url = portada_data.get('url', '') if isinstance(portada_data, dict) else ''

            # Vigencia
            vigencia = fields.get('Vigencia', '')
            valido_desde, valido_hasta = self._parsear_vigencia(vigencia)

            # Condiciones
            condiciones = fields.get('Condiciones Comerciales', '')

            # Tarjetas
            tarjetas = fields.get('Tarjetas Permitidas', [])
            tarjeta_str = ', '.join(tarjetas[:3]) if tarjetas else 'Tarjetas Banco de Chile'

            # URL
            slug = meta.get('slug', '')
            url = f"https://sitiospublicos.bancochile.cl/personas/beneficios/detalle/{slug}" if slug else ''

            # Keywords
            keywords = fields.get('Keywords', '')
            presencial = 'presencial' in keywords.lower() if keywords else True
            online_flag = 'online' in keywords.lower() if keywords else False

            beneficio_id = f"banchile_{meta.get('uuid', nombre.lower().replace(' ', '_'))}"

            return Beneficio(
                id=beneficio_id,
                banco=self.BANCO,
                tarjeta=tarjeta_str,
                restaurante=nombre,
                descuento_valor=descuento_valor,
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto or tipo_beneficio,
                dias_validos=dias_validos,
                valido_desde=valido_desde,
                valido_hasta=valido_hasta,
                ubicacion=ubicacion,
                locales=locales,
                restricciones_texto=condiciones[:300] if condiciones else vigencia[:200] if vigencia else '',
                presencial=presencial,
                online=online_flag,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                direccion=direccion,
                tags=tags,
                activo=True,
            )
        except Exception as e:
            return None

    def _parsear_descuento(self, texto: str) -> tuple:
        """Extrae valor y texto del descuento"""
        if not texto:
            return 0, ''
        match = re.search(r'(\d+)%', texto)
        valor = int(match.group(1)) if match else 0
        return valor, texto.strip()

    def _extraer_dias(self, tags: list) -> List[str]:
        """Extrae días válidos de los tags"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miercoles',
            'miércoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sabado': 'sabado', 'sábado': 'sabado', 'domingo': 'domingo',
        }
        dias = []
        for tag in tags:
            tag_lower = tag.lower().strip()
            if tag_lower in dias_map:
                dias.append(dias_map[tag_lower])
        return dias if dias else ['todos']

    def _extraer_region(self, tags: list) -> str:
        """Extrae región de los tags"""
        regiones_keywords = [
            'metropolitana', 'valparaíso', 'valparaiso', 'biobío', 'biobio',
            'araucanía', 'araucania', 'maule', 'coquimbo', 'antofagasta',
            'atacama', "o'higgins", 'ohiggins', 'los ríos', 'los rios',
            'los lagos', 'aysén', 'aysen', 'magallanes', 'arica', 'tarapacá',
            'ñuble', 'santiago',
        ]
        for tag in tags:
            tag_lower = tag.lower().strip()
            for keyword in regiones_keywords:
                if keyword in tag_lower:
                    return tag
        return ''

    def _parsear_sucursales(self, html: str) -> tuple:
        """Extrae locales, regiones y direcciones del HTML de sucursales"""
        if not html:
            return [], [], []
        locales = []
        regiones = []
        direcciones = []
        items = re.findall(r'<li>(.*?)</li>', html)
        for item in items:
            parts = [p.strip() for p in item.split(';') if p.strip() and p.strip() != 'VACIO']
            if len(parts) >= 1:
                # parts[0] puede ser dirección si solo hay un campo útil
                direccion = parts[0] if parts[0] != 'VACIO' else ''
                if direccion:
                    direcciones.append(direccion)
            if len(parts) >= 2:
                locales.append(parts[1] if len(parts) > 1 else parts[0])
                if len(parts) > 2:
                    regiones.append(parts[2])
        return locales, regiones, direcciones

    def _parsear_vigencia(self, texto: str) -> tuple:
        """Extrae fechas de vigencia"""
        if not texto:
            return '', ''
        # Buscar patrones de fecha
        fechas = re.findall(r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', texto)
        desde = fechas[0] if len(fechas) > 0 else ''
        hasta = fechas[-1] if len(fechas) > 0 else ''
        return desde, hasta


# ============================================
# SCRAPER BANCO FALABELLA (Contentful API)
# ============================================

class ScraperBancoFalabella:
    """Scraper de Banco Falabella via Contentful CMS"""

    CONTENTFUL_SPACE = "p6eyia4djstu"
    CONTENTFUL_ENV = "master"
    BANCO = "Banco Falabella"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.beneficios: List[Beneficio] = []
        self._access_token: Optional[str] = None

    def _obtener_token(self) -> Optional[str]:
        """Obtiene el access token de Contentful desde el sitio"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                token = None

                def capture_token(response):
                    nonlocal token
                    url = response.url
                    if 'cdn.contentful.com' in url and f'spaces/{self.CONTENTFUL_SPACE}' in url:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.query)
                        t = params.get('access_token', [None])[0]
                        if t:
                            token = t

                page.on('response', capture_token)
                page.goto('https://www.bancofalabella.cl/descuentos/restaurantes',
                          wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(5000)
                browser.close()
                return token
        except Exception as e:
            print(f"   ⚠️  No se pudo obtener token de Contentful: {e}")
            return None

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios usando Playwright para capturar datos de Contentful"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Contentful CMS)...")

            from playwright.sync_api import sync_playwright

            raw_data = None

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                def capture_data(response):
                    nonlocal raw_data
                    url = response.url
                    if 'orderedBenefits' in url and 'Todos' in url:
                        try:
                            raw_data = response.json()
                        except:
                            pass

                page.on('response', capture_data)
                page.goto('https://www.bancofalabella.cl/descuentos/restaurantes',
                          wait_until='domcontentloaded', timeout=25000)
                page.wait_for_timeout(8000)
                browser.close()

            if not raw_data:
                print(f"   ❌ No se capturaron datos de Contentful")
                return []

            # Construir mapa de assets (id → URL de imagen)
            assets = raw_data.get('includes', {}).get('Asset', [])
            asset_map = {}
            for a in assets:
                aid = a.get('sys', {}).get('id', '')
                file_info = a.get('fields', {}).get('file', {})
                url = file_info.get('url', '')
                if url and not url.startswith('http'):
                    url = 'https:' + url
                if aid and url:
                    asset_map[aid] = url
            print(f"   Assets mapeados: {len(asset_map)}")

            entries = raw_data.get('includes', {}).get('Entry', [])
            print(f"   Total entries capturadas: {len(entries)}")

            # Procesar newBenefits (formato nuevo)
            count_new = 0
            count_legacy = 0
            for entry in entries:
                ct = entry.get('sys', {}).get('contentType', {}).get('sys', {}).get('id', '')
                fields = entry.get('fields', {})

                if ct == 'newBenefits':
                    # Filtrar solo restaurantes
                    categories = fields.get('relatedCategory', [])
                    if 'Restaurantes' in categories:
                        beneficio = self._parsear_new_benefit(entry, asset_map)
                        if beneficio:
                            self.beneficios.append(beneficio)
                            count_new += 1

                elif ct == 'descuentos':
                    # Filtrar solo restaurantes
                    categories = fields.get('categoriaV2', [])
                    if 'Restaurantes' in categories:
                        beneficio = self._parsear_descuento_legacy(entry, asset_map)
                        if beneficio:
                            self.beneficios.append(beneficio)
                            count_legacy += 1

            print(f"   newBenefits (restaurantes): {count_new}")
            print(f"   descuentos legacy (restaurantes): {count_legacy}")
            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except ImportError:
            print(f"   ⚠️  Playwright no instalado. Instalando...")
            import subprocess
            subprocess.run(['pip', 'install', 'playwright'], capture_output=True)
            subprocess.run(['python3', '-m', 'playwright', 'install', 'chromium'], capture_output=True)
            return self.scrapear()
        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_new_benefit(self, entry: dict, asset_map: dict = None) -> Optional[Beneficio]:
        """Parsea un newBenefits entry"""
        try:
            fields = entry.get('fields', {})
            sys_data = entry.get('sys', {})
            asset_map = asset_map or {}

            nombre = fields.get('commerceName', fields.get('benefitTitle', 'Desconocido'))
            descuento_valor = fields.get('discount', 0) or 0

            top_text = fields.get('topDiscountText', '')
            center_text = fields.get('centerDiscountText', '')
            bottom_text = fields.get('bottomDiscountText', '')
            descuento_texto = f"{top_text} {center_text} {bottom_text}".strip()

            # Días
            dias_raw = fields.get('discountDays', [])
            dias_validos = self._normalizar_dias(dias_raw)

            # Tarjetas
            tarjetas = fields.get('creditCards', [])
            tarjeta_str = ', '.join(tarjetas[:3]) if tarjetas else 'CMR Falabella'

            # Región
            regiones = fields.get('region', [])
            ubicacion = regiones[0] if regiones else ''

            # Modo
            modos = fields.get('benefitsMode', [])
            presencial = 'Presencial' in modos
            online = 'Online' in modos or 'Delivery' in modos

            # Fechas
            valido_desde = fields.get('initDate', '')[:10] if fields.get('initDate') else ''
            valido_hasta = fields.get('endDate', '')[:10] if fields.get('endDate') else ''

            # URL
            permalink = fields.get('permalink', '')
            url = f"https://www.bancofalabella.cl/descuentos/detalle/{permalink}" if permalink else ''

            # Descripción
            descripcion = fields.get('commerceInfoDescription', '')
            card_desc = fields.get('cardDescription', '')

            # Legal
            legal = fields.get('legalText', '')

            # Imágenes (resolver asset IDs)
            card_img_ref = fields.get('cardImage', {}).get('sys', {}).get('id', '')
            card_logo_ref = fields.get('cardLogo', {}).get('sys', {}).get('id', '')
            imagen_url = asset_map.get(card_img_ref, '')
            logo_url = asset_map.get(card_logo_ref, '')

            entry_id = sys_data.get('id', nombre.lower().replace(' ', '_'))

            return Beneficio(
                id=f"falabella_{entry_id}",
                banco=self.BANCO,
                tarjeta=tarjeta_str,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                valido_desde=valido_desde,
                valido_hasta=valido_hasta,
                ubicacion=ubicacion,
                restricciones_texto=legal[:300] if legal else card_desc,
                presencial=presencial,
                online=online,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                activo=True,
                descripcion=descripcion,
            )
        except Exception as e:
            return None

    def _parsear_descuento_legacy(self, entry: dict, asset_map: dict = None) -> Optional[Beneficio]:
        """Parsea un descuentos (legacy) entry"""
        try:
            fields = entry.get('fields', {})
            sys_data = entry.get('sys', {})
            asset_map = asset_map or {}

            nombre = fields.get('empresaBeneficioV2', fields.get('nombreBeneficio', 'Desconocido'))
            subtitulo = fields.get('subtituloCajaV2', '')

            # Extraer descuento del subtítulo
            descuento_valor = 0
            match = re.search(r'(\d+)%', subtitulo)
            if match:
                descuento_valor = int(match.group(1))

            # Días
            dias_raw = fields.get('diasDescuento', [])
            dias_validos = self._normalizar_dias(dias_raw)

            # Región
            regiones = fields.get('region', [])
            ubicacion = regiones[0] if regiones else ''

            # Método de pago
            payment = fields.get('paymentMethodBenefit', [])
            tarjeta_str = ', '.join(payment) if payment else 'CMR Falabella'

            # Fechas
            valido_desde = fields.get('fechaIngresoV2', '')[:10] if fields.get('fechaIngresoV2') else ''
            valido_hasta = fields.get('fechaTerminoV2', '')[:10] if fields.get('fechaTerminoV2') else ''

            # URL
            permalink = fields.get('permalink', '')
            url = f"https://www.bancofalabella.cl/descuentos/detalle/{permalink}" if permalink else ''

            # Tipo beneficio
            tipo = fields.get('tipoBeneficio', [])

            # Imágenes legacy
            img_ref = fields.get('imagenCajaV2', {}).get('sys', {}).get('id', '')
            logo_ref = fields.get('logoCajaV2', {}).get('sys', {}).get('id', '')
            imagen_url = asset_map.get(img_ref, '')
            logo_url = asset_map.get(logo_ref, '')

            entry_id = sys_data.get('id', nombre.lower().replace(' ', '_'))

            return Beneficio(
                id=f"falabella_legacy_{entry_id}",
                banco=self.BANCO,
                tarjeta=tarjeta_str,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=subtitulo,
                dias_validos=dias_validos,
                valido_desde=valido_desde,
                valido_hasta=valido_hasta,
                ubicacion=ubicacion,
                restricciones_texto=', '.join(tipo) if tipo else '',
                presencial=True,
                online=False,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                activo=True,
            )
        except Exception as e:
            return None

    def _normalizar_dias(self, dias_raw: list) -> List[str]:
        """Normaliza los nombres de días"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes',
            'miércoles': 'miercoles', 'miercoles': 'miercoles',
            'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sabado': 'sabado',
            'domingo': 'domingo',
        }
        dias = []
        for d in dias_raw:
            d_lower = d.lower().strip()
            if d_lower in dias_map:
                dias.append(dias_map[d_lower])
        return dias if dias else ['todos']


# ============================================
# SCRAPER BCI (API REST bciplus.cl)
# ============================================

class ScraperBCI:
    """Scraper de BCI via API REST (Azure APIM)"""

    API_URL = "https://api.bciplus.cl/bff-loyalty-beneficios/v1/offers"
    SUBSCRIPTION_KEY = "fa981752762743668413b68821a43840"
    BANCO = "BCI"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Ocp-Apim-Subscription-Key': self.SUBSCRIPTION_KEY,
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de restaurantes via API"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (API REST)...")
            page = 1
            total_pages = 1

            while page <= total_pages:
                params = {'itemsPorPagina': 100, 'pagina': page}
                response = self.session.get(self.API_URL, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

                paginado = data.get('paginado', {})
                total_pages = paginado.get('totalPaginas', 1)

                if page == 1:
                    print(f"   Total ofertas: {paginado.get('cantidadTotal', 0)}")

                ofertas = data.get('ofertas', [])
                for oferta in ofertas:
                    # Filtrar solo restaurantes
                    tags = [t.get('nombre', '') for t in oferta.get('tags', [])]
                    if 'Restaurantes' not in tags:
                        continue
                    beneficio = self._parsear_oferta(oferta, tags)
                    if beneficio:
                        self.beneficios.append(beneficio)

                print(f"   Página {page}/{total_pages} procesada")
                page += 1

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_oferta(self, oferta: dict, tags: list) -> Optional[Beneficio]:
        """Parsea una oferta de la API a Beneficio"""
        try:
            comercio = oferta.get('comercio', {})
            nombre_comercio = comercio.get('nombre', oferta.get('titulo', 'Desconocido'))
            # Limpiar nombre: quitar " - Descuento", " - Cashback", etc
            nombre = re.sub(r'\s*-\s*(Descuento|Cashback|Cuotas).*$', '', nombre_comercio).strip()

            # Descuento
            descuento_valor = oferta.get('deal', {}).get('discount', {}).get('percentage', 0) or 0
            descuento_texto = f"{descuento_valor}% dcto." if descuento_valor > 0 else oferta.get('titulo', '')

            # Días de la semana desde tags
            dias_validos = self._extraer_dias(tags)

            # Modalidad desde tags
            presencial = 'Presencial' in tags
            online = 'Online' in tags

            # Fechas
            fecha_inicio = oferta.get('fechaInicio', '')[:10] if oferta.get('fechaInicio') else ''
            fecha_termino = oferta.get('fechaTermino', '')[:10] if oferta.get('fechaTermino') else ''

            # Imágenes
            imagenes = oferta.get('imagenes', {})
            imagen_url = imagenes.get('imagen1', '')

            # URL
            slug = oferta.get('slug', '')
            url = f"https://www.bci.cl/beneficios/beneficios-bci/detalle/{slug}" if slug else ''

            # Descripción
            descripcion = oferta.get('descripcion', '')[:200]

            # Región desde título
            ubicacion = self._extraer_region_titulo(oferta.get('titulo', ''))

            oferta_id = oferta.get('id', nombre.lower().replace(' ', '_'))

            return Beneficio(
                id=f"bci_{oferta_id}",
                banco=self.BANCO,
                tarjeta="Tarjetas de Crédito BCI",
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                valido_desde=fecha_inicio,
                valido_hasta=fecha_termino,
                ubicacion=ubicacion,
                presencial=presencial,
                online=online,
                url_fuente=url,
                imagen_url=imagen_url,
                descripcion=descripcion,
                activo=True,
            )
        except Exception as e:
            return None

    def _extraer_dias(self, tags: list) -> List[str]:
        """Extrae días válidos de los tags de BCI"""
        dias_map = {
            'Lunes': 'lunes', 'Martes': 'martes', 'Miércoles': 'miercoles',
            'Miercoles': 'miercoles', 'Jueves': 'jueves', 'Viernes': 'viernes',
            'Sábado': 'sabado', 'Sabado': 'sabado', 'Domingo': 'domingo',
        }
        dias = [dias_map[t] for t in tags if t in dias_map]
        return dias if dias else ['todos']

    def _extraer_region_titulo(self, titulo: str) -> str:
        """Intenta extraer ubicación del título de la oferta"""
        regiones = {
            'santiago': 'Metropolitana', 'providencia': 'Metropolitana',
            'las condes': 'Metropolitana', 'vitacura': 'Metropolitana',
            'ñuñoa': 'Metropolitana', 'la reina': 'Metropolitana',
            'viña del mar': 'Valparaíso', 'vina del mar': 'Valparaíso',
            'valparaiso': 'Valparaíso', 'valparaíso': 'Valparaíso',
            'concepción': 'Biobío', 'concepcion': 'Biobío',
            'la serena': 'Coquimbo', 'antofagasta': 'Antofagasta',
            'temuco': 'Araucanía', 'puerto montt': 'Los Lagos',
            'rancagua': "O'Higgins", 'talca': 'Maule',
            'maitencillo': 'Valparaíso', 'reñaca': 'Valparaíso',
            'pucón': 'Araucanía', 'pucon': 'Araucanía',
        }
        titulo_lower = titulo.lower()
        for keyword, region in regiones.items():
            if keyword in titulo_lower:
                return region
        return ''


# ============================================
# SCRAPER ITAÚ (HTML WordPress)
# ============================================

class ScraperItau:
    """Scraper de Itaú via Playwright (Cloudflare-protected WordPress)"""

    LISTING_URL = "https://itaubeneficios.cl/beneficios/beneficios-y-descuentos/ruta-gourmet/"
    BANCO = "Banco Itaú"

    def __init__(self):
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de la Ruta Gourmet Itaú usando Playwright"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Playwright + Cloudflare)...")

            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox'],
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='es-CL',
                )
                page = context.new_page()
                page.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
                page.goto(self.LISTING_URL, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(12000)
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('a.beneficio__item')
            print(f"   Tarjetas encontradas: {len(cards)}")

            for card in cards:
                beneficio = self._parsear_card(card)
                if beneficio:
                    self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except ImportError:
            print(f"   ⚠️  Playwright/bs4 no instalado. Instalando...")
            import subprocess
            subprocess.run(['pip', 'install', 'playwright', 'beautifulsoup4'], capture_output=True)
            subprocess.run(['python3', '-m', 'playwright', 'install', 'chromium'], capture_output=True)
            return self.scrapear()
        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_card(self, card) -> Optional[Beneficio]:
        """Parsea una tarjeta HTML a Beneficio"""
        try:
            # Nombre
            title_el = card.select_one('h2.beneficio__item__info-location__title')
            nombre = title_el.get_text(strip=True) if title_el else card.get('title', 'Desconocido')

            # URL detalle
            url = card.get('href', '')

            # Ubicación
            addr_el = card.select_one('p.beneficio__item__info-location__address')
            ubicacion_raw = addr_el.get_text(strip=True) if addr_el else ''
            # Separar comuna y región
            ubicacion = self._normalizar_ubicacion(ubicacion_raw)

            # Modalidad
            details_el = card.select_one('p.beneficio__item__info-location__details')
            modalidad = details_el.get_text(strip=True) if details_el else 'Presencial'
            presencial = 'presencial' in modalidad.lower()
            online = 'online' in modalidad.lower() or 'delivery' in modalidad.lower()

            # Descuento
            discount_el = (card.select_one('p.beneficio__item__info-discount-pb__discount')
                          or card.select_one('p.beneficio__item__info-discount-pb-text__discount'))
            descuento_raw = discount_el.get_text(strip=True) if discount_el else ''
            descuento_valor = 0
            match = re.search(r'(\d+)', descuento_raw)
            if match:
                descuento_valor = int(match.group(1))
            descuento_texto = f"{descuento_valor}% dcto." if descuento_valor > 0 else descuento_raw

            # Tarjeta
            card_img = card.select_one('.beneficio__item__info-discount-pb__logo img')
            tarjeta = card_img.get('alt', 'Tarjeta Itaú') if card_img else 'Tarjeta Itaú'

            # Día gourmet
            cat_el = card.select_one('p.beneficio__item__category__name')
            dia_gourmet = cat_el.get_text(strip=True) if cat_el else ''
            dias_validos = self._extraer_dia_gourmet(dia_gourmet)

            # Logo
            logo_el = card.select_one('.beneficio__item__logo img')
            logo_url = logo_el.get('src', '') if logo_el else ''

            # Imagen de fondo
            bg_el = card.select_one('.beneficio__item__background')
            imagen_url = ''
            if bg_el and bg_el.get('style'):
                bg_match = re.search(r'url\((.*?)\)', bg_el.get('style', ''))
                if bg_match:
                    imagen_url = bg_match.group(1).strip('"').strip("'")

            tarjeta_key = re.sub(r'[^a-z0-9]', '', tarjeta.lower())
            beneficio_id = re.sub(r'[^a-z0-9]', '_', nombre.lower())

            return Beneficio(
                id=f"itau_{beneficio_id}_{tarjeta_key}",
                banco=self.BANCO,
                tarjeta=tarjeta,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                ubicacion=ubicacion,
                direccion=ubicacion_raw,
                presencial=presencial,
                online=online,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                activo=True,
                descripcion=f"Ruta Gourmet Itaú - {dia_gourmet}",
            )
        except Exception as e:
            return None

    def _extraer_dia_gourmet(self, dia_gourmet: str) -> List[str]:
        """Extrae el día de la semana del nombre del gourmet"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miercoles',
            'miércoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sabado': 'sabado', 'sábado': 'sabado', 'domingo': 'domingo',
        }
        dia_lower = dia_gourmet.lower()
        for keyword, dia in dias_map.items():
            if keyword in dia_lower:
                return [dia]
        return ['todos']

    def _normalizar_ubicacion(self, raw: str) -> str:
        """Normaliza ubicación: 'Vitacura, RM' -> 'Metropolitana'"""
        regiones_map = {
            'rm': 'Metropolitana', 'r.m.': 'Metropolitana',
            'región metropolitana': 'Metropolitana',
            'valparaíso': 'Valparaíso', 'valparaiso': 'Valparaíso',
            'biobío': 'Biobío', 'biobio': 'Biobío',
            'concepción': 'Biobío', 'concepcion': 'Biobío',
            'la serena': 'Coquimbo', 'coquimbo': 'Coquimbo',
        }
        raw_lower = raw.lower().strip()
        for keyword, region in regiones_map.items():
            if keyword in raw_lower:
                return region
        # Si termina en ", XX" usar la parte completa como ubicación
        return raw


# ============================================
# SCRAPER SCOTIABANK (JS embebido en HTML)
# ============================================

class ScraperScotiabank:
    """Scraper de Scotiabank via JS embebido (ScotiaRewards)"""

    PAGE_URL = "https://www.scotiarewards.cl/scclubfront/categoria/platosycomida/rutagourmet"
    IMAGE_BASE = "https://www.scotiarewards.cl/scclubfront"
    BANCO = "Scotiabank"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de Ruta Gourmet Scotiabank"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (JS embebido)...")

            response = self.session.get(self.PAGE_URL, timeout=20)
            response.raise_for_status()
            html = response.text

            # Extraer arrays JS: sitiosSantiago y sitiosRegiones
            sitios_stgo = self._extraer_array_js(html, 'sitiosSantiago')
            sitios_reg = self._extraer_array_js(html, 'sitiosRegiones')

            print(f"   Santiago: {len(sitios_stgo)} restaurantes")
            print(f"   Regiones: {len(sitios_reg)} restaurantes")

            for sitio in sitios_stgo:
                beneficio = self._parsear_sitio(sitio, es_santiago=True)
                if beneficio:
                    self.beneficios.append(beneficio)

            for sitio in sitios_reg:
                beneficio = self._parsear_sitio(sitio, es_santiago=False)
                if beneficio:
                    self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _extraer_array_js(self, html: str, var_name: str) -> list:
        """Extrae un array JS embebido del HTML"""
        try:
            # Buscar: const varName = [...];
            pattern = rf'const\s+{var_name}\s*=\s*(\[.*?\]);'
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                print(f"   ⚠️  No se encontró {var_name}")
                return []
            raw = match.group(1)
            # Limpiar para JSON válido: reemplazar comillas simples, trailing commas
            # El JS usa comillas dobles en general, pero puede tener caracteres especiales
            data = json.loads(raw)
            return data
        except json.JSONDecodeError:
            # Intentar limpiar el JSON
            try:
                # Remover trailing commas antes de ] o }
                cleaned = re.sub(r',\s*([\]}])', r'\1', raw)
                data = json.loads(cleaned)
                return data
            except:
                print(f"   ⚠️  Error parseando {var_name}")
                return []

    def _parsear_sitio(self, sitio: dict, es_santiago: bool) -> Optional[Beneficio]:
        """Parsea un sitio de ScotiaRewards a Beneficio"""
        try:
            nombre = sitio.get('nombre', 'Desconocido')
            direccion = sitio.get('direccion', '')

            # telefono es realmente el descuento
            descuento_raw = sitio.get('telefono', '')
            descuento_valor = 0
            match = re.search(r'(\d+)%', descuento_raw)
            if match:
                descuento_valor = int(match.group(1))

            # especialidad es el día
            especialidad = sitio.get('especialidad', '')
            dias_validos = self._extraer_dias(especialidad)

            # Imagen
            imagen_rel = sitio.get('imagen', '')
            imagen_url = f"{self.IMAGE_BASE}{imagen_rel}" if imagen_rel else ''

            # Parsear descripcion (pipe-delimited)
            descripcion_raw = sitio.get('descripcion', '')
            vigencia, comuna, condiciones = self._parsear_descripcion(descripcion_raw)

            # Región siempre desde id_region
            id_region = sitio.get('id_region', 0)
            ubicacion = 'Metropolitana' if es_santiago else self._region_por_id(id_region)

            sitio_id = sitio.get('id_sitio', nombre.lower().replace(' ', '_'))

            return Beneficio(
                id=f"scotiabank_{sitio_id}",
                banco=self.BANCO,
                tarjeta="Tarjetas Scotiabank",
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_raw,
                dias_validos=dias_validos,
                valido_hasta=vigencia,
                ubicacion=ubicacion,
                direccion=direccion,
                presencial=True,
                online=False,
                url_fuente=self.PAGE_URL,
                imagen_url=imagen_url,
                restricciones_texto=condiciones[:300] if condiciones else '',
                activo=True,
            )
        except Exception as e:
            return None

    def _extraer_dias(self, especialidad: str) -> List[str]:
        """Extrae días de la especialidad ('Todos los lunes' -> ['lunes'])"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miercoles',
            'miércoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sabado': 'sabado', 'sábado': 'sabado', 'domingo': 'domingo',
        }
        esp_lower = especialidad.lower().strip()
        if 'todos los dias' in esp_lower or 'todos los días' in esp_lower:
            return ['todos']
        dias = [dia for keyword, dia in dias_map.items() if keyword in esp_lower]
        return dias if dias else ['todos']

    def _parsear_descripcion(self, desc: str) -> tuple:
        """Parsea campo descripcion pipe-delimited -> (vigencia, ubicacion, condiciones)"""
        if not desc:
            return '', '', ''
        parts = desc.split('|')
        vigencia = ''
        ubicacion = ''
        condiciones = ''

        if len(parts) >= 1:
            # Parte 0: vigencia
            v = re.sub(r'<[^>]+>', '', parts[0]).strip()
            # Extraer fecha
            fecha_match = re.search(r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', v)
            if fecha_match:
                vigencia = fecha_match.group(1)
        if len(parts) >= 3:
            # Parte 2: comuna/ubicación
            ubicacion = re.sub(r'<[^>]+>', '', parts[2]).strip()
        if len(parts) >= 5:
            # Parte 4: condiciones legales
            condiciones = re.sub(r'<[^>]+>', '', parts[4]).strip()

        return vigencia, ubicacion, condiciones

    def _region_por_id(self, id_region: int) -> str:
        """Mapea id_region chileno a nombre"""
        regiones = {
            1: 'Tarapacá', 2: 'Antofagasta', 3: 'Atacama', 4: 'Coquimbo',
            5: 'Valparaíso', 6: "O'Higgins", 7: 'Maule', 8: 'Biobío',
            9: 'Araucanía', 10: 'Los Lagos', 11: 'Aysén', 12: 'Magallanes',
            13: 'Metropolitana', 14: 'Los Ríos', 15: 'Arica y Parinacota',
            16: 'Ñuble',
        }
        return regiones.get(id_region, '')


# ============================================
# SCRAPER SANTANDER (HTML SSR, Modyo CMS)
# ============================================

class ScraperSantander:
    """Scraper de Santander via HTML estático (SSR)"""

    BASE_URL = "https://banco.santander.cl/beneficios/promociones"
    DETAIL_BASE = "https://banco.santander.cl"
    BANCO = "Santander"
    MAX_PAGES = 25

    RESTAURANT_KEYWORDS = [
        'restaurante', 'restaurant', 'comida', 'gastronomía', 'gastronom',
        'pizza', 'sushi', 'burger', 'café', 'cafe', 'bar ', 'pub ',
        'parrilla', 'grill', 'cocina', 'menú', 'menu', 'delivery',
        'cena', 'almuerzo', 'brunch', 'food', 'gourmet', 'sabores',
        'starbucks', 'mcdonald', 'papa john', 'domino', 'subway',
        'juan maestro', 'doggis', 'tarragona', 'bravissimo', 'telepizza',
        'cencosud', 'rappi', 'uber eats', 'pedidosya', 'ifood',
    ]

    def __init__(self):
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de restaurantes de Santander (Playwright para bypass 403)"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Playwright)...")
            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup

            total_items = 0

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                )
                page = context.new_page()

                for page_num in range(1, self.MAX_PAGES + 1):
                    url = f"{self.BASE_URL}?page={page_num}"
                    try:
                        page.goto(url, wait_until='domcontentloaded', timeout=15000)
                        page.wait_for_timeout(1500)
                    except Exception:
                        break

                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    items = soup.select('li.item')

                    if not items:
                        break

                    for item in items:
                        total_items += 1
                        beneficio = self._parsear_item(item)
                        if beneficio:
                            self.beneficios.append(beneficio)

                    if page_num % 5 == 0 or page_num == 1:
                        print(f"   Página {page_num}: {len(self.beneficios)} restaurantes de {total_items} items")

                browser.close()

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios de {total_items} total")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_item(self, item) -> Optional[Beneficio]:
        """Parsea un item HTML a Beneficio si es restaurante"""
        try:
            title_el = item.select_one('h4 a') or item.select_one('h3 a') or item.select_one('a')
            if not title_el:
                return None
            nombre = title_el.get_text(strip=True)
            href = title_el.get('href', '')
            slug = href.rstrip('/').split('/')[-1] if href else ''
            url = f"{self.DETAIL_BASE}{href}" if href and href.startswith('/') else href

            desc_el = item.select_one('p') or item.select_one('.description')
            descripcion = desc_el.get_text(strip=True) if desc_el else ''

            img_el = item.select_one('img')
            imagen_url = ''
            if img_el:
                src = img_el.get('src', '') or img_el.get('data-src', '')
                if src:
                    imagen_url = src if src.startswith('http') else f"{self.DETAIL_BASE}{src}"

            texto_buscar = f"{nombre} {descripcion}".lower()
            es_restaurante = any(kw in texto_buscar for kw in self.RESTAURANT_KEYWORDS)
            if not es_restaurante:
                return None

            descuento_valor = 0
            match = re.search(r'(\d+)\s*%', f"{nombre} {descripcion}")
            if match:
                descuento_valor = int(match.group(1))
            descuento_texto = f"{descuento_valor}% dcto." if descuento_valor > 0 else descripcion[:100]

            beneficio_id = f"santander_{slug or re.sub(r'[^a-z0-9]', '_', nombre.lower()[:40])}"

            return Beneficio(
                id=beneficio_id,
                banco=self.BANCO,
                tarjeta="Tarjetas Santander",
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=['todos'],
                ubicacion='',
                presencial=True,
                online=False,
                url_fuente=url,
                imagen_url=imagen_url,
                descripcion=descripcion[:200],
                activo=True,
            )
        except Exception:
            return None


# ============================================
# SCRAPER CONSORCIO (API Modyo CMS)
# ============================================

class ScraperConsorcio:
    """Scraper de Banco Consorcio via API Modyo CMS"""

    API_URL = "https://sitio.consorcio.cl/api/content/spaces/grupo-consorcio-cim/types/tab-card-credit-card/entries"
    BANCO = "Banco Consorcio"

    RESTAURANT_KEYWORDS = [
        'restaurante', 'restaurant', 'comida', 'gastronomía', 'gastronom',
        'pizza', 'sushi', 'burger', 'café', 'cafe', 'bar',
        'parrilla', 'grill', 'cocina', 'food', 'gourmet',
        'casacostanera', 'casa costanera', 'sabores', 'cena',
        'almuerzo', 'delivery', 'comer',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de restaurantes de Consorcio"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (API Modyo CMS)...")

            params = {'per_page': 100}
            response = self.session.get(self.API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            entries = data.get('entries', [])
            print(f"   Total entries: {len(entries)}")

            for entry in entries:
                beneficio = self._parsear_entry(entry)
                if beneficio:
                    self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_entry(self, entry: dict) -> Optional[Beneficio]:
        """Parsea una entry del CMS a Beneficio si es restaurante"""
        try:
            fields = entry.get('fields', {})
            meta = entry.get('meta', {})

            nombre = fields.get('title_card', 'Desconocido')
            subtitulo = fields.get('subtitle_card', '')
            complemento = fields.get('complement_card', '')
            activa = fields.get('active_card', True)
            body_html = fields.get('card_body', '')

            if not activa:
                return None

            texto = f"{nombre} {subtitulo} {complemento} {body_html}".lower()
            es_restaurante = any(kw in texto for kw in self.RESTAURANT_KEYWORDS)
            if not es_restaurante:
                return None

            descuento_valor = 0
            match = re.search(r'(\d+)\s*%', f"{nombre} {subtitulo}")
            if match:
                descuento_valor = int(match.group(1))
            descuento_texto = f"{descuento_valor}% dcto." if descuento_valor > 0 else subtitulo[:100]

            descripcion = re.sub(r'<[^>]+>', ' ', body_html).strip()[:200] if body_html else ''

            img_data = fields.get('image_desktop', {})
            imagen_url = ''
            if isinstance(img_data, dict):
                imagen_url = img_data.get('url', '')
            elif isinstance(img_data, str):
                imagen_url = img_data

            entry_id = meta.get('uuid', re.sub(r'[^a-z0-9]', '_', nombre.lower()[:40]))

            return Beneficio(
                id=f"consorcio_{entry_id}",
                banco=self.BANCO,
                tarjeta="Tarjetas Consorcio",
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "cashback",
                descuento_texto=descuento_texto,
                dias_validos=['todos'],
                ubicacion=complemento or '',
                presencial=True,
                online=False,
                url_fuente="https://sitio.consorcio.cl/beneficios",
                imagen_url=imagen_url,
                descripcion=descripcion,
                activo=True,
            )
        except Exception:
            return None


# ============================================
# SCRAPER BANCO ESTADO (Playwright + Akamai)
# ============================================

class ScraperBancoEstado:
    """Scraper de BancoEstado via Playwright + Stealth (Akamai WAF)"""

    PAGE_URL = "https://www.bancoestado.cl/content/bancoestado-public/cl/es/home/home/todosuma---bancoestado-personas/un-mes-de-sabores---bancoestado-personas.html"
    BANCO = "BancoEstado"

    def __init__(self):
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de Un Mes de Sabores BancoEstado"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Playwright + Stealth)...")

            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
            from bs4 import BeautifulSoup

            stealth = Stealth()

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox'],
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='es-CL',
                )
                page = context.new_page()
                stealth.apply_stealth_sync(page)
                page.goto(self.PAGE_URL, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(10000)
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.select('div[data-card-id]')
            print(f"   Cards encontradas: {len(cards)}")

            for card in cards:
                beneficio = self._parsear_card(card)
                if beneficio:
                    self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_card(self, card) -> Optional[Beneficio]:
        """Parsea una card con data-attributes a Beneficio"""
        try:
            card_id = card.get('data-card-id', '')
            nombre = card.get('data-name', 'Desconocido')
            tarjeta_raw = card.get('data-tarjeta', '')
            oferta_raw = card.get('data-oferta', '')

            subfiltros_raw = card.get('data-subfiltros', '{}')
            subfiltros = {}
            try:
                subfiltros = json.loads(subfiltros_raw) if subfiltros_raw else {}
            except (json.JSONDecodeError, TypeError):
                pass

            # Days from subfiltros
            dias_raw = subfiltros.get('dia', [])
            if isinstance(dias_raw, str):
                dias_raw = [dias_raw]
            dias_validos = self._normalizar_dias(dias_raw) if dias_raw else ['todos']

            # Zone from subfiltros
            zonas = subfiltros.get('zona', [])
            if isinstance(zonas, str):
                zonas = [zonas]
            ubicacion = zonas[0] if zonas else ''

            # Discount: can be in data-oferta or data-tarjeta
            # data-tarjeta might be "50% dto." or card type like "Menú Priceless"
            descuento_valor = 0
            descuento_texto = ''
            tarjeta = 'Tarjetas BancoEstado'

            # Check data-tarjeta for discount
            match_t = re.search(r'(\d+)\s*%', tarjeta_raw)
            match_o = re.search(r'(\d+)\s*%', oferta_raw)

            if match_t and 'dto' in tarjeta_raw.lower():
                descuento_valor = int(match_t.group(1))
                descuento_texto = tarjeta_raw.strip()
                tarjeta = 'Tarjetas BancoEstado'
            elif match_o:
                descuento_valor = int(match_o.group(1))
                descuento_texto = oferta_raw.strip()
                tarjeta = tarjeta_raw if tarjeta_raw else 'Tarjetas BancoEstado'
            elif tarjeta_raw:
                descuento_texto = tarjeta_raw.strip()
                tarjeta = 'Tarjetas BancoEstado'
            else:
                descuento_texto = oferta_raw.strip() or 'Ver detalle'

            # Image
            img_el = card.select_one('img')
            imagen_url = ''
            if img_el:
                src = img_el.get('src', '') or img_el.get('data-src', '')
                if src and not src.startswith('http'):
                    src = f"https://www.bancoestado.cl{src}"
                imagen_url = src

            return Beneficio(
                id=f"bancoestado_{card_id or re.sub(r'[^a-z0-9]', '_', nombre.lower()[:40])}",
                banco=self.BANCO,
                tarjeta=tarjeta,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                ubicacion=ubicacion,
                presencial=True,
                online=False,
                url_fuente=self.PAGE_URL,
                imagen_url=imagen_url,
                activo=True,
            )
        except Exception:
            return None

    def _normalizar_dias(self, dias_raw: list) -> List[str]:
        """Normaliza nombres de días"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sabado': 'sabado', 'domingo': 'domingo',
            'todos los días': 'todos',
        }
        dias = []
        for d in dias_raw:
            d_lower = d.lower().strip()
            if d_lower in dias_map:
                mapped = dias_map[d_lower]
                if mapped == 'todos':
                    return ['todos']
                dias.append(mapped)
        return dias if dias else ['todos']


# ============================================
# SCRAPER BANCO SECURITY (Drupal JSON:API)
# ============================================

class ScraperBancoSecurity:
    """Scraper de Banco Security via Drupal JSON:API"""

    API_URL = "https://personas.bancosecurity.cl/jsonapi/node/beneficio"
    BANCO = "Banco Security"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/vnd.api+json',
        })
        self.beneficios: List[Beneficio] = []

    # Categorías de comida: Gourmet=116, Restaurantes=121, Comida Rápida=206
    FOOD_TIDS = [116, 121, 206]

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de comida de Banco Security (3 categorías)"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Drupal JSON:API)...")

            seen_ids = set()
            total_fetched = 0

            for tid in self.FOOD_TIDS:
                offset = 0
                limit = 50
                while True:
                    params = {
                        'filter[status][value]': '1',
                        'filter[field_categorias_beneficio.drupal_internal__tid]': str(tid),
                        'include': 'field_categorias_beneficio,field_dias_de_aplicacion',
                        'page[limit]': str(limit),
                        'page[offset]': str(offset),
                    }

                    response = self.session.get(self.API_URL, params=params, timeout=20)
                    response.raise_for_status()
                    data = response.json()

                    items = data.get('data', [])
                    included = data.get('included', [])

                    if not items:
                        break

                    # Build included map
                    included_map = {}
                    for inc in included:
                        inc_id = inc.get('id', '')
                        if inc_id:
                            included_map[inc_id] = inc

                    for item in items:
                        item_id = item.get('id', '')
                        if item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)
                        beneficio = self._parsear_item(item, included_map)
                        if beneficio:
                            self.beneficios.append(beneficio)

                    total_fetched += len(items)

                    if len(items) < limit:
                        break
                    offset += limit

                print(f"   tid={tid}: {len(self.beneficios)} beneficios acumulados")

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios de {total_fetched} total")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_item(self, item: dict, included_map: dict) -> Optional[Beneficio]:
        """Parsea un item JSON:API a Beneficio"""
        try:
            attrs = item.get('attributes', {})
            rels = item.get('relationships', {})

            nombre = attrs.get('field_nombre_marca', attrs.get('title', 'Desconocido'))

            # Discount
            descuento_valor = attrs.get('field_porcentaje_descuento', 0) or 0
            descuento_texto = f"{descuento_valor}% dcto." if descuento_valor > 0 else ''

            # Card type
            tarjeta = attrs.get('field_tipo_de_tarjeta', '') or 'Tarjetas Security'

            # Vigencia — puede ser dict {'value': '2025-08-01', 'end_value': '2025-08-31'} o string
            vigencia_raw = attrs.get('field_vigencia_beneficio', '') or ''
            valido_desde = ''
            valido_hasta = ''
            restricciones_vig = ''
            if isinstance(vigencia_raw, dict):
                valido_desde = vigencia_raw.get('value', '')
                valido_hasta = vigencia_raw.get('end_value', '')
            elif isinstance(vigencia_raw, str) and vigencia_raw:
                restricciones_vig = vigencia_raw
                fechas = re.findall(r'(\d{1,2}\s+de\s+\w+(?:\s+de\s+\d{4})?)', vigencia_raw)
                if len(fechas) >= 2:
                    valido_desde = fechas[0]
                    valido_hasta = fechas[-1]
                elif len(fechas) == 1:
                    valido_hasta = fechas[0]

            # Address and location
            direccion = attrs.get('field_direccion_establecimiento_', '') or ''
            ubicacion_caluga = attrs.get('field_ubicacion_caluga', '') or ''

            # Days from relationship
            dias_validos = ['todos']
            dias_rel = rels.get('field_dias_de_aplicacion', {}).get('data', [])
            if isinstance(dias_rel, list) and dias_rel:
                dias = []
                for d_ref in dias_rel:
                    d_id = d_ref.get('id', '')
                    if d_id in included_map:
                        d_name = included_map[d_id].get('attributes', {}).get('name', '')
                        dia = self._normalizar_dia(d_name)
                        if dia:
                            dias.append(dia)
                if dias:
                    dias_validos = dias

            # URL from path alias
            path_info = attrs.get('path', {})
            path_alias = path_info.get('alias', '') if isinstance(path_info, dict) else ''
            url = f"https://personas.bancosecurity.cl{path_alias}" if path_alias else 'https://personas.bancosecurity.cl/beneficios'

            item_id = item.get('id', re.sub(r'[^a-z0-9]', '_', nombre.lower()[:30]))

            return Beneficio(
                id=f"security_{item_id[:50]}",
                banco=self.BANCO,
                tarjeta=tarjeta,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                valido_desde=valido_desde,
                valido_hasta=valido_hasta,
                ubicacion=ubicacion_caluga,
                direccion=direccion,
                presencial=True,
                online=False,
                url_fuente=url,
                restricciones_texto=restricciones_vig[:200] if restricciones_vig else '',
                activo=True,
            )
        except Exception:
            return None

    def _normalizar_dia(self, nombre: str) -> str:
        """Normaliza un día de la semana"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sabado': 'sabado', 'domingo': 'domingo',
        }
        return dias_map.get(nombre.lower().strip(), '')


# ============================================
# SCRAPER BANCO RIPLEY (API interna)
# ============================================

class ScraperBancoRipley:
    """Scraper de Banco Ripley via API interna (Angular + Firebase)"""

    API_URL = "https://www.bancoripley.cl/api/call-sp-api"
    BANCO = "Banco Ripley"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://www.bancoripley.cl',
            'Referer': 'https://www.bancoripley.cl/beneficios-y-promociones',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de restaurantes de Banco Ripley"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (API interna)...")

            headers = {
                **dict(self.session.headers),
                'x-path-api': '/api/sp/beneficios/get-activeBox-beneficio',
                'x-method-api': 'POST',
                'Content-Type': 'application/x-www-form-urlencoded',
            }

            response = self.session.post(
                self.API_URL,
                headers=headers,
                data='idSection=restofans',
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            # Navigate response structure
            items = self._extract_items(data)
            print(f"   Items encontrados: {len(items)}")

            for item in items:
                beneficio = self._parsear_item(item)
                if beneficio:
                    self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error API directa {self.BANCO}: {e}")
            print(f"   🔄 Intentando fallback con Playwright...")
            return self._scrape_playwright_fallback()

    def _extract_items(self, data) -> list:
        """Navega la estructura de respuesta: {success, haveData, data: [{config, items: [...]}]}"""
        if isinstance(data, dict):
            # Ripley structure: data[0]['items']
            data_list = data.get('data')
            if isinstance(data_list, list):
                for entry in data_list:
                    if isinstance(entry, dict) and 'items' in entry:
                        items = entry['items']
                        if isinstance(items, list):
                            return items
                return data_list
            # Fallback: try other keys
            for key in ['result', 'items', 'beneficios', 'body']:
                val = data.get(key)
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    return self._extract_items(val)
        if isinstance(data, list):
            return data
        return []

    def _scrape_playwright_fallback(self) -> List[Beneficio]:
        """Fallback usando Playwright para interceptar API"""
        try:
            from playwright.sync_api import sync_playwright

            captured_data = []

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                def capture(response):
                    if 'call-sp-api' in response.url and response.status == 200:
                        try:
                            captured_data.append(response.json())
                        except Exception:
                            pass

                page.on('response', capture)
                page.goto('https://www.bancoripley.cl/beneficios-y-promociones',
                          wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(8000)

                # Try clicking restaurant tab
                try:
                    page.click('text=Restaurantes', timeout=3000)
                    page.wait_for_timeout(3000)
                except Exception:
                    pass

                browser.close()

            for data in captured_data:
                items = self._extract_items(data)
                for item in items:
                    beneficio = self._parsear_item(item)
                    if beneficio:
                        self.beneficios.append(beneficio)

            print(f"   Playwright fallback: {len(self.beneficios)} beneficios")
            return self.beneficios
        except Exception as e:
            print(f"   ❌ Fallback también falló: {e}")
            return self.beneficios

    @staticmethod
    def _val(param):
        """Extrae value de un param dict {'nombre': '...', 'value': X} o retorna string directo"""
        if isinstance(param, dict):
            return str(param.get('value', '')).strip()
        return str(param).strip() if param else ''

    def _parsear_item(self, item: dict) -> Optional[Beneficio]:
        """Parsea un item de la API de Ripley a Beneficio
        Estructura: {config, nombre, params: {txtNameComercio: {nombre, value}, ...}}
        """
        try:
            params = item.get('params', {})

            # Name
            nombre = self._val(params.get('txtNameComercio'))
            if not nombre:
                return None

            # Discount
            descuento_raw = self._val(params.get('txtDescuento'))
            descuento_valor = 0
            match = re.search(r'(\d+)', descuento_raw)
            if match:
                descuento_valor = int(match.group(1))

            # Location from txtDetalleCard (e.g. "R.M. (Vitacura)")
            ubicacion = self._val(params.get('txtDetalleCard'))

            # Days from txtValidezBeneficio (e.g. "Jueves", "Lunes a Viernes")
            validez_dias = self._val(params.get('txtValidezBeneficio'))
            dias_validos = self._parsear_dias_ripley(validez_dias) if validez_dias else ['todos']

            # Vigencia from details.arrVigencia or txtVigenciaDetalle
            vigencia = self._val(params.get('txtVigenciaDetalle'))
            if not vigencia:
                vigencia = self._val(params.get('txtVigenciaCard'))
            # Try to get vigencia from details
            details = params.get('details', {})
            if isinstance(details, dict):
                arr_vig = details.get('arrVigencia', {})
                if isinstance(arr_vig, dict):
                    arr = arr_vig.get('array', [])
                    if arr and isinstance(arr, list):
                        vigencia = self._val(arr[0].get('txtItem', '')) or vigencia

            # Address from details.arrDireccion
            direccion = ''
            if isinstance(details, dict):
                arr_dir = details.get('arrDireccion', {})
                if isinstance(arr_dir, dict):
                    arr = arr_dir.get('array', [])
                    if arr and isinstance(arr, list):
                        direccion = self._val(arr[0].get('txtItem', ''))

            # Subtitle (type of restaurant)
            subtitulo = self._val(params.get('txtSubtitulo'))

            # Tarjeta
            tarjeta_card = self._val(params.get('txtVigenciaCard'))  # e.g. "Exclusivo Black"
            tarjeta = f"Tarjeta Ripley {tarjeta_card}".strip() if tarjeta_card and 'exclusivo' in tarjeta_card.lower() else "Tarjeta Ripley"

            # Images
            imagen = self._val(params.get('imgBackground')) or self._val(params.get('imgLogo'))
            logo = self._val(params.get('imgLogo'))

            # Link — always point to bank's benefits page, not restaurant website
            url = "https://www.bancoripley.cl/beneficios-y-promociones"

            item_id = str(item.get('id', item.get('idBeneficio',
                          re.sub(r'[^a-z0-9]', '_', nombre.lower()[:30]))))

            return Beneficio(
                id=f"ripley_{item_id}",
                banco=self.BANCO,
                tarjeta=tarjeta,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=f"{descuento_valor}% dcto." if descuento_valor > 0 else descuento_raw[:100],
                dias_validos=dias_validos,
                valido_hasta=vigencia,
                ubicacion=ubicacion,
                direccion=direccion,
                descripcion=subtitulo[:200],
                presencial=True,
                online=False,
                url_fuente=url,
                imagen_url=imagen,
                logo_url=logo,
                restricciones_texto='',
                activo=True,
            )
        except Exception:
            return None

    def _parsear_dias_ripley(self, texto: str) -> List[str]:
        """Parsea días de validez de Ripley (ej: 'Jueves', 'Lunes a Viernes')"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sabado': 'sabado', 'domingo': 'domingo',
        }
        texto_lower = texto.lower().strip()
        # "Lunes a Viernes"
        match = re.match(r'(\w+)\s+a\s+(\w+)', texto_lower)
        if match:
            start, end = match.group(1), match.group(2)
            all_days = list(dias_map.keys())
            try:
                s_idx = next(i for i, d in enumerate(all_days) if d == start)
                e_idx = next(i for i, d in enumerate(all_days) if d == end)
                if e_idx >= s_idx:
                    return [dias_map[all_days[i]] for i in range(s_idx, e_idx + 1)]
            except (StopIteration, IndexError):
                pass
        # Single day or comma-separated
        found = [dias_map[d.strip()] for d in texto_lower.replace(',', ' ').split() if d.strip() in dias_map]
        return found if found else ['todos']


# ============================================
# SCRAPER ENTEL (HTML + Lit Web Components)
# ============================================

class ScraperEntel:
    """Scraper de Entel via HTML con Lit Web Components"""

    PAGE_URL = "https://www.entel.cl/beneficios"
    BANCO = "Entel"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de comida de Entel (tab 'Comida' con id tab-comida-2)"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (HTML + Lit Components)...")
            from bs4 import BeautifulSoup

            response = self.session.get(self.PAGE_URL, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar el container del tab Comida (segundo set, listado completo)
            comida_tab = soup.find(id='tab-comida-2')
            if comida_tab:
                cards = comida_tab.select('andino-card-general[eds-card]')
                print(f"   Tab 'Comida' (tab-comida-2): {len(cards)} cards")
            else:
                # Fallback: buscar highlight swiper de Comida (primer swiper-container)
                cards = []
                for section in soup.select('section'):
                    headings = section.find_all('h3')
                    for h in headings:
                        if h.get_text(strip=True).lower() == 'comida':
                            swiper = h.find_next('swiper-container')
                            if swiper:
                                cards = swiper.select('andino-card-general[eds-card]')
                            break
                    if cards:
                        break
                print(f"   Fallback Comida swiper: {len(cards)} cards")

            for card in cards:
                beneficio = self._parsear_card(card)
                if beneficio:
                    self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_card(self, card) -> Optional[Beneficio]:
        """Parsea una card con eds-card JSON a Beneficio (ya filtrada por sección Comida)"""
        try:
            eds_card_raw = card.get('eds-card', '[]')
            try:
                card_data_list = json.loads(eds_card_raw)
            except (json.JSONDecodeError, TypeError):
                return None

            if not card_data_list or not isinstance(card_data_list, list):
                return None

            data = card_data_list[0] if isinstance(card_data_list[0], dict) else {}

            # Card structure: {header: {image: {sources: [{src}]}}, title, text, href, data: {market, segment}}
            nombre = data.get('title', data.get('name', ''))
            if not nombre:
                return None
            descripcion = data.get('text', data.get('description', ''))

            # Get days from parent swiper-slide data-tags, or from description text
            parent = card.find_parent('swiper-slide')
            dias_raw = ''
            if parent:
                dias_raw = parent.get('data-tags', '')
            if dias_raw:
                dias_validos = self._parsear_dias(dias_raw)
            else:
                dias_validos = self._extraer_dias_de_texto(descripcion)

            # Try to extract discount from text
            descuento_raw = descripcion
            descuento_valor = 0
            match = re.search(r'(\d+)\s*%', str(descuento_raw))
            if match:
                descuento_valor = int(match.group(1))
            # Also check for price-based offers (e.g. "$100")
            if descuento_valor == 0:
                price_match = re.search(r'\$\s*([\d.,]+)', str(descuento_raw))
                if price_match:
                    descuento_raw = f"${price_match.group(1)}"

            descuento_texto = f"{descuento_valor}% dcto." if descuento_valor > 0 else str(descuento_raw)[:100]

            # Image from header.image.sources[0].src
            imagen_url = ''
            header = data.get('header', {})
            if isinstance(header, dict):
                image_data = header.get('image', {})
                if isinstance(image_data, dict):
                    sources = image_data.get('sources', [])
                    if sources and isinstance(sources, list):
                        imagen_url = sources[0].get('src', '')
            if not imagen_url:
                imagen_url = data.get('image', data.get('img', ''))
            if imagen_url and not imagen_url.startswith('http'):
                imagen_url = f"https://www.entel.cl{imagen_url}"

            # URL
            link = data.get('href', data.get('link', data.get('url', '')))
            url = link if link and link.startswith('http') else f"https://www.entel.cl{link}" if link else self.PAGE_URL

            card_id = data.get('id', re.sub(r'[^a-z0-9]', '_', nombre.lower()[:30]))

            return Beneficio(
                id=f"entel_{card_id}",
                banco=self.BANCO,
                tarjeta="Entel",
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                ubicacion='',
                presencial=True,
                online=True,
                url_fuente=url,
                imagen_url=imagen_url,
                descripcion=descripcion[:200],
                activo=True,
            )
        except Exception:
            return None

    def _parsear_dias(self, tags_str: str) -> List[str]:
        """Parsea dias de data-tags='lunes, martes, ...'"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sabado': 'sabado', 'domingo': 'domingo',
        }
        tags = [t.strip().lower() for t in tags_str.split(',')]
        dias = [dias_map[t] for t in tags if t in dias_map]
        return dias if dias else ['todos']

    def _extraer_dias_de_texto(self, texto: str) -> List[str]:
        """Extrae días mencionados en la descripción del beneficio"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sábados': 'sabado', 'sabado': 'sabado',
            'domingo': 'domingo', 'domingos': 'domingo',
        }
        texto_lower = texto.lower()
        # "de X a Y" range
        range_match = re.search(r'de\s+(\w+)\s+a\s+(\w+)', texto_lower)
        if range_match:
            start, end = range_match.group(1), range_match.group(2)
            ordered = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
            s_norm = dias_map.get(start)
            e_norm = dias_map.get(end)
            if s_norm and e_norm and s_norm in ordered and e_norm in ordered:
                si = ordered.index(s_norm)
                ei = ordered.index(e_norm)
                if ei >= si:
                    return ordered[si:ei+1]
                else:
                    return ordered[si:] + ordered[:ei+1]
        # Individual day mentions
        found = []
        for word, norm in dias_map.items():
            if word in texto_lower and norm not in found:
                found.append(norm)
        return found if found else ['todos']


# ============================================
# SCRAPER TENPO (Webflow CMS)
# ============================================

class ScraperTenpo:
    """Scraper de Tenpo via Webflow CMS (HTML estático paginado)"""

    BASE_URL = "https://www.tenpo.cl/beneficios"
    BANCO = "Tenpo"
    MAX_PAGES = 6

    FOOD_KEYWORDS = [
        'foodie', 'comida', 'restaurante', 'restaurant', 'pizza', 'sushi',
        'burger', 'café', 'cafe', 'bar', 'parrilla', 'grill', 'cocina',
        'food', 'gourmet', 'starbucks', 'mcdonald', 'papa john', 'domino',
        'subway', 'kfc', 'delivery', 'rappi', 'uber eats', 'pedidosya',
        'brunch', 'almuerzo', 'cena', 'menú', 'menu', 'sabores',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de comida de Tenpo (Webflow CMS)"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Webflow CMS)...")
            from bs4 import BeautifulSoup

            all_cards = []
            for page_num in range(1, self.MAX_PAGES + 1):
                url = f"{self.BASE_URL}?ca01dc3d_page={page_num}" if page_num > 1 else self.BASE_URL
                try:
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                except Exception:
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                # Webflow CMS benefit cards (not filter checkboxes)
                cards = soup.select('.beneficio-collection-item')
                if not cards:
                    break

                all_cards.extend(cards)
                if page_num == 1:
                    print(f"   Página 1: {len(cards)} cards")

                # If fewer than expected, we're on the last page
                if len(cards) < 10:
                    break

            print(f"   Total cards: {len(all_cards)}")

            seen_names = set()
            for card in all_cards:
                beneficio = self._parsear_card(card)
                if beneficio and beneficio.restaurante not in seen_names:
                    seen_names.add(beneficio.restaurante)
                    self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _parsear_card(self, card) -> Optional[Beneficio]:
        """Parsea una card de Webflow CMS a Beneficio"""
        try:
            # Category from fs-cmsfilter-field="Categoria"
            cat_el = card.select_one('[fs-cmsfilter-field="Categoria"]')
            category = cat_el.get_text(strip=True).lower() if cat_el else ''

            # Name from fs-cmsfilter-field="Name"
            name_el = card.select_one('[fs-cmsfilter-field="Name"]')
            nombre = name_el.get_text(strip=True) if name_el else ''

            if not nombre:
                titulo_el = card.select_one('.b-titulo, .titulo-beneficio')
                nombre = titulo_el.get_text(strip=True) if titulo_el else ''
            if not nombre:
                return None

            # Title/discount text
            titulo_el = card.select_one('.titulo-beneficio, .b-titulo, .titulo-beneficio-all')
            titulo = titulo_el.get_text(strip=True) if titulo_el else ''

            # Description
            desc_el = card.select_one('.p-text-beneficio-copy, .texto-beneficio')
            descripcion = desc_el.get_text(strip=True) if desc_el else ''

            # Check if food-related by category or keywords
            texto_buscar = f"{nombre} {titulo} {descripcion} {category}".lower()
            es_comida = category in ['foodie', 'comida', 'food', 'gastronomía', 'gastronomia', 'restaurante']
            if not es_comida:
                es_comida = any(kw in texto_buscar for kw in self.FOOD_KEYWORDS)
            if not es_comida:
                return None

            # Discount
            descuento_valor = 0
            match = re.search(r'(\d+)\s*%', f"{titulo} {descripcion}")
            if match:
                descuento_valor = int(match.group(1))
            descuento_texto = f"{descuento_valor}% dcto." if descuento_valor > 0 else titulo[:100] if titulo else descripcion[:100]

            # Days from .dia-abrev elements
            dias_els = card.select('.dia-abrev')
            if dias_els:
                dias_texto = ' '.join(d.get_text(strip=True) for d in dias_els)
                dias_validos = self._extraer_dias(dias_texto)
            else:
                dias_validos = self._extraer_dias(f"{titulo} {descripcion}")

            # Image from background-image or img
            imagen_url = ''
            head_card = card.select_one('.head-card')
            if head_card:
                style = head_card.get('style', '')
                bg_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                if bg_match:
                    imagen_url = bg_match.group(1)
            if not imagen_url:
                img_el = card.select_one('img.brand-partner, img')
                if img_el:
                    imagen_url = img_el.get('src', '') or img_el.get('data-src', '')

            # Logo from .brand-partner img
            logo_url = ''
            logo_el = card.select_one('img.brand-partner')
            if logo_el:
                logo_url = logo_el.get('src', '')

            # Link
            link_el = card.select_one('a')
            href = link_el.get('href', '') if link_el else ''
            url = href if href and href.startswith('http') else f"https://www.tenpo.cl{href}" if href else self.BASE_URL

            # Location
            ciudad_el = card.select_one('[fs-cmsfilter-field="Ciudad"]')
            ubicacion = ciudad_el.get_text(strip=True) if ciudad_el else ''
            if ubicacion.lower() == 'todo chile':
                ubicacion = ''

            card_id = re.sub(r'[^a-z0-9]', '_', nombre.lower()[:40])

            return Beneficio(
                id=f"tenpo_{card_id}",
                banco=self.BANCO,
                tarjeta="Tenpo",
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                ubicacion=ubicacion,
                presencial=True,
                online=True,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                descripcion=descripcion[:200],
                activo=True,
            )
        except Exception:
            return None

    def _extraer_dias(self, texto: str) -> List[str]:
        """Extrae días mencionados en texto"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sábados': 'sabado', 'sabado': 'sabado',
            'domingo': 'domingo', 'domingos': 'domingo',
        }
        texto_lower = texto.lower()
        if 'todos los días' in texto_lower or 'todos los dias' in texto_lower:
            return ['todos']
        found = [dias_map[d] for d in dias_map if d in texto_lower]
        return list(dict.fromkeys(found)) if found else ['todos']


# ============================================
# SCRAPER LIDER BCI (Modyo CMS via Playwright)
# ============================================

class ScraperLiderBCI:
    """Scraper de Lider BCI via Modyo CMS API (interceptada con Playwright)"""

    API_URL = "https://www.bci.cl/api/content/spaces/tarjeta-lider/types/descuentos/entries?per_page=10000&sort_by=meta.published_at&order=desc"
    PAGE_URL = "https://www.liderbci.cl/descuentos"
    BANCO = "Lider BCI"

    def __init__(self):
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de gastronomía de Lider BCI (Playwright intercept)"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Playwright + API intercept)...")
            from playwright.sync_api import sync_playwright

            captured_data = []

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                )
                page = context.new_page()

                def capture(response):
                    if 'tarjeta-lider' in response.url and 'entries' in response.url and response.status == 200:
                        try:
                            captured_data.append(response.json())
                        except Exception:
                            pass

                page.on('response', capture)
                page.goto(self.PAGE_URL, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(8000)
                browser.close()

            if not captured_data:
                print(f"   ⚠️ No se capturó data de API, intentando request directo...")
                return self._fallback_request()

            # Process captured API data
            for data in captured_data:
                entries = data.get('entries', [])
                print(f"   Entries capturadas: {len(entries)}")
                for entry in entries:
                    beneficio = self._parsear_entry(entry)
                    if beneficio:
                        self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _fallback_request(self) -> List[Beneficio]:
        """Intenta request directo a la API (puede fallar por Cloudflare)"""
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': self.PAGE_URL,
            })
            response = session.get(self.API_URL, timeout=15)
            response.raise_for_status()
            data = response.json()
            entries = data.get('entries', [])
            for entry in entries:
                beneficio = self._parsear_entry(entry)
                if beneficio:
                    self.beneficios.append(beneficio)
            print(f"   Fallback request OK: {len(self.beneficios)} beneficios")
        except Exception as e:
            print(f"   ❌ Fallback también falló: {e}")
        return self.beneficios

    def _parsear_entry(self, entry: dict) -> Optional[Beneficio]:
        """Parsea una entry de Modyo CMS a Beneficio si es gastronomía"""
        try:
            fields = entry.get('fields', {})
            meta = entry.get('meta', {})

            categoria = fields.get('categoria', '').strip()
            # Normalize: "Gastronomía" → "gastronomia" (remove accents + lowercase)
            import unicodedata
            cat_norm = ''.join(c for c in unicodedata.normalize('NFD', categoria.lower()) if unicodedata.category(c) != 'Mn')
            if cat_norm != 'gastronomia':
                return None

            nombre_raw = fields.get('descripcion_card', '') or meta.get('name', 'Desconocido')
            # Extract restaurant name from "En KFC todos los lunes" → try to get cleaner name
            nombre = meta.get('name', '').replace('Descuento - ', '').strip()
            if not nombre:
                nombre = nombre_raw

            slug = meta.get('slug', '')
            descuento_card = fields.get('valor_descuento', '')
            dias_texto = fields.get('texto_dias', '')
            filtrado_dias = fields.get('filtrado_dias', [])

            # Discount
            descuento_valor = 0
            match = re.search(r'(\d+)', descuento_card)
            if match:
                descuento_valor = int(match.group(1))
            descuento_texto = descuento_card.strip() if descuento_card else ''
            if descuento_valor > 0 and 'dcto' not in descuento_texto.lower() and 'dto' not in descuento_texto.lower():
                descuento_texto = f"{descuento_valor}% dcto."

            # Days
            dias_validos = ['todos']
            if isinstance(filtrado_dias, list) and filtrado_dias:
                dias_map = {
                    'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miercoles',
                    'miércoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
                    'sabado': 'sabado', 'sábado': 'sabado', 'domingo': 'domingo',
                }
                dias = [dias_map.get(d.lower().strip(), d.lower().strip()) for d in filtrado_dias if d.lower().strip() in dias_map]
                if dias:
                    dias_validos = dias

            # Images
            img_data = fields.get('imagen', {})
            imagen_url = img_data.get('url', '') if isinstance(img_data, dict) else ''
            logo_data = fields.get('logo_marca', {})
            logo_url = logo_data.get('url', '') if isinstance(logo_data, dict) else ''

            # Vigencia
            vigencia = fields.get('vigencia_detalle', '')
            valido_desde = ''
            valido_hasta = ''
            if vigencia:
                fechas = re.findall(r'(\d{1,2}-\d{2}-\d{4})', vigencia)
                if len(fechas) >= 2:
                    valido_desde = fechas[0]
                    valido_hasta = fechas[-1]
                elif len(fechas) == 1:
                    valido_hasta = fechas[0]

            # Modo (presencial/online)
            modo = fields.get('modo_descuento_detalle', '').lower()
            presencial = 'presencial' in modo or not modo
            online = 'online' in modo

            # Tope
            tope_raw = fields.get('tope_descuento_detalle', '')
            tope = 0
            tope_match = re.search(r'\$\s*([\d.]+)', str(tope_raw))
            if tope_match:
                tope = int(tope_match.group(1).replace('.', ''))

            # Descripción
            titulo = fields.get('titulo_detalle', '')
            desc_card = fields.get('descripcion_card', '')
            descripcion = titulo if titulo else desc_card

            url = f"https://www.liderbci.cl/descuentos/{slug}" if slug else self.PAGE_URL

            entry_id = meta.get('uuid', re.sub(r'[^a-z0-9]', '_', nombre.lower()[:40]))

            return Beneficio(
                id=f"liderbci_{entry_id}",
                banco=self.BANCO,
                tarjeta="Tarjeta Lider BCI",
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                valido_desde=valido_desde,
                valido_hasta=valido_hasta,
                ubicacion='',
                tope_descuento=tope,
                presencial=presencial,
                online=online,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                descripcion=descripcion[:200] if descripcion else '',
                activo=True,
            )
        except Exception:
            return None


# ============================================
# SCRAPER BANCO BICE (Widget JS Bundle)
# ============================================

class ScraperBICE:
    """Scraper de Banco BICE via Widget JS Bundle (Modyo CMS)"""

    WIDGET_URL = "https://banco.bice.cl/personas/widget_manager/1b019b42-daf2-4148-a051-a360be61be81/4197b85bfbed841f865596459940910d8cde6819bfc3633dd5073564e7d11be7.js"
    FALLBACK_API = "https://bice.certification.modyo.com/api/content/spaces/beneficios-bice/types/beneficios/entries"
    BANCO = "Banco BICE"
    FOOD_CATEGORIES = ['restaurante', 'gourmet', 'delivery']

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': '*/*',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de restaurantes de Banco BICE"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (Widget JS Bundle)...")

            entries = self._fetch_widget_js()
            if not entries:
                print(f"   ⚠️ Widget JS falló, intentando API certification...")
                entries = self._fetch_certification_api()

            if not entries:
                print(f"   ❌ No se pudieron obtener datos")
                return self.beneficios

            print(f"   Total entries: {len(entries)}")

            # Filter food categories
            for entry in entries:
                cat = entry.get('meta', {}).get('category_slug') or entry.get('meta', {}).get('category') or ''
                if cat and cat.lower() in self.FOOD_CATEGORIES:
                    beneficio = self._parsear_entry(entry)
                    if beneficio:
                        self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _fetch_widget_js(self) -> list:
        """Extrae entries del JS bundle del widget"""
        try:
            response = self.session.get(self.WIDGET_URL, timeout=20)
            response.raise_for_status()
            js_content = response.text

            # Extract JSON array from 'const entries = [...]'
            match = re.search(r'const\s+entries\s*=\s*(\[.*?\]);\s*\n', js_content, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            # Try alternative patterns
            match = re.search(r'entries\s*[:=]\s*(\[.*?\])\s*[;,]', js_content, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            return []
        except Exception as e:
            print(f"   Widget JS error: {e}")
            return []

    def _fetch_certification_api(self) -> list:
        """Fallback: API de certificación de Modyo"""
        try:
            all_entries = []
            for cat in self.FOOD_CATEGORIES:
                params = {'meta.category': cat, 'per_page': 100}
                response = self.session.get(self.FALLBACK_API, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                entries = data.get('entries', [])
                all_entries.extend(entries)
            return all_entries
        except Exception as e:
            print(f"   API certification error: {e}")
            return []

    def _parsear_entry(self, entry: dict) -> Optional[Beneficio]:
        """Parsea una entry BICE a Beneficio"""
        try:
            meta = entry.get('meta', {})
            fields = entry.get('fields', {})

            nombre = fields.get('Marca', meta.get('name', 'Desconocido'))

            # Discount
            promo_big = fields.get('Texto-promo-big', '')
            promo_small = fields.get('Texto-promo-small', '')
            descuento_valor = 0
            match = re.search(r'(\d+)', str(promo_big))
            if match:
                descuento_valor = int(match.group(1))
            descuento_texto = f"{promo_big} {promo_small}".strip()
            if descuento_valor > 0 and 'dcto' not in descuento_texto.lower():
                descuento_texto = f"{descuento_valor}% dcto."

            # Region
            regiones = fields.get('Region', [])
            ubicacion = ''
            if isinstance(regiones, list) and regiones:
                ubicacion = regiones[0]

            # Cities/address
            ciudades_html = fields.get('Ciudades', '')
            direccion_html = fields.get('Direccion', '')
            ciudades = re.sub(r'<[^>]+>', ' ', str(ciudades_html)).strip() if ciudades_html else ''
            direccion = re.sub(r'<[^>]+>', ' ', str(direccion_html)).strip() if direccion_html else ''

            # Dates
            fecha_desde = fields.get('Fecha-desde', '')
            fecha_hasta = fields.get('Fecha-hasta', '')
            valido_desde = fecha_desde[:10] if fecha_desde else ''
            valido_hasta = fecha_hasta[:10] if fecha_hasta else ''

            # Cards/tarjetas
            tarjetas = fields.get('Tarjetas', [])
            tarjeta = ', '.join(tarjetas[:2]) if tarjetas else 'Tarjetas BICE'

            # Days from name (e.g. "Living Cafe / Lunes")
            dias_validos = self._extraer_dias(meta.get('name', ''))

            # Images
            logo_data = fields.get('Logo', {})
            logo_url = logo_data.get('url', '') if isinstance(logo_data, dict) else ''
            img_data = fields.get('Imagen-show', fields.get('Galeria', [{}]))
            imagen_url = ''
            if isinstance(img_data, dict):
                imagen_url = img_data.get('url', '')
            elif isinstance(img_data, list) and img_data:
                imagen_url = img_data[0].get('url', '') if isinstance(img_data[0], dict) else ''

            # Donde (presencial/online)
            donde = fields.get('Donde', '').lower()
            presencial = 'presencial' in donde or 'fisic' in donde or not donde
            online = 'online' in donde

            # Description
            bajada_html = fields.get('Bajada-sitio-publico', '') or fields.get('Bajada', '')
            descripcion = re.sub(r'<[^>]+>', ' ', str(bajada_html)).strip()[:200] if bajada_html else ''

            # URL
            slug = meta.get('slug', '')
            url = f"https://banco.bice.cl/personas/beneficios/{slug}" if slug else 'https://banco.bice.cl/personas/beneficios'

            # Website
            sitio_web = fields.get('Sitio_web', '')

            entry_id = meta.get('uuid', re.sub(r'[^a-z0-9]', '_', nombre.lower()[:40]))

            return Beneficio(
                id=f"bice_{entry_id}",
                banco=self.BANCO,
                tarjeta=tarjeta,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                valido_desde=valido_desde,
                valido_hasta=valido_hasta,
                ubicacion=ubicacion,
                comuna=ciudades[:50] if ciudades else '',
                direccion=direccion[:200] if direccion else '',
                presencial=presencial,
                online=online,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                descripcion=descripcion,
                activo=True,
            )
        except Exception:
            return None

    def _extraer_dias(self, texto: str) -> List[str]:
        """Extrae días de texto como 'Living Cafe / Lunes'"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sabado': 'sabado', 'domingo': 'domingo',
        }
        texto_lower = texto.lower()
        found = [dias_map[d] for d in dias_map if d in texto_lower]
        return list(dict.fromkeys(found)) if found else ['todos']


# ============================================
# SCRAPER MACH (HTML embebido, Modyo CMS)
# ============================================

class ScraperMach:
    """Scraper de Mach via HTML con JSON embebido (const apiBnf)"""

    PAGE_URL = "https://www.machbank.cl/beneficios?catg=restaurantes"
    BANCO = "Mach"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        self.beneficios: List[Beneficio] = []

    def scrapear(self) -> List[Beneficio]:
        """Extrae beneficios de restaurantes de Mach"""
        try:
            print(f"📡 Scrapeando {self.BANCO} (HTML con JSON embebido)...")

            response = self.session.get(self.PAGE_URL, timeout=20)
            response.raise_for_status()
            html = response.text

            # Extract embedded JSON array: const apiBnf = [...];
            match = re.search(r'const\s+apiBnf\s*=\s*(\[.*?\]);\s*\n', html, re.DOTALL)
            if not match:
                # Try alternative patterns
                match = re.search(r'apiBnf\s*=\s*(\[.*?\]);\s', html, re.DOTALL)

            if not match:
                print(f"   ⚠️ No se encontró apiBnf en HTML, intentando Playwright...")
                return self._playwright_fallback()

            entries = json.loads(match.group(1))
            print(f"   Total entries embebidas: {len(entries)}")

            # Filter restaurants
            for entry in entries:
                cat = entry.get('meta', {}).get('category_name') or entry.get('meta', {}).get('category') or ''
                if cat and cat.lower() in ['restaurantes', 'restaurante', 'comida']:
                    beneficio = self._parsear_entry(entry)
                    if beneficio:
                        self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos")
            return self.beneficios

        except Exception as e:
            print(f"❌ Error scrapeando {self.BANCO}: {e}")
            return self.beneficios

    def _playwright_fallback(self) -> List[Beneficio]:
        """Fallback: interceptar API con Playwright"""
        try:
            from playwright.sync_api import sync_playwright

            captured_data = []

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                def capture(response):
                    if 'mach' in response.url and 'entries' in response.url and response.status == 200:
                        try:
                            captured_data.append(response.json())
                        except Exception:
                            pass

                page.on('response', capture)
                page.goto(self.PAGE_URL, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(8000)
                browser.close()

            for data in captured_data:
                entries = data.get('entries', [])
                for entry in entries:
                    cat = entry.get('meta', {}).get('category_name') or ''
                    if cat and cat.lower() in ['restaurantes', 'restaurante']:
                        beneficio = self._parsear_entry(entry)
                        if beneficio:
                            self.beneficios.append(beneficio)

            print(f"   Playwright fallback: {len(self.beneficios)} beneficios")
            return self.beneficios
        except Exception as e:
            print(f"   ❌ Fallback también falló: {e}")
            return self.beneficios

    def _parsear_entry(self, entry: dict) -> Optional[Beneficio]:
        """Parsea una entry de Mach a Beneficio"""
        try:
            meta = entry.get('meta', {})
            fields = entry.get('fields', {})

            nombre = fields.get('nombre_de_empresa', '') or fields.get('titulo', meta.get('name', 'Desconocido'))
            titulo = fields.get('titulo', '')

            # Discount from etiqueta_banner
            etiqueta = fields.get('etiqueta_banner', '')
            descuento_valor = 0
            match = re.search(r'(\d+)\s*%', etiqueta)
            if match:
                descuento_valor = int(match.group(1))
            if not etiqueta:
                match = re.search(r'(\d+)\s*%', titulo)
                if match:
                    descuento_valor = int(match.group(1))
            descuento_texto = etiqueta.strip() if etiqueta else f"{descuento_valor}% dcto." if descuento_valor > 0 else titulo[:100]

            # Days
            dias_raw = fields.get('dia_de_promo', [])
            dias_validos = ['todos']
            if isinstance(dias_raw, list) and dias_raw:
                dias_map = {
                    'lunes': 'lunes', 'martes': 'martes', 'miercoles': 'miercoles',
                    'miércoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
                    'sabado': 'sabado', 'sábado': 'sabado', 'domingo': 'domingo',
                }
                dias = [dias_map.get(d.lower().strip(), d.lower().strip()) for d in dias_raw if d.lower().strip() in dias_map]
                if dias:
                    dias_validos = dias

            # Payment method
            medio_pago = fields.get('medio_de_pago', [])
            tarjeta_parts = []
            for mp in (medio_pago if isinstance(medio_pago, list) else []):
                mp_lower = mp.lower()
                if 'credito' in mp_lower or 'crédito' in mp_lower:
                    tarjeta_parts.append('Crédito')
                elif 'debito' in mp_lower or 'débito' in mp_lower:
                    tarjeta_parts.append('Débito')
                elif 'qr' in mp_lower:
                    tarjeta_parts.append('QR')
            tarjeta = f"Mach {', '.join(tarjeta_parts)}".strip() if tarjeta_parts else 'Mach'

            # Region
            regiones = fields.get('region_de_promo', [])
            ubicacion = regiones[0] if isinstance(regiones, list) and regiones else ''

            # Type (presencial/online)
            tipo = fields.get('tipo_de_beneficio', [])
            presencial = any('presencial' in t.lower() for t in tipo) if isinstance(tipo, list) else True
            online = any('online' in t.lower() for t in tipo) if isinstance(tipo, list) else False

            # Images
            img_data = fields.get('imagen', {})
            imagen_url = img_data.get('url', '') if isinstance(img_data, dict) else ''
            logo_data = fields.get('logo_de_empresa', {})
            logo_url = logo_data.get('url', '') if isinstance(logo_data, dict) else ''

            # Description
            descripcion = fields.get('descripcion', '') or fields.get('descripcion_banner', '')
            descripcion = re.sub(r'<[^>]+>', ' ', str(descripcion)).strip()[:200]

            # URL
            slug = meta.get('slug', '')
            url = f"https://www.machbank.cl/beneficios/detalle/{slug}" if slug else self.PAGE_URL

            entry_id = meta.get('uuid', re.sub(r'[^a-z0-9]', '_', nombre.lower()[:40]))

            return Beneficio(
                id=f"mach_{entry_id}",
                banco=self.BANCO,
                tarjeta=tarjeta,
                restaurante=nombre,
                descuento_valor=float(descuento_valor),
                descuento_tipo="porcentaje" if descuento_valor > 0 else "otro",
                descuento_texto=descuento_texto,
                dias_validos=dias_validos,
                ubicacion=ubicacion,
                presencial=presencial,
                online=online,
                url_fuente=url,
                imagen_url=imagen_url,
                logo_url=logo_url,
                descripcion=descripcion,
                activo=True,
            )
        except Exception:
            return None


# ============================================
# SCRAPER DE DESCUENTOS EN BENCINA
# ============================================

class ScraperBencina:
    """Scraper de descuentos en bencina/combustible.

    Fuente primaria: descuentosrata.com/bencina
    Fallback: datos estáticos mensuales (biobiochile, chocale, etc.)
    """

    URL_DESCUENTOSRATA = "https://descuentosrata.com/bencina"
    CADENAS = ["Copec", "Shell", "Aramco"]

    # Logos de cadenas de gasolineras
    LOGOS = {
        "Copec": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Copec_logo.svg/200px-Copec_logo.svg.png",
        "Shell": "https://upload.wikimedia.org/wikipedia/en/thumb/e/e8/Shell_logo.svg/200px-Shell_logo.svg.png",
        "Aramco": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Aramco_logo.svg/200px-Aramco_logo.svg.png",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        self.descuentos: List[DescuentoBencina] = []

    def scrapear(self) -> List[DescuentoBencina]:
        """Extrae descuentos de bencina. Intenta web scraping, usa fallback si falla."""
        print("⛽ Scrapeando descuentos de bencina...")
        try:
            self._scrapear_descuentosrata()
            if len(self.descuentos) >= 15:
                print(f"  ✅ descuentosrata.com: {len(self.descuentos)} descuentos")
            else:
                print(f"  ⚠️ Solo {len(self.descuentos)} descuentos de web, cargando fallback...")
                self.descuentos = []
                self._cargar_datos_estaticos()
        except Exception as e:
            print(f"  ⚠️ descuentosrata falló ({e}), usando datos estáticos...")
            self.descuentos = []
            self._cargar_datos_estaticos()

        print(f"  ⛽ Total descuentos bencina: {len(self.descuentos)}")
        return self.descuentos

    def _scrapear_descuentosrata(self):
        """Scrapea descuentosrata.com/bencina"""
        from bs4 import BeautifulSoup

        resp = self.session.get(self.URL_DESCUENTOSRATA, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # descuentosrata organiza por secciones de cadena con cards
        cards = soup.select('.card, .discount-card, article, .benefit-card, [class*="descuento"]')

        for card in cards:
            try:
                texto = card.get_text(separator=' ', strip=True)
                # Intentar extraer cadena
                cadena = ""
                texto_lower = texto.lower()
                for c in self.CADENAS:
                    if c.lower() in texto_lower:
                        cadena = c
                        break
                if not cadena:
                    continue

                # Extraer monto descuento
                match_monto = re.search(r'\$\s*(\d+)', texto)
                if not match_monto:
                    continue
                monto = int(match_monto.group(1))

                # Extraer banco/medio de pago
                banco = self._extraer_banco(texto)

                # Extraer dias
                dias = self._extraer_dias(texto)

                self.descuentos.append(DescuentoBencina(
                    id=f"bencina_{cadena.lower()}_{banco.lower().replace(' ', '_')}_{'-'.join(dias) if dias else 'todos'}",
                    cadena=cadena,
                    banco=banco,
                    tarjeta=banco,
                    descuento_por_litro=monto,
                    descuento_texto=f"${monto}/L",
                    dias_validos=dias if dias else ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"],
                    condicion="",
                    url_fuente=self.URL_DESCUENTOSRATA,
                ))
            except Exception:
                continue

    def _extraer_banco(self, texto: str) -> str:
        """Extrae nombre del banco/medio de pago del texto"""
        bancos_conocidos = [
            "Banco Consorcio", "Consorcio", "Mercado Pago", "Banco Ripley", "Ripley",
            "ABC Visa", "Tenpo", "SBPay", "SPIN", "Lider BCI", "Lider Bci",
            "Micopiloto", "BICE", "Bice", "Security", "Cencosud Scotiabank",
            "Scotiabank", "Jumbo Prime", "Santander Consumer", "Santander",
            "Banco Internacional", "Internacional", "Itaú", "Itau",
            "Coopeuch", "BCI", "Bci", "Rutpay", "BancoEstado", "MACHBANK",
            "Machbank", "Mach", "Copec Pay",
        ]
        texto_lower = texto.lower()
        for banco in bancos_conocidos:
            if banco.lower() in texto_lower:
                return banco
        return "Varios"

    def _extraer_dias(self, texto: str) -> List[str]:
        """Extrae dias de la semana del texto"""
        dias_map = {
            'lunes': 'lunes', 'martes': 'martes', 'miércoles': 'miercoles',
            'miercoles': 'miercoles', 'jueves': 'jueves', 'viernes': 'viernes',
            'sábado': 'sabado', 'sabado': 'sabado', 'domingo': 'domingo',
        }
        encontrados = []
        texto_lower = texto.lower()
        for nombre, dia in dias_map.items():
            if nombre in texto_lower and dia not in encontrados:
                encontrados.append(dia)
        return encontrados

    def _cargar_datos_estaticos(self):
        """Datos de descuentos bencina marzo 2026 (fallback)"""
        import calendar
        now = datetime.now()
        ultimo_dia = calendar.monthrange(now.year, now.month)[1]
        mes_abrev = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
                     7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}[now.month]
        valido_hasta = f"{ultimo_dia:02d}-{mes_abrev}-{now.year}"

        # Fuente: biobiochile.cl, chocale.cl, descuentosrata.com - Marzo 2026
        datos = [
            # ARAMCO
            ("Aramco", "Banco Consorcio", "Crédito Consorcio", 150, ["lunes"], "App Aramco", 0, 10000),
            ("Aramco", "Mercado Pago", "Prepago Mercado Pago", 50, ["martes"], "", 0, 5000),
            ("Aramco", "Banco Ripley", "Crédito Ripley Gold", 150, ["miercoles"], "", 0, 0),
            ("Aramco", "Banco Ripley", "Crédito Ripley Silver", 125, ["miercoles"], "", 0, 0),
            ("Aramco", "Banco Ripley", "Crédito Ripley Plus", 100, ["miercoles"], "", 0, 0),
            ("Aramco", "ABC Visa", "Crédito ABC Visa", 150, ["jueves"], "", 0, 0),
            ("Aramco", "Tenpo", "Crédito/Prepago Tenpo", 300, ["viernes"], "Min $5.000, máx 2 tx/mes", 0, 4000),
            ("Aramco", "SBPay", "Crédito SBPay", 150, ["sabado"], "App Aramco", 0, 10000),
            ("Aramco", "SPIN", "Crédito SPIN", 150, ["domingo"], "", 0, 10000),

            # SHELL
            ("Shell", "Lider BCI", "Crédito Lider BCI", 100, ["martes"], "App Micopiloto, máx $4.000/carga", 0, 8000),
            ("Shell", "Micopiloto", "Cualquier tarjeta", 15, ["miercoles"], 'Código "MIDCTO", 1x/día, 70L', 70, 0),
            ("Shell", "Banco BICE", "Crédito BICE", 100, ["domingo"], "Máx 1 carga/mes", 0, 5000),
            ("Shell", "Banco Security", "Crédito Security", 100, ["domingo"], "", 0, 5000),

            # COPEC
            ("Copec", "Cencosud Scotiabank", "Black", 100, ["lunes"], "App Copec", 0, 0),
            ("Copec", "Cencosud Scotiabank", "Clásica/Platinum", 50, ["lunes"], "App Copec", 0, 0),
            ("Copec", "Jumbo Prime", "Jumbo Prime", 100, ["lunes"], "Máx 100 litros", 100, 0),
            ("Copec", "Santander Consumer", "Crédito Auto Santander", 100, ["lunes", "martes", "miercoles", "jueves", "viernes"], "70L máx", 70, 0),
            ("Copec", "Banco Internacional", "MC Clásica/Gold/Black", 100, ["martes"], "App Copec", 0, 0),
            ("Copec", "Scotiabank", "Visa Crédito Singular", 100, ["miercoles"], "App Copec", 0, 0),
            ("Copec", "Scotiabank", "Visa Crédito Platinum", 50, ["miercoles"], "App Copec", 0, 0),
            ("Copec", "Scotiabank", "Visa Crédito Tradicional", 25, ["miercoles"], "App Copec", 0, 0),
            ("Copec", "Coopeuch", "Crédito Coopeuch", 100, ["jueves"], "", 0, 0),
            ("Copec", "BCI", "Crédito BCI", 100, ["jueves"], "Cashback 7%", 0, 0),
            ("Copec", "Itaú", "Crédito Legend Itaú", 100, ["viernes"], "Código desde Itaú Beneficios", 0, 0),
            ("Copec", "BancoEstado", "Rutpay", 100, ["viernes"], "50L máx, estaciones participantes", 50, 0),
            ("Copec", "MACHBANK", "Crédito MACHBANK", 100, ["sabado"], "", 0, 0),
            ("Copec", "Banco BICE", "Limitless BICE", 100, ["domingo"], "", 0, 0),
            ("Copec", "Copec Pay", "Copec Pay", 10, ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"], "+50% puntos bonus", 0, 0),
        ]

        for (cadena, banco, tarjeta, monto, dias, condicion, tope_l, tope_m) in datos:
            dias_id = '-'.join(dias) if len(dias) <= 2 else 'semana'
            self.descuentos.append(DescuentoBencina(
                id=f"bencina_{cadena.lower()}_{banco.lower().replace(' ', '_')}_{dias_id}",
                cadena=cadena,
                banco=banco,
                tarjeta=tarjeta,
                descuento_por_litro=monto,
                descuento_texto=f"${monto}/L",
                dias_validos=dias,
                condicion=condicion,
                tope_litros=tope_l,
                tope_monto=tope_m,
                valido_hasta=valido_hasta,
                url_fuente="https://descuentosrata.com/bencina",
                tags=[cadena.lower(), banco.lower(), "bencina", "combustible"],
            ))


# ============================================
# SCRAPER DE ESTACIONES Y PRECIOS (bencinaenlinea.cl)
# ============================================

class ScraperBencinaEnLinea:
    """Obtiene estaciones de servicio y precios de combustible de todo Chile.

    Fuente: api.bencinaenlinea.cl (datos publicos, ~1800 estaciones)
    Incluye: ubicacion, marca, precios 93/95/97/diesel/kerosene
    """

    API_BASE = "https://api.bencinaenlinea.cl/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BeneficiosBancarios/1.0 (scraper educativo)',
            'Accept': 'application/json',
        })
        self.estaciones: List[EstacionBencina] = []
        self.marcas: dict = {}  # id -> nombre marca

    def scrapear(self, solo_con_descuentos: bool = False) -> List[EstacionBencina]:
        """Obtiene estaciones con precios desde bencinaenlinea.cl"""
        print("⛽ Obteniendo estaciones y precios desde bencinaenlinea.cl...")

        try:
            self._cargar_marcas()
            self._scrapear_estaciones(solo_con_descuentos)
            if len(self.estaciones) >= 10:
                print(f"  ✅ bencinaenlinea.cl: {len(self.estaciones)} estaciones con precios")
                return self.estaciones
            else:
                print(f"  ⚠️ Solo {len(self.estaciones)} estaciones obtenidas")
        except Exception as e:
            print(f"  ⚠️ bencinaenlinea.cl fallo: {e}")

        print(f"  📍 Total estaciones: {len(self.estaciones)}")
        return self.estaciones

    def _cargar_marcas(self):
        """Carga catalogo de marcas (id -> nombre)"""
        try:
            resp = self.session.get(f"{self.API_BASE}/marca_ciudadano", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            marcas_list = data if isinstance(data, list) else data.get('data', data.get('marcas', []))
            for m in marcas_list:
                mid = m.get('id')
                nombre = m.get('nombre', m.get('razon_social', ''))
                if mid and nombre:
                    self.marcas[mid] = nombre
            print(f"  📋 {len(self.marcas)} marcas cargadas")
        except Exception as e:
            print(f"  ⚠️ No se pudieron cargar marcas: {e}")
            # Marcas conocidas como fallback
            self.marcas = {1: 'Copec', 2: 'Shell', 3: 'Petrobras', 4: 'Aramco'}

    def _scrapear_estaciones(self, solo_con_descuentos: bool):
        """Obtiene todas las estaciones con precios"""
        resp = self.session.get(
            f"{self.API_BASE}/busqueda_estacion_filtro",
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()

        estaciones_raw = data if isinstance(data, list) else data.get('data', data.get('estaciones', []))
        print(f"  📡 API retorno {len(estaciones_raw)} estaciones brutas")

        cadenas_con_descuentos = {'copec', 'shell', 'aramco'}

        for est in estaciones_raw:
            try:
                # Coordenadas
                lat = est.get('latitud')
                lon = est.get('longitud')
                if not lat or not lon:
                    continue
                lat = float(str(lat).strip())
                lon = float(str(lon).strip())
                if lat == 0 or lon == 0:
                    continue

                # Marca/cadena
                marca_id = est.get('marca')
                marca_nombre = self.marcas.get(marca_id, '')
                cadena = self._normalizar_cadena(marca_nombre)

                # Filtro: solo cadenas con descuentos bancarios si se pide
                if solo_con_descuentos and cadena.lower() not in cadenas_con_descuentos:
                    continue

                # Extraer precios de combustibles
                precios = self._extraer_precios(est.get('combustibles', []))

                # Datos de la estacion
                direccion = est.get('direccion', '').strip()
                comuna = est.get('comuna', '').strip()
                region = est.get('region', '').strip()
                nombre_est = f"{cadena} {direccion}" if cadena else direccion
                if not nombre_est.strip():
                    nombre_est = f"Estacion #{est.get('id', 0)}"

                self.estaciones.append(EstacionBencina(
                    id=f"bel_{est.get('id', len(self.estaciones))}",
                    nombre=nombre_est,
                    cadena=cadena,
                    direccion=direccion,
                    comuna=comuna,
                    region=region,
                    latitud=lat,
                    longitud=lon,
                    precio_93=precios.get('93', 0),
                    precio_95=precios.get('95', 0),
                    precio_97=precios.get('97', 0),
                    precio_diesel=precios.get('diesel', 0),
                    precio_kerosene=precios.get('kerosene', 0),
                    precio_fecha=precios.get('fecha', ''),
                ))
            except Exception:
                continue

        # Stats
        cadena_count = {}
        con_precio = 0
        for e in self.estaciones:
            cadena_count[e.cadena] = cadena_count.get(e.cadena, 0) + 1
            if e.precio_93 > 0 or e.precio_97 > 0 or e.precio_diesel > 0:
                con_precio += 1
        for c, n in sorted(cadena_count.items(), key=lambda x: -x[1]):
            print(f"    {c}: {n} estaciones")
        print(f"  💰 {con_precio} estaciones con precios")

    def _extraer_precios(self, combustibles: list) -> dict:
        """Extrae precios por tipo de combustible"""
        precios = {}
        fecha_mas_reciente = ''

        for comb in combustibles:
            nombre = (comb.get('nombre_corto', '') or '').strip().upper()
            precio_str = comb.get('precio', '0')
            suministra = comb.get('suministra', 0)

            if not suministra or not precio_str:
                continue

            try:
                precio = int(float(str(precio_str).strip()))
            except (ValueError, TypeError):
                continue

            if precio <= 0:
                continue

            # Mapear nombre a tipo (priorizar asistido sobre autoservicio)
            if nombre in ('93', 'A93'):
                if '93' not in precios or nombre == '93':
                    precios['93'] = precio
            elif nombre in ('95', 'A95'):
                if '95' not in precios or nombre == '95':
                    precios['95'] = precio
            elif nombre in ('97', 'A97'):
                if '97' not in precios or nombre == '97':
                    precios['97'] = precio
            elif nombre in ('DI', 'ADI', 'DIESEL'):
                if 'diesel' not in precios or nombre == 'DI':
                    precios['diesel'] = precio
            elif nombre in ('KE', 'AKE', 'KEROSENE'):
                if 'kerosene' not in precios or nombre == 'KE':
                    precios['kerosene'] = precio

            # Fecha mas reciente
            fecha = comb.get('precio_fecha', '')
            if fecha and fecha > fecha_mas_reciente:
                fecha_mas_reciente = fecha

        precios['fecha'] = fecha_mas_reciente
        return precios

    def _normalizar_cadena(self, nombre: str) -> str:
        """Normaliza nombre de marca a cadena conocida"""
        if not nombre:
            return "Otra"
        nombre_lower = nombre.lower()
        cadenas = {
            'copec': 'Copec', 'shell': 'Shell', 'aramco': 'Aramco',
            'petrobras': 'Petrobras', 'terpel': 'Terpel',
        }
        for key, value in cadenas.items():
            if key in nombre_lower:
                return value
        return nombre.strip().title() if nombre.strip() else "Otra"


# ============================================
# ORQUESTADOR PRINCIPAL
# ============================================

class OrquestadorScrapers:
    """Orquesta los scrapers, normaliza datos (fechas, regiones, textos)"""

    # Meses en español para normalización de fechas
    MESES_ES = {
        'enero': ('Ene', 1), 'febrero': ('Feb', 2), 'marzo': ('Mar', 3),
        'abril': ('Abr', 4), 'mayo': ('May', 5), 'junio': ('Jun', 6),
        'julio': ('Jul', 7), 'agosto': ('Ago', 8), 'septiembre': ('Sep', 9),
        'octubre': ('Oct', 10), 'noviembre': ('Nov', 11), 'diciembre': ('Dic', 12),
    }
    MESES_NUM_A_ABREV = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
    }

    # Unificación de regiones
    REGIONES_MAP = {
        'metropolitana': 'Metropolitana', 'region metropolitana': 'Metropolitana',
        'región metropolitana': 'Metropolitana', 'r.m.': 'Metropolitana',
        'rm': 'Metropolitana', 'santiago': 'Metropolitana',
        'región metropolitana de santiago': 'Metropolitana',
        'valparaiso': 'Valparaíso', 'valparaíso': 'Valparaíso',
        'v region': 'Valparaíso', 'v región': 'Valparaíso',
        'viña del mar': 'Valparaíso', 'vina del mar': 'Valparaíso',
        'biobio': 'Biobío', 'biobío': 'Biobío', 'bio bio': 'Biobío',
        'viii region': 'Biobío', 'viii región': 'Biobío',
        'concepción': 'Biobío', 'concepcion': 'Biobío',
        'araucanía': 'Araucanía', 'araucania': 'Araucanía',
        'ix region': 'Araucanía', 'temuco': 'Araucanía',
        'coquimbo': 'Coquimbo', 'la serena': 'Coquimbo',
        'antofagasta': 'Antofagasta',
        'atacama': 'Atacama', 'copiapó': 'Atacama', 'copiapo': 'Atacama',
        "o'higgins": "O'Higgins", 'ohiggins': "O'Higgins", 'rancagua': "O'Higgins",
        'maule': 'Maule', 'talca': 'Maule',
        'los ríos': 'Los Ríos', 'los rios': 'Los Ríos', 'valdivia': 'Los Ríos',
        'los lagos': 'Los Lagos', 'puerto montt': 'Los Lagos',
        'aysén': 'Aysén', 'aysen': 'Aysén',
        'magallanes': 'Magallanes', 'punta arenas': 'Magallanes',
        'arica y parinacota': 'Arica y Parinacota', 'arica': 'Arica y Parinacota',
        'tarapacá': 'Tarapacá', 'tarapaca': 'Tarapacá', 'iquique': 'Tarapacá',
        'ñuble': 'Ñuble', 'chillán': 'Ñuble', 'chillan': 'Ñuble',
        # Regiones por número romano
        'i región': 'Tarapacá', 'i region': 'Tarapacá',
        'ii región': 'Antofagasta', 'ii region': 'Antofagasta',
        'iii región': 'Atacama', 'iii region': 'Atacama',
        'iv región': 'Coquimbo', 'iv region': 'Coquimbo',
        'v región': 'Valparaíso',
        'vi región': "O'Higgins", 'vi region': "O'Higgins",
        'vii región': 'Maule', 'vii region': 'Maule',
        'viii región': 'Biobío',
        'ix región': 'Araucanía',
        'x región': 'Los Lagos', 'x region': 'Los Lagos',
        'xi región': 'Aysén', 'xi region': 'Aysén',
        'xii región': 'Magallanes', 'xii region': 'Magallanes',
        'xiv región': 'Los Ríos', 'xiv region': 'Los Ríos',
        'xv región': 'Arica y Parinacota', 'xv region': 'Arica y Parinacota',
        'xvi región': 'Ñuble', 'xvi region': 'Ñuble',
        'región metropolitana': 'Metropolitana',
    }

    # Comunas de la Región Metropolitana
    COMUNAS_RM = [
        'providencia', 'las condes', 'vitacura', 'lo barnechea', 'ñuñoa',
        'la reina', 'peñalolén', 'penalolen', 'macul', 'san joaquín',
        'san joaquin', 'la florida', 'puente alto', 'maipú', 'maipu',
        'cerrillos', 'estación central', 'estacion central', 'quinta normal',
        'renca', 'independencia', 'recoleta', 'conchalí', 'conchali',
        'huechuraba', 'quilicura', 'lampa', 'colina', 'til til',
        'pudahuel', 'lo prado', 'cerro navia', 'pedro aguirre cerda',
        'san miguel', 'san ramón', 'san ramon', 'la granja', 'la pintana',
        'el bosque', 'san bernardo', 'la cisterna', 'lo espejo',
        'padre hurtado', 'peñaflor', 'penaflor', 'talagante', 'buin',
        'paine', 'calera de tango', 'isla de maipo', 'pirque',
        'san josé de maipo', 'san jose de maipo', 'santiago centro',
        'santiago', 'barrio italia', 'barrio lastarria', 'bellavista',
    ]

    def __init__(self):
        self.all_beneficios: List[Beneficio] = []
        self.descuentos_bencina: List[DescuentoBencina] = []
        self.estaciones_bencina: List[EstacionBencina] = []
        self.precios_todas: List[EstacionBencina] = []

    def scrapear_bencinas(self) -> tuple:
        """Scrapea descuentos de bencina y estaciones con precios"""
        print("\n" + "=" * 50)
        print("⛽ INICIANDO SCRAPING DE BENCINAS")
        print("=" * 50 + "\n")

        # 1. Descuentos bancarios
        scraper_desc = ScraperBencina()
        self.descuentos_bencina = scraper_desc.scrapear()

        # 2. Estaciones con precios desde bencinaenlinea.cl
        scraper_est = ScraperBencinaEnLinea()

        # 2a. Todas las estaciones (para comparador de precios)
        self.precios_todas = scraper_est.scrapear(solo_con_descuentos=False)

        # 2b. Solo Copec/Shell/Aramco (para mapa de descuentos)
        self.estaciones_bencina = [
            e for e in self.precios_todas
            if e.cadena.lower() in ('copec', 'shell', 'aramco')
        ]

        print(f"\n✅ BENCINAS: {len(self.descuentos_bencina)} descuentos, "
              f"{len(self.estaciones_bencina)} estaciones con descuentos, "
              f"{len(self.precios_todas)} estaciones totales\n")
        return self.descuentos_bencina, self.estaciones_bencina

    def guardar_bencinas_json(self, filename: str = "bencinas.json"):
        """Guarda descuentos de bencina, estaciones y precios en JSON"""
        data = {
            "descuentos": [d.to_dict() for d in self.descuentos_bencina],
            "estaciones": [e.to_dict() for e in self.estaciones_bencina],
            "precios_todas": [e.to_dict() for e in self.precios_todas],
            "meta": {
                "fecha_scrape": datetime.now().isoformat(),
                "fecha_precios": datetime.now().isoformat(),
                "vigencia_mes": datetime.now().strftime("%Y-%m"),
                "total_descuentos": len(self.descuentos_bencina),
                "total_estaciones": len(self.estaciones_bencina),
                "total_con_precios": len(self.precios_todas),
                "fuente_precios": "Bencinas en Línea - Comisión Nacional de Energía",
                "disclaimer": "Los precios publicados son de exclusiva responsabilidad de las estaciones de servicio informantes",
            }
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Bencinas guardadas en: {filename}")

    def scrapear_todo(self) -> List[Beneficio]:
        """Ejecuta todos los scrapers y normaliza datos"""
        print("\n" + "=" * 50)
        print("🚀 INICIANDO SCRAPING DE BENEFICIOS BANCARIOS")
        print("=" * 50 + "\n")

        resultados = {}

        scrapers = [
            ('Banco de Chile', ScraperBancoChile),
            ('Banco Falabella', ScraperBancoFalabella),
            ('BCI', ScraperBCI),
            ('Banco Itaú', ScraperItau),
            ('Scotiabank', ScraperScotiabank),
            ('Santander', ScraperSantander),
            ('Banco Consorcio', ScraperConsorcio),
            ('BancoEstado', ScraperBancoEstado),
            ('Banco Security', ScraperBancoSecurity),
            ('Banco Ripley', ScraperBancoRipley),
            ('Entel', ScraperEntel),
            ('Tenpo', ScraperTenpo),
            ('Lider BCI', ScraperLiderBCI),
            ('Banco BICE', ScraperBICE),
            ('Mach', ScraperMach),
        ]

        for nombre, ScraperClass in scrapers:
            try:
                scraper = ScraperClass()
                beneficios = scraper.scrapear()
                self.all_beneficios.extend(beneficios)
                resultados[nombre] = len(beneficios)
            except Exception as e:
                print(f"❌ Error con {nombre}: {e}")
                resultados[nombre] = 0
            print()

        # Normalizar todos los beneficios
        print("🔧 Normalizando datos...")
        self._normalizar_todos()

        print("=" * 50)
        print(f"✅ TOTAL BENEFICIOS EXTRAÍDOS: {len(self.all_beneficios)}")
        for nombre, count in resultados.items():
            print(f"   • {nombre}: {count}")
        print("=" * 50 + "\n")

        return self.all_beneficios

    # ── Normalización ──

    def _normalizar_todos(self):
        """Aplica todas las normalizaciones a los beneficios"""
        for b in self.all_beneficios:
            # Fechas → DD-MMM-AAAA
            b.valido_desde = self._normalizar_fecha(b.valido_desde)
            b.valido_hasta = self._normalizar_fecha(b.valido_hasta)

            # Regiones unificadas
            b.ubicacion = self._normalizar_region(b.ubicacion)

            # Extraer comuna para RM
            if b.ubicacion == 'Metropolitana':
                b.comuna = self._extraer_comuna(b.direccion, b.restricciones_texto, b.descripcion)

            # Textos limpios
            b.descuento_texto = self._limpiar_texto(b.descuento_texto)
            b.restricciones_texto = self._limpiar_texto(b.restricciones_texto, max_len=200)
            b.descripcion = self._limpiar_texto(b.descripcion, max_len=200)

            # Normalizar descuento_texto
            b.descuento_texto = self._normalizar_descuento_texto(b.descuento_texto)

    def _normalizar_fecha(self, fecha_str: str) -> str:
        """Convierte fecha a formato DD-MMM-AAAA (ej: 31-Mar-2026)"""
        if not fecha_str or not fecha_str.strip():
            return ''

        fecha_str = fecha_str.strip()

        # Ya en formato DD-MMM-AAAA
        if re.match(r'^\d{1,2}-[A-Z][a-z]{2}-\d{4}$', fecha_str):
            return fecha_str

        # Formato ISO: 2025-08-31 o 2025-08-31T...
        match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', fecha_str)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            abrev = self.MESES_NUM_A_ABREV.get(m, 'Ene')
            return f"{d:02d}-{abrev}-{y}"

        # Formato "31 de marzo de 2026" o "31 de marzo 2026"
        match = re.search(r'(\d{1,2})\s+de\s+(\w+)(?:\s+de)?\s+(\d{4})', fecha_str, re.IGNORECASE)
        if match:
            d = int(match.group(1))
            mes_nombre = match.group(2).lower()
            y = int(match.group(3))
            mes_info = self.MESES_ES.get(mes_nombre)
            if mes_info:
                return f"{d:02d}-{mes_info[0]}-{y}"

        # Formato "marzo 2026" (sin día)
        match = re.search(r'(\w+)\s+(\d{4})', fecha_str, re.IGNORECASE)
        if match:
            mes_nombre = match.group(1).lower()
            y = int(match.group(2))
            mes_info = self.MESES_ES.get(mes_nombre)
            if mes_info:
                return f"01-{mes_info[0]}-{y}"

        # Formato DD/MM/YYYY
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', fecha_str)
        if match:
            d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
            abrev = self.MESES_NUM_A_ABREV.get(m, 'Ene')
            return f"{d:02d}-{abrev}-{y}"

        return fecha_str

    def _normalizar_region(self, ubicacion: str) -> str:
        """Unifica variantes de regiones chilenas"""
        if not ubicacion or not ubicacion.strip():
            return ''

        ubicacion_lower = ubicacion.strip().lower()

        # Búsqueda directa
        if ubicacion_lower in self.REGIONES_MAP:
            return self.REGIONES_MAP[ubicacion_lower]

        # Búsqueda parcial
        for keyword, region in self.REGIONES_MAP.items():
            if keyword in ubicacion_lower:
                return region

        # Si contiene una comuna de RM, es Metropolitana
        for comuna in self.COMUNAS_RM:
            if comuna in ubicacion_lower:
                return 'Metropolitana'

        return ubicacion.strip()

    def _extraer_comuna(self, direccion: str, restricciones: str, descripcion: str) -> str:
        """Extrae la comuna dentro de la Región Metropolitana"""
        textos = f"{direccion} {restricciones} {descripcion}".lower()
        for comuna in self.COMUNAS_RM:
            if comuna in textos:
                # Capitalizar correctamente
                return comuna.title()
        return ''

    def _limpiar_texto(self, texto: str, max_len: int = 300) -> str:
        """Limpia texto: elimina HTML, 'P' sueltas, trunca"""
        if not texto:
            return ''

        # Eliminar tags HTML residuales
        texto = re.sub(r'<[^>]+>', ' ', texto)

        # Eliminar entidades HTML
        texto = re.sub(r'&[a-z]+;', ' ', texto)
        texto = re.sub(r'&#\d+;', ' ', texto)

        # Eliminar "P" sueltas al final (viene de HTML mal cortado)
        texto = re.sub(r'\s+P\s*$', '', texto)
        texto = re.sub(r'\s+P\s+', ' ', texto)

        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto).strip()

        # Truncar con "..."
        if len(texto) > max_len:
            texto = texto[:max_len - 3].rsplit(' ', 1)[0] + '...'

        return texto

    def _normalizar_descuento_texto(self, texto: str) -> str:
        """Normaliza texto de descuento"""
        if not texto:
            return ''
        # Remove stray semicolons: "20%; dto." → "20% dto."
        texto = texto.replace('%;', '%')
        # "50% dto." → "50% dcto."
        texto = re.sub(r'(\d+)%\s*dto\.?', r'\1% dcto.', texto, flags=re.IGNORECASE)
        # "50% de descuento" → "50% dcto."
        texto = re.sub(r'(\d+)%\s*de\s*descuento', r'\1% dcto.', texto, flags=re.IGNORECASE)
        # "50% descuento" → "50% dcto."
        texto = re.sub(r'(\d+)%\s*descuento', r'\1% dcto.', texto, flags=re.IGNORECASE)
        # "50% dscto." → "50% dcto."
        texto = re.sub(r'(\d+)%\s*dscto\.?', r'\1% dcto.', texto, flags=re.IGNORECASE)
        return texto

    def guardar_json(self, filename: str = "beneficios.json"):
        """Guarda los beneficios en JSON"""
        data = [b.to_dict() for b in self.all_beneficios]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Datos guardados en: {filename} ({len(data)} beneficios)")

    def guardar_csv(self, filename: str = "beneficios.csv"):
        """Guarda los beneficios en CSV"""
        import csv
        if not self.all_beneficios:
            print("❌ No hay beneficios para guardar")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = list(self.all_beneficios[0].to_dict().keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for b in self.all_beneficios:
                row = b.to_dict()
                # Convert lists to strings for CSV
                for k, v in row.items():
                    if isinstance(v, list):
                        row[k] = ', '.join(str(i) for i in v)
                writer.writerow(row)
        print(f"💾 Datos guardados en: {filename}")


# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    orquestador = OrquestadorScrapers()

    # Scraping de beneficios bancarios (restaurantes)
    beneficios = orquestador.scrapear_todo()
    orquestador.guardar_json("beneficios.json")
    orquestador.guardar_csv("beneficios.csv")

    # Scraping de bencinas
    descuentos_bencina, estaciones = orquestador.scrapear_bencinas()
    orquestador.guardar_bencinas_json("bencinas.json")

    # Mostrar muestra de beneficios
    print("\n📋 MUESTRA DE BENEFICIOS:\n")
    for b in beneficios[:5]:
        print(f"  • {b.restaurante} ({b.banco})")
        print(f"    Descuento: {b.descuento_texto}")
        print(f"    Días: {', '.join(b.dias_validos)}")
        print(f"    Ubicación: {b.ubicacion}\n")

    # Mostrar muestra de bencinas
    print("⛽ MUESTRA DE DESCUENTOS BENCINA:\n")
    for d in descuentos_bencina[:5]:
        print(f"  • {d.cadena} - {d.banco}")
        print(f"    Descuento: {d.descuento_texto}")
        print(f"    Días: {', '.join(d.dias_validos)}")
        print(f"    Condición: {d.condicion}\n")

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

            seen = set()
            for card in cards:
                beneficio = self._parsear_card(card)
                if beneficio:
                    key = beneficio.restaurante.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        self.beneficios.append(beneficio)

            print(f"✅ {self.BANCO}: {len(self.beneficios)} beneficios extraídos (deduplicados)")
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

            beneficio_id = re.sub(r'[^a-z0-9]', '_', nombre.lower())

            return Beneficio(
                id=f"itau_{beneficio_id}",
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

            # Web
            web = sitio.get('web', '')

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
                url_fuente=web or self.PAGE_URL,
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
# ORQUESTADOR PRINCIPAL
# ============================================

class OrquestadorScrapers:
    """Orquesta los scrapers y normaliza datos"""

    def __init__(self):
        self.all_beneficios: List[Beneficio] = []

    def scrapear_todo(self) -> List[Beneficio]:
        """Ejecuta todos los scrapers"""
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

        print("=" * 50)
        print(f"✅ TOTAL BENEFICIOS EXTRAÍDOS: {len(self.all_beneficios)}")
        for nombre, count in resultados.items():
            print(f"   • {nombre}: {count}")
        print("=" * 50 + "\n")

        return self.all_beneficios

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
    beneficios = orquestador.scrapear_todo()

    orquestador.guardar_json("beneficios.json")
    orquestador.guardar_csv("beneficios.csv")

    # Mostrar muestra
    print("\n📋 MUESTRA DE BENEFICIOS:\n")
    for b in beneficios[:5]:
        print(f"  • {b.restaurante} ({b.banco})")
        print(f"    Descuento: {b.descuento_texto}")
        print(f"    Días: {', '.join(b.dias_validos)}")
        print(f"    Ubicación: {b.ubicacion}\n")

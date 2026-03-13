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

        # Banco de Chile
        scraper_chile = ScraperBancoChile()
        beneficios_chile = scraper_chile.scrapear()
        self.all_beneficios.extend(beneficios_chile)

        print()

        # Banco Falabella
        scraper_falabella = ScraperBancoFalabella()
        beneficios_falabella = scraper_falabella.scrapear()
        self.all_beneficios.extend(beneficios_falabella)

        print("\n" + "=" * 50)
        print(f"✅ TOTAL BENEFICIOS EXTRAÍDOS: {len(self.all_beneficios)}")
        print(f"   • Banco de Chile: {len(beneficios_chile)}")
        print(f"   • Banco Falabella: {len(beneficios_falabella)}")
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

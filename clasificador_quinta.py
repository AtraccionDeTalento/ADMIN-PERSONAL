# ═══════════════════════════════════════════════════════════════════════════════
#  clasificador_quinta.py — Motor de clasificación DJ Quinta Categoría
#  People Analytics USIL
#
#  Extrae y clasifica PDFs de "Declaración Jurada de Quinta" para
#  determinar la categoría tributaria del colaborador.
#
#  Usos:
#    • OCR automático para PDFs escaneados (requiere Tesseract)
#    • Soporte de formato estándar Y formato antiguo (distintas posiciones)
#    • Extracción de nombre desde carpeta padre (patrón "12345 - APELLIDOS NOMBRE")
#
#  Categorías:
#   1A: USIL único empleador + SÍ percibió renta quinta antes
#   1B: USIL único empleador + NO percibió renta quinta antes
#   2:  USIL empleador principal + percibe quinta en otras empresas
#   3:  USIL NO es empleador principal
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
import sys
import json
import shelve
import hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Compatibilidad con pythonw.exe (sin consola)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

try:
    import fitz  # PyMuPDF
except ImportError:
    print("[ERROR] PyMuPDF no instalado. Ejecuta INICIAR.bat.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# OCR (opcional — no falla si no está instalado)
# ─────────────────────────────────────────────────────────────────────────────

_pytesseract = None
_PIL_Image   = None
_PIL_ImageOps = None
_OCR_DISPONIBLE = False

_google_vision   = None
_VISION_DISPONIBLE = False

# ─────────────────────────────────────────────────────────────────────────────
# CACHÉ DE OCR  (shelve — built-in Python, cero dependencias extra)
# Hash MD5 del archivo → datos DNI extraídos. Respuesta instantánea en re-runs.
# ─────────────────────────────────────────────────────────────────────────────

_CACHE_DB = str(Path(__file__).parent / 'cache_ocr_dni')

def _cache_key(archivo_path):
    """MD5 de los primeros 128 KB del archivo (rápido, detecta cambios)."""
    try:
        h = hashlib.md5()
        with open(archivo_path, 'rb') as f:
            h.update(f.read(131072))
        return h.hexdigest()
    except Exception:
        return None

def _cache_get(archivo_path):
    try:
        key = _cache_key(archivo_path)
        if not key:
            return None
        with shelve.open(_CACHE_DB) as db:
            return db.get(key)
    except Exception:
        return None

def _cache_set(archivo_path, datos):
    try:
        key = _cache_key(archivo_path)
        if not key:
            return
        with shelve.open(_CACHE_DB) as db:
            db[key] = datos
    except Exception:
        pass

# Extensiones de archivo soportadas
_EXTENSIONES_PDF = {'.pdf'}
_EXTENSIONES_IMAGEN = {'.jpg', '.jpeg', '.png', '.jfif', '.bmp', '.tiff', '.tif', '.gif', '.webp'}
_EXTENSIONES_SOPORTADAS = _EXTENSIONES_PDF | _EXTENSIONES_IMAGEN

def _inicializar_ocr():
    global _pytesseract, _PIL_Image, _PIL_ImageOps, _OCR_DISPONIBLE
    if _OCR_DISPONIBLE:
        return True
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance

        # Rutas comunes de Tesseract en Windows
        _rutas_tesseract = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'),
            os.path.expanduser(r'~\AppData\Local\Tesseract-OCR\tesseract.exe'),
            r'C:\Tesseract-OCR\tesseract.exe',
        ]

        for _path in _rutas_tesseract:
            if os.path.exists(_path):
                pytesseract.pytesseract.tesseract_cmd = _path
                break

        # Verificar que funciona
        pytesseract.get_tesseract_version()
        _pytesseract  = pytesseract
        _PIL_Image    = Image
        _PIL_ImageOps = ImageOps
        _OCR_DISPONIBLE = True
        return True
    except Exception:
        return False


def _inicializar_google_vision():
    global _google_vision, _VISION_DISPONIBLE
    if _VISION_DISPONIBLE:
        return True
    try:
        from google.cloud import vision as _gv
        _google_vision = _gv
        _VISION_DISPONIBLE = True
        return True
    except Exception:
        return False


def _ocr_google_vision(img_pil):
    """Envía una imagen PIL a Google Cloud Vision y devuelve el texto extraído."""
    import io
    try:
        client = _google_vision.ImageAnnotatorClient()
        buf = io.BytesIO()
        img_pil.save(buf, format='PNG')
        imagen = _google_vision.Image(content=buf.getvalue())
        respuesta = client.text_detection(image=imagen)
        if respuesta.error.message:
            return None
        anotaciones = respuesta.text_annotations
        return anotaciones[0].description if anotaciones else None
    except Exception:
        return None


def _mejorar_contraste_dni(img):
    """Aplica solo contraste + nitidez SIN escalar (para imágenes ya en alta resolución)."""
    from PIL import ImageFilter
    img = _PIL_ImageOps.grayscale(img)
    img = _PIL_ImageOps.autocontrast(img, cutoff=1)
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    return img



def _mejorar_imagen_dni(img):
    """Escala y limpia imagen de DNI/CUI para mejorar OCR en fotos de baja resolución."""
    from PIL import ImageFilter

    # Normalizar modo de color antes de preprocesar
    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    lado_menor = min(img.width, img.height)
    if lado_menor > 0 and lado_menor < 900:
        escala = min(8.0, max(3.0, 900 / lado_menor))
        img = img.resize(
            (int(img.width * escala), int(img.height * escala)),
            _PIL_Image.Resampling.LANCZOS
        )

    img = _PIL_ImageOps.grayscale(img)
    img = _PIL_ImageOps.autocontrast(img, cutoff=1)
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    return img



# ─────────────────────────────────────────────────────────────────────────────
# ARCHIVOS QUE NO SON QUINTA (filtro rápido por nombre para ahorrar tiempo)
# ─────────────────────────────────────────────────────────────────────────────

# Nombres de archivo que NUNCA son una declaración de quinta
_SKIP_FILENAME_PATTERNS = [
    'carta oferta', 'contrato', 'liquidacion', 'boleta',
    'recibo', 'planilla', 'constancia', 'certificado',
    'memoran', 'memo ',
]

# Frases que confirman que el PDF es una declaración de quinta (cualquiera basta)
_QUINTA_KWORDS = [
    'DECLARACION JURADA DE QUINTA',
    'DECLARACION JURADA QUINTA',
    'QUINTA CATEGORIA',
    'QUINTA CATEGOR',
    '5TA CATEGORIA',
    '5TA. CATEGORIA',
    '5° CATEGORIA',
    'RETENCIONES DE QUINTA',
    'RETENCION DE QUINTA',
    'RENTA DE QUINTA',
    'RENTA 5TA',
    'IMPUESTO QUINTA',
    'CATEGORIA QUINTA',
    'RENDIMIENTO DE QUINTA',
]

def _es_posible_quinta(file_path: Path) -> bool:
    """Heurística rápida por nombre de archivo para saltar archivos claramente no-quinta."""
    name = file_path.name.lower()
    ext = file_path.suffix.lower()

    # Para imágenes, ser más permisivo (necesitan OCR para determinar contenido)
    if ext in _EXTENSIONES_IMAGEN:
        # Solo saltar si el nombre indica claramente que NO es quinta
        for pat in ['boleta', 'recibo', 'planilla']:
            if pat in name:
                return False
        return True  # Procesar la imagen y dejar que el OCR determine

    # Para PDFs, mantener filtro original
    for pat in _SKIP_FILENAME_PATTERNS:
        if pat in name:
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORÍAS
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIAS = {
    '1A': {
        'codigo': '1A',
        'nombre': 'Único Empleador - Con renta quinta previa',
        'descripcion': 'USIL es su único empleador. SÍ percibió renta de quinta categoría antes de ingresar a USIL.',
        'color': '#2196F3'
    },
    '1B': {
        'codigo': '1B',
        'nombre': 'Único Empleador - Sin renta quinta previa',
        'descripcion': 'USIL es su único empleador. NO percibió renta de quinta categoría antes de ingresar a USIL.',
        'color': '#4CAF50'
    },
    '2': {
        'codigo': '2',
        'nombre': 'Empleador Principal + Otros ingresos',
        'descripcion': 'USIL es su empleador principal pero percibe quinta categoría en otras empresas adicionales.',
        'color': '#FF9800'
    },
    '3': {
        'codigo': '3',
        'nombre': 'NO es Empleador Principal',
        'descripcion': 'USIL NO es su empleador principal. Solicita no efectuar retenciones de quinta categoría.',
        'color': '#F44336'
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# IDENTIFICADOR DE DNI CORRECTO EN CARPETA DE PERSONA
# ─────────────────────────────────────────────────────────────────────────────

def _extraer_datos_documento_dni(texto):
    """Extrae apellidos, prenombres, número y sexo de texto OCR de un DNI/CUI peruano."""
    if not texto:
        return {}
    t = texto.upper()
    apellidos = prenombres = numero = sexo = None

    # ── Formato nuevo CUI vertical: "Apellidos\nFIGUEROA RODRIGUEZ\nPrenombres\nLUIS ABELARDO"
    m = re.search(r'APELLIDOS?\s*[\n\r:]+\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,40}?)[\n\r]', t)
    if m:
        apellidos = m.group(1).strip()
    m = re.search(r'PRENOMBRES?\s*[\n\r:]+\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,40}?)[\n\r]', t)
    if m:
        prenombres = m.group(1).strip()

    # ── Formato antiguo DNI horizontal: "Primer Apellido X  Segundo Apellido Y"
    if not apellidos:
        m1 = re.search(r'PRIMER\s+APELLIDO\s+([A-ZÁÉÍÓÚÑ]+)', t)
        m2 = re.search(r'SEGUNDO\s+APELLIDO\s+([A-ZÁÉÍÓÚÑ]+)', t)
        if m1 and m2:
            apellidos = m1.group(1) + ' ' + m2.group(1)
        elif m1:
            apellidos = m1.group(1)
    if not prenombres:
        m = re.search(r'PRE\s*NOMBRES?\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,40}?)(?:\s{2,}|\n|\r)', t)
        if m:
            prenombres = m.group(1).strip()

    # ── Número desde MRZ línea 1: "I<PER72958419<1" o "1<PERU46934697..."
    # NOTA: OCR puede leer la 'I' latina como '1' o viceversa, aceptar ambos
    m = re.search(r'[I1][<\s]?PER[UO]?(\d{8})', t)
    if m:
        numero = m.group(1)

    # ── Número desde campo explícito DNI / CUI
    if not numero:
        m = re.search(r'(?:DNI|CUI|N[UÚ]MERO)[^\d]{0,10}(\d{8})', t)
        if m:
            numero = m.group(1)

    # ── Fallback: primer número de 8 dígitos que no sea fecha
    if not numero:
        for c in re.findall(r'\b(\d{8})\b', texto):
            if not re.match(r'(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])\d{4}', c):
                numero = c
                break

    # ── Sexo desde campo explícito
    m = re.search(r'SEXO\s*[\n\r:]+\s*([MF])\b', t)
    if m:
        sexo = m.group(1)
    # ── Sexo desde MRZ línea 2: "{6digitos}{check}[M/F]..."
    if not sexo:
        m = re.search(r'\d{7}([MF])\d', t)
        if m:
            sexo = m.group(1)
    if not sexo:
        m = re.search(r'\bSEXO\b[^\n]{0,10}\b([MF])\b', t)
        if m:
            sexo = m.group(1)

    # ── Fallback MRZ línea 3: "RODRIGUEZ<<FLORES<<PERPETUA<<<"
    if not apellidos or not prenombres:
        m = re.search(r'([A-Z]{2,20})<<([A-Z]{2,20})<<([A-Z<]{2,40})', t)
        if m:
            if not apellidos:
                apellidos = m.group(1) + ' ' + m.group(2)
            if not prenombres:
                prenombres = re.sub(r'<+', ' ', m.group(3)).strip()

    nombre_completo = ' '.join(filter(None, [apellidos, prenombres])) or None
    return {
        'apellidos':       apellidos,
        'prenombres':      prenombres,
        'nombre_completo': nombre_completo,
        'numero':          numero,
        'sexo':            sexo,
    }


def _puntaje_match_dni(datos_dni, nombre_carpeta):
    """Devuelve un score 0.0–1.0 de qué tan bien coincide el DNI con el nombre de la carpeta."""
    if not nombre_carpeta:
        return 0.0
    
    limpiar = lambda s: re.sub(r'[^A-ZÁÉÍÓÚÑ\s]', '', s.upper())
    palabras_carpeta = set(limpiar(nombre_carpeta).split()) - {'DE', 'LA', 'LOS', 'DEL'}
    if not palabras_carpeta:
        return 0.0

    # Score por nombre detectado dentro del DNI vía OCR
    nombre_dni = datos_dni.get('nombre_completo')
    score_ocr = 0.0
    if nombre_dni:
        palabras_dni = set(limpiar(nombre_dni).split())
        if palabras_dni:
            coincidencias = palabras_carpeta & palabras_dni
            score_ocr = len(coincidencias) / len(palabras_carpeta)

    # Score por texto crudo del OCR (especial para atrapar el MRZ ej: MAYERLY<HARLEY)
    texto_crudo = datos_dni.get('texto_crudo', '')
    score_texto = 0.0
    if texto_crudo:
        texto_limpio = texto_crudo.replace('<', ' ')
        palabras_texto = set(limpiar(texto_limpio).split())
        if palabras_texto:
            coincidencias_txt = palabras_carpeta & palabras_texto
            score_texto = len(coincidencias_txt) / len(palabras_carpeta)

    # Score por nombre de archivo (ej. "DNI Helen Porras.pdf")
    archivo = datos_dni.get('archivo_dni')
    score_archivo = 0.0
    if archivo:
        palabras_archivo = set(limpiar(archivo).split()) - {'PDF', 'JPG', 'PNG', 'JPEG', 'DNI', 'CUI'}
        if palabras_archivo:
            coincidencias_arch = palabras_carpeta & palabras_archivo
            score_archivo = len(coincidencias_arch) / len(palabras_carpeta)

    return max(score_ocr, score_archivo, score_texto)


# ─────────────────────────────────────────────────────────────────────────────
# CLASIFICADOR
# ─────────────────────────────────────────────────────────────────────────────

class ClasificadorQuinta:
    """
    Analiza PDFs de Declaración Jurada de Quinta y clasifica al colaborador.
    Soporta: PDFs nativos, PDFs escaneados (OCR), formato estándar y antiguo.
    """

    # ── Rangos Y para formato ESTÁNDAR (nuevo) ───────────────────────────────
    CHECKBOX_Y_STD = {
        'opcion1': (170, 210),
        'opcion2': (230, 270),
        'opcion3': (275, 320),
    }

    # ── Rangos Y para formato ANTIGUO (más largo) ───────────────────────────
    CHECKBOX_Y_OLD = {
        'opcion1': (140, 180),
        'opcion2': (200, 250),
        'opcion3': (255, 310),
    }

    # ── Rangos extra amplios como último recurso ──────────────────────────────
    CHECKBOX_Y_WIDE = {
        'opcion1': (100, 250),
        'opcion2': (200, 350),
        'opcion3': (280, 450),
    }

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def analizar_archivo(self, archivo_path):
        """Punto de entrada unificado: detecta tipo de archivo y procesa."""
        archivo_path = Path(archivo_path)
        ext = archivo_path.suffix.lower()

        if ext in _EXTENSIONES_PDF:
            return self.analizar_pdf(archivo_path)
        elif ext in _EXTENSIONES_IMAGEN:
            return self.analizar_imagen(archivo_path)
        else:
            return self._error(f'Formato no soportado: {ext}', archivo_path.name)

    def analizar_imagen(self, img_path):
        """Analiza una imagen (JPG, PNG, JFIF, etc.) usando OCR."""
        img_path = Path(img_path)

        if not img_path.exists():
            return self._error(f'Archivo no encontrado: {img_path}', img_path.name)

        if not _inicializar_ocr():
            return self._error('OCR no disponible. Instala Tesseract.', img_path.name)

        persona = self._extraer_persona_carpeta(img_path)

        try:
            img = _PIL_Image.open(str(img_path))
            # Si el archivo se llama "DNI" o "CUI", agrandamos la imagen antes de rotar
            # Esto ayuda enormemente a Tesseract con documentos pequeños
            es_dni_doc = 'dni' in img_path.name.lower() or 'cui' in img_path.name.lower()

            # Intentar OCR con todas las rotaciones posibles
            # Priorizar 0° y 180° (documentos al revés son comunes)
            mejor_texto = ''
            mejor_longitud = 0
            mejor_angulo = 0
            rotaciones = [0, 180, 90, 270]

            if es_dni_doc:
                img = _mejorar_imagen_dni(img)
                # Intentar Google Vision primero (más preciso que Tesseract para DNIs)
                if _inicializar_google_vision():
                    texto_vision = _ocr_google_vision(img)
                    if texto_vision and len(re.sub(r'\s', '', texto_vision)) > 20:
                        mejor_texto    = texto_vision
                        mejor_longitud = len(re.sub(r'\s', '', texto_vision))
                        mejor_angulo   = 'vision'

            # Convertir a RGB si no se procesó como DNI (DNIs ya quedan en escala de grises)
            if not es_dni_doc:
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

            # Si Google Vision ya obtuvo texto, saltar el pipeline Tesseract
            if not mejor_texto:
                # Primera pasada: buscar rotación con texto de quinta
                for angulo in rotaciones:
                    img_rot = img.rotate(angulo, expand=True) if angulo != 0 else img

                    try:
                        # Usar psm 6 para documentos con bloques de texto
                        texto = _pytesseract.image_to_string(
                            img_rot,
                            lang='spa+eng',
                            config='--psm 6 --oem 3'
                        )
                        texto_norm = self._normalizar(texto)
                        longitud = len(re.sub(r'\s', '', texto))

                        # Si encontramos indicadores de quinta, usar este texto y SALIR (Fast Path)
                        if self._es_declaracion_quinta(texto_norm):
                            mejor_texto = texto
                            mejor_longitud = longitud
                            mejor_angulo = angulo
                            break # Encontrado, no perder tiempo en más rotaciones
                    except Exception:
                        continue

                # Si no encontró quinta, intentar con psm 3 y 4
                if not mejor_texto:
                    for psm in ['--psm 3', '--psm 4', '--psm 1']:
                        for angulo in rotaciones:
                            img_rot = img.rotate(angulo, expand=True) if angulo != 0 else img
                            try:
                                texto = _pytesseract.image_to_string(
                                    img_rot,
                                    lang='spa+eng',
                                    config=f'{psm} --oem 3'
                                )
                                texto_norm = self._normalizar(texto)
                                longitud = len(re.sub(r'\s', '', texto))

                                if self._es_declaracion_quinta(texto_norm) and longitud > mejor_longitud:
                                    mejor_texto = texto
                                    mejor_longitud = longitud
                                    mejor_angulo = angulo
                            except Exception:
                                continue
                        if mejor_texto:
                            break

                # Fallback: usar el texto más largo
                if not mejor_texto:
                    for angulo in rotaciones:
                        img_rot = img.rotate(angulo, expand=True) if angulo != 0 else img
                        try:
                            texto = _pytesseract.image_to_string(
                                img_rot,
                                lang='spa+eng',
                                config='--psm 6 --oem 3'
                            )
                            longitud = len(re.sub(r'\s', '', texto))
                            if longitud > mejor_longitud:
                                mejor_texto = texto
                                mejor_longitud = longitud
                                mejor_angulo = angulo
                        except Exception:
                            continue

            if not mejor_texto or mejor_longitud < 50:
                return {
                    'status': 'WARNING',
                    'archivo': img_path.name,
                    'nombre': persona or 'No identificado',
                    'persona': persona,
                    'categoria': None, 'categoria_info': None,
                    'confianza': 0, 'metodo': 'imagen_ocr_fallido',
                    'mensaje': 'No se pudo extraer texto de la imagen'
                }

            texto_completo = mejor_texto
            texto_norm = self._normalizar(texto_completo)

            # Verificar que es declaración de quinta
            if not self._es_declaracion_quinta(texto_norm):
                return {
                    'status': 'WARNING',
                    'archivo': img_path.name,
                    'nombre': persona or 'No identificado',
                    'persona': persona,
                    'categoria': None, 'categoria_info': None,
                    'confianza': 0, 'metodo': 'imagen_no_quinta',
                    'mensaje': 'No parece ser una Declaración de Quinta'
                }

            nombre = self._extraer_nombre(texto_completo, img_path)

            # MÉTODO: Texto "-X" / "[X]"
            categoria, confianza, metodo = self._detectar_por_texto(texto_completo)

            # MÉTODO: Keywords
            if categoria is None:
                categoria, confianza, metodo = self._detectar_por_keywords(texto_completo)

            metodo += f'+OCR_IMG_{mejor_angulo}°' if mejor_angulo != 'vision' else '+GoogleVision'

            if categoria is None:
                return {
                    'status': 'WARNING',
                    'archivo': img_path.name,
                    'nombre': nombre,
                    'persona': persona,
                    'categoria': None, 'categoria_info': None,
                    'confianza': 0, 'metodo': metodo,
                    'mensaje': 'No se pudo determinar la categoría. Verificar manualmente.'
                }

            dni = self._extraer_dni(texto_completo)

            return {
                'status': 'OK',
                'archivo': img_path.name,
                'nombre': nombre,
                'persona': persona,
                'dni': dni,
                'categoria': categoria,
                'categoria_info': CATEGORIAS.get(categoria, {}),
                'confianza': confianza,
                'metodo': metodo,
                'mensaje': f'Categoría {categoria}: {CATEGORIAS[categoria]["nombre"]}'
            }

        except Exception as e:
            return self._error(f'Error procesando imagen: {e}', img_path.name)

    def analizar_pdf(self, pdf_path):
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return self._error(f'Archivo no encontrado: {pdf_path}', pdf_path.name)

        # Filtro rápido por nombre
        if not _es_posible_quinta(pdf_path):
            return self._error(f'Archivo omitido (no parece quinta): {pdf_path.name}', pdf_path.name)

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            return self._error(f'No se pudo abrir PDF: {e}', pdf_path.name)

        if len(doc) == 0:
            doc.close()
            return self._error('PDF vacío (sin páginas)', pdf_path.name)

        page = doc[0]
        texto_completo = page.get_text()
        usa_ocr = False

        # ── OCR si el texto nativo es insuficiente ────────────────────────────
        es_escaneado = self._necesita_ocr(texto_completo)
        if es_escaneado:
            # Si el nombre del archivo sugiere que es un DNI, usamos escala 4.0
            es_dni_doc = 'dni' in pdf_path.name.lower() or 'cui' in pdf_path.name.lower()
            scale = 4.0 if es_dni_doc else 2.0
            
            texto_ocr = self._texto_via_ocr(page, scale=scale)
            if texto_ocr and len(texto_ocr.strip()) > 30: # Bajado de 60 para capturar DNI cortos
                texto_completo = texto_ocr
                usa_ocr = True

        # ── Verificar que es Declaración Jurada de Quinta ─────────────────────
        texto_norm = self._normalizar(texto_completo)
        es_quinta = self._es_declaracion_quinta(texto_norm)
        
        # Si NO es quinta pero es un DNI, permitimos que continúe para extraer el DNI
        es_dni_por_nombre = 'dni' in pdf_path.name.lower() or 'cui' in pdf_path.name.lower()
        
        if not es_quinta and not es_dni_por_nombre:
            # Segunda oportunidad: OCR aunque ya haya algo de texto (PDF mixto/escaneado)
            if not usa_ocr:
                texto_ocr = self._texto_via_ocr(page)
                texto_norm2 = self._normalizar(texto_ocr or '')
                if self._es_declaracion_quinta(texto_norm2):
                    texto_completo = texto_ocr
                    usa_ocr = True
                    texto_norm = texto_norm2
                elif es_escaneado:
                    # PDF escaneado pero Tesseract no disponible — aparece como WARNING
                    doc.close()
                    persona = self._extraer_persona_carpeta(pdf_path)
                    return {
                        'status': 'WARNING',
                        'archivo': pdf_path.name,
                        'nombre': persona or 'No identificado',
                        'persona': persona,
                        'categoria': None, 'categoria_info': None,
                        'confianza': 0, 'metodo': 'escaneado_sin_ocr',
                        'mensaje': 'PDF escaneado — instala Tesseract OCR para clasificar'
                    }
                else:
                    doc.close()
                    return self._error('No es una Declaración Jurada de Quinta', pdf_path.name)
            else:
                doc.close()
                return self._error('No es una Declaración Jurada de Quinta', pdf_path.name)

        nombre  = self._extraer_nombre(texto_completo, pdf_path)
        persona = self._extraer_persona_carpeta(pdf_path)

        # ── MÉTODO 1: Drawings (checkboxes gráficos) — solo para PDFs nativos ─
        categoria, confianza, metodo = None, 0, 'ninguno'

        if not usa_ocr:
            opcion_principal, confianza, metodo = self._detectar_por_drawings(page)
            if opcion_principal:
                categoria = self._resolver_categoria(opcion_principal, texto_completo, page)
                if categoria:
                    metodo = 'drawings+texto'

        # ── MÉTODO 1b: Formato antiguo — "X" texto + posición relativa a "1.-/2.-/3.-" ─
        if categoria is None and not usa_ocr:
            categoria, confianza, metodo = self._detectar_formato_antiguo(page)

        # ── MÉTODO 1c: Widgets de formulario PDF ─────────────────────────────
        if categoria is None and not usa_ocr:
            categoria, confianza, metodo = self._detectar_por_widgets(page)

        # ── MÉTODO 2: Texto "-X" / "[X]" (funciona también con OCR) ──────────
        if categoria is None:
            categoria, confianza, metodo = self._detectar_por_texto(texto_completo)

        # ── MÉTODO 3: Spans bold (solo nativo) ──────────────────────────────
        if categoria is None and not usa_ocr:
            categoria, confianza, metodo = self._detectar_por_spans(page)

        # ── MÉTODO 4: Palabras clave robustas (más permisivo) ─────────────────
        if categoria is None:
            categoria, confianza, metodo = self._detectar_por_keywords(texto_completo)

        doc.close()

        if usa_ocr:
            metodo += '+OCR'

        if categoria is None:
            return {
                'status': 'WARNING',
                'archivo': pdf_path.name,
                'nombre':  nombre,
                'persona': persona,
                'categoria': None, 'categoria_info': None,
                'confianza': 0, 'metodo': metodo,
                'mensaje': 'No se pudo determinar la categoría. Verificar manualmente.'
            }

        dni = self._extraer_dni(texto_completo)

        return {
            'status': 'OK',
            'archivo': pdf_path.name,
            'nombre':  nombre,
            'persona': persona,
            'dni': dni,
            'categoria': categoria,
            'categoria_info': CATEGORIAS.get(categoria, {}),
            'confianza': confianza,
            'metodo': metodo,
            'mensaje': f'Categoría {categoria}: {CATEGORIAS[categoria]["nombre"]}'
        }

    # ─────────────────────────────────────────────────────────────────────────
    # OCR
    # ─────────────────────────────────────────────────────────────────────────

    def _necesita_ocr(self, texto):
        """True si el texto nativo es insuficiente (PDF escaneado)."""
        texto_limpio = re.sub(r'[\s\n\r\t]', '', texto)
        return len(texto_limpio) < 120

    def _texto_via_ocr(self, page, scale=2.0):
        """
        Renderiza la página y aplica Tesseract OCR con pre-procesamiento avanzado.
        Imita el comportamiento humano: si no se ve bien, aumenta el zoom y el contraste.
        """
        if not _inicializar_ocr():
            return ''
        
        try:
            # 1. Renderizar a la resolución solicitada
            mat = fitz.Matrix(scale, scale) 
            pix = page.get_pixmap(matrix=mat)
            img = _PIL_Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 2. Pre-procesamiento de imagen (Mejora de lectura)
            # Convertir a escala de grises para eliminar ruido de color
            img_gray = _PIL_ImageOps.grayscale(img)
            
            # Aumentar contraste significativamente
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img_gray)
            img_final = enhancer.enhance(2.0) # Duplicar contraste
            
            # Si el scale es alto, aplicamos un filtro de nitidez
            if scale >= 3.0:
                img_final = img_final.resize((img_final.width, img_final.height), _PIL_Image.Resampling.LANCZOS)
                enhancer_sharp = ImageEnhance.Sharpness(img_final)
                img_final = enhancer_sharp.enhance(1.5)

            # 3. Ejecutar OCR
            # Usamos PSM 3 (auto) o 6 (bloque) según el caso
            config_ocr = '--psm 3 --oem 3' if scale > 2.0 else '--psm 6 --oem 3'
            
            texto = _pytesseract.image_to_string(img_final, lang='spa+eng', config=config_ocr)
            
            # Si el texto es muy corto y scale era bajo, intentar re-procesar con más zoom (Recursión controlada)
            if len(texto.strip()) < 10 and scale < 4.0:
                return self._texto_via_ocr(page, scale=4.0)
                
            return texto
        except Exception:
            return ''

    # ─────────────────────────────────────────────────────────────────────────
    # EXTRACCIÓN DE DATOS
    # ─────────────────────────────────────────────────────────────────────────

    def _extraer_dni(self, texto):
        """Extrae DNI/CE con ventana de contexto + filtro inteligente de fechas."""
        if not texto:
            return None

        # DNIs de apoderados o RRHH que firman cartas (ej. 40535977) que no deben extraerse
        _DNI_BLACKLIST = {'40535977'}

        t = re.sub(r'\s+', ' ', re.sub(r'[^\x00-\x7F]+', ' ', texto)).upper()

        def _es_fecha(n):
            """True si el número de 8 dígitos parece una fecha DDMMAAAA o AAAAMMDD."""
            # DDMMAAAA: día 01-31, mes 01-12, año 19xx-20xx
            if re.match(r'^(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])(19|20)\d{2}$', n):
                return True
            # AAAAMMDD
            if re.match(r'^(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$', n):
                return True
            # Solo año al inicio (1900-2099)
            if n.startswith(('19', '20')):
                return True
            return False

        # ── Paso 1: patrones con etiqueta explícita (más confiables) ────────────
        patrones_etiqueta = [
            r'D\.?N\.?I\.?\s*[N°º#:]*\s*(\d{8})',
            r'DNI\s*/\s*\w+\s*[:\-]?\s*(\d{8})',
            r'N[°º]\s*DE?\s*DOC\.?\s*[:\-]?\s*(\d{8})',
            r'NRO\.?\s*DOC\.?\s*[:\-]?\s*(\d{8,12})',
            r'N[°º]\s*DOCUMENTO\s*[:\-]?\s*(\d{8})',
            r'DOCUMENTO\s*(?:DE\s*)?IDENTIDAD\s*[:\-]?\s*(\d{8,12})',
            r'DOC\.?\s*DE?\s*IDENT\.?\s*[:\-]?\s*(\d{8,12})',
            r'IDENTIFICACI[OÓ]N\s*[:\-]?\s*(\d{8,12})',
            r'C\.?E\.?\s*[:\-]?\s*(\d{9,12})',
            r'L\.?E\.?\s*[:\-]?\s*(\d{8})',
            r'D\s*N\s*I\s+(\d{8})',
            r'CUI\s*[:\-]?\s*(\d{8})',
        ]
        for pat in patrones_etiqueta:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                val = m.group(1)
                if len(val) >= 8 and not _es_fecha(val) and val not in _DNI_BLACKLIST:
                    return val

        # ── Paso 2: ventana de contexto ─────────────────────────────────────────
        # Buscar "DNI" / "DOCUMENTO" y extraer el número de 8 dígitos más cercano
        for kw in ['DNI', 'IDENTIDAD', 'DOCUMENTO', 'DOC.', 'N° DOC', 'NRO DOC']:
            idx = t.find(kw)
            while idx != -1:
                ventana = t[idx: idx + 80]
                nums = re.findall(r'\b(\d{8,12})\b', ventana)
                for n in nums:
                    if 8 <= len(n) <= 12 and not _es_fecha(n[:8]) and n not in _DNI_BLACKLIST:
                        return n
                idx = t.find(kw, idx + 1)

        # ── Paso 3: fallback — todos los números de 8 dígitos, filtrando fechas ─
        posibles = re.findall(r'(?<!\d)(\d{8})(?!\d)', t)
        for val in posibles:
            if not _es_fecha(val) and val not in _DNI_BLACKLIST:
                return val

        return None

    def _extraer_dni_campos_pdf(self, pdf_path):
        """
        Extrae DNI directamente de los campos de formulario de un PDF fillable.
        Los sistemas RRHH (DocuSign, Adobe Sign, Word→PDF) suelen generar PDFs con
        campos nombrados "DNI", "documento", "nro_doc", etc.
        """
        try:
            doc = fitz.open(str(pdf_path))
            candidatos = []
            for page in doc:
                campos = page.get_fields() or {}
                for nombre_campo, valor in campos.items():
                    if not isinstance(valor, (str, dict)):
                        continue
                    texto_val = valor if isinstance(valor, str) else str(valor.get('value', ''))
                    nombre_norm = re.sub(r'[\s_\-]', '', nombre_campo.lower())
                    # Si el campo se llama "dni", "documento", "nrodoc", etc.
                    es_campo_dni = any(k in nombre_norm for k in ['dni', 'doc', 'ident', 'cui', 'nro'])
                    nums = re.findall(r'\b(\d{8,12})\b', texto_val)
                    for n in nums:
                        score = 2 if es_campo_dni else 1
                        candidatos.append((score, n))

                # También buscar en texto plano con bloques (posición)
                bloques = page.get_text("blocks") or []
                for blk in bloques:
                    blk_txt = blk[4] if len(blk) > 4 else ''
                    nums_blk = re.findall(r'(?<!\d)(\d{8})(?!\d)', blk_txt)
                    for n in nums_blk:
                        if not re.match(r'^(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])(19|20)', n):
                            if not n.startswith(('19', '20')):
                                candidatos.append((1, n))
            doc.close()

            if not candidatos:
                return None
            # Ordenar por score descendente; tomar el primero
            candidatos.sort(key=lambda x: -x[0])
            return candidatos[0][1]
        except Exception:
            return None

    def _extraer_dni_carpeta(self, path):
        """Intenta extraer el DNI del nombre de la carpeta (ej: '12345678 - NOMBRE')."""
        folder_name = Path(path).parent.name if Path(path).is_file() else Path(path).name
        # Patrón 1: Empieza con 8 dígitos seguidos de guión o espacio
        m = re.match(r'^(\d{8})\s*[-–\s]', folder_name)
        if m:
            return m.group(1)
        # Patrón 2: Contiene 8 dígitos entre paréntesis o corchetes
        m = re.search(r'[\(\[\{](\d{8})[\)\]\}]', folder_name)
        if m:
            return m.group(1)
        return None

    def _extraer_nombre(self, texto, pdf_path=None):
        lines = texto.split('\n')
        for i, line in enumerate(lines):
            if 'FECHA' in line and ':' in line:
                if i > 0:
                    candidato = lines[i - 1].strip()
                    if candidato and candidato != 'FIRMA' and len(candidato) > 3:
                        return candidato
            if 'Aceptada el' in line:
                for j in range(i + 1, min(i + 5, len(lines))):
                    candidato = lines[j].strip()
                    if candidato and candidato != 'FIRMA' and 'FECHA' not in candidato and len(candidato) > 3:
                        return candidato

        # Fallback: extraer de nombre de carpeta padre
        if pdf_path:
            persona = self._extraer_persona_carpeta(pdf_path)
            if persona:
                return persona

        return 'NO IDENTIFICADO'

    def _extraer_fecha(self, texto):
        for patron in [
            r'Aceptada el\s*:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
            r'FECHA\s*:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
        ]:
            m = re.search(patron, texto)
            if m:
                return m.group(1)
        return 'NO IDENTIFICADA'

    def _extraer_persona_carpeta(self, pdf_path):
        """Extrae el nombre de la carpeta padre (patrón: '12345 - APELLIDOS NOMBRE')."""
        parent = Path(pdf_path).parent.name
        m = re.match(r'^\d+\s*[-–]\s*(.+)$', parent)
        if m:
            return m.group(1).strip()
        if len(parent) > 3 and not parent.lower().endswith('.pdf'):
            return parent
        return ''

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO 1: DRAWINGS (checkboxes gráficos)
    # ─────────────────────────────────────────────────────────────────────────

    def _detectar_por_drawings(self, page):
        drawings  = page.get_drawings()
        checkboxes, lineas = [], []

        for d in drawings:
            items = d.get('items', [])
            if not items:
                continue
            item_type = items[0][0]
            rect = d.get('rect')
            if rect is None:
                continue
            if item_type == 're':
                w, h = rect.width, rect.height
                if 4 < w < 20 and 4 < h < 20:
                    checkboxes.append({'rect': rect, 'y': rect.y0, 'x': rect.x0, 'marcado': False})
            elif item_type == 'l':
                lineas.append({'rect': rect, 'y': rect.y0})

        if not checkboxes:
            return None, 0, 'drawings_sin_checkboxes'

        for cb in checkboxes:
            cb_y, cb_rect = cb['y'], cb['rect']
            count = sum(
                1 for l in lineas
                if abs(l['y'] - cb_y) < 4
                and l['rect'].x0 >= cb_rect.x0 - 2
                and l['rect'].x1 <= cb_rect.x1 + 2
            )
            if count >= 2:
                cb['marcado'] = True

        marcados = [cb for cb in checkboxes if cb['marcado']]
        if not marcados:
            return None, 0, 'drawings_sin_marcas'

        confianza = 70 if len(marcados) > 1 else 95
        cb_marcado = marcados[0]

        # Intentar mapeo con múltiples conjuntos de rangos
        for rango_set in [self.CHECKBOX_Y_STD, self.CHECKBOX_Y_OLD, self.CHECKBOX_Y_WIDE]:
            opcion = self._mapear_y(cb_marcado['y'], rango_set)
            if opcion:
                return opcion, confianza, 'drawings'

        return None, 0, 'drawings_posicion_no_mapeada'

    def _mapear_y(self, y, rangos):
        for opcion, (y_min, y_max) in rangos.items():
            if y_min <= y <= y_max:
                return opcion
        return None

    # ── MÉTODO 1b: FORMATO ANTIGUO (X como texto + posición relativa a opciones numeradas) ─

    def _detectar_formato_antiguo(self, page):
        """
        Formato antiguo: las opciones están numeradas como '1.-', '2.-', '3.-'.
        El colaborador escribe 'X' como texto a la izquierda de la opción elegida.
        Detecta qué opción fue marcada por proximidad Y entre el 'X' y la etiqueta.
        """
        td = page.get_text('dict')
        opts = {}   # {'1': y, '2': y, '3': y, '1A': y, '1B': y}
        xs   = []   # [(x, y)] de cada 'X' suelto

        for block in td.get('blocks', []):
            if block.get('type') != 0:
                continue
            for line in block.get('lines', []):
                text = ''.join(s.get('text', '') for s in line.get('spans', [])).strip()
                y    = line['bbox'][1]
                x    = line['bbox'][0]
                tlow = text.lower()

                if re.match(r'^1[\.\-]', text):
                    opts['1'] = y
                elif re.match(r'^2[\.\-]', text):
                    opts['2'] = y
                elif re.match(r'^3[\.\-]', text):
                    opts['3'] = y
                elif re.search(r'no\s+he\s+percibido', tlow):
                    opts['1B'] = y
                elif re.search(r's[íi]\s+he\s+percibido', tlow):
                    opts['1A'] = y

                # X suelto en margen izquierdo (x < 200, texto corto)
                if text in ('X', 'x') and x < 200:
                    xs.append((x, y))

        if not xs or not opts:
            return None, 0, 'fmt_antiguo_sin_datos'

        for x_pos, y_pos in xs:
            best_opt, best_dist = None, float('inf')
            for opt, opt_y in opts.items():
                dist = abs(y_pos - opt_y)
                if dist < best_dist:
                    best_dist = dist
                    best_opt  = opt

            if best_dist > 35:
                continue  # demasiado lejos, no confiable

            if best_opt == '1':
                # Buscar sub-opción: otro X cerca de 1A o 1B
                # Verificar AMBAS opciones
                tiene_1A = False
                tiene_1B = False
                for x2, y2 in xs:
                    if (x_pos, y_pos) == (x2, y2):
                        continue
                    if '1A' in opts and abs(y2 - opts['1A']) <= 25:
                        tiene_1A = True
                    if '1B' in opts and abs(y2 - opts['1B']) <= 25:
                        tiene_1B = True

                if tiene_1A and not tiene_1B:
                    return '1A', 92, 'fmt_antiguo'
                elif tiene_1B and not tiene_1A:
                    return '1B', 92, 'fmt_antiguo'
                elif tiene_1A and tiene_1B:
                    return '1A', 80, 'fmt_antiguo_ambiguo'
                return '1B', 65, 'fmt_antiguo_sin_sub'
            elif best_opt == '1A':
                return '1A', 92, 'fmt_antiguo'
            elif best_opt == '1B':
                return '1B', 92, 'fmt_antiguo'
            elif best_opt == '2':
                return '2', 92, 'fmt_antiguo'
            elif best_opt == '3':
                return '3', 92, 'fmt_antiguo'

        return None, 0, 'fmt_antiguo_x_no_mapeado'

    # ── MÉTODO 1c: WIDGETS DE FORMULARIO PDF ─────────────────────────────────

    def _detectar_por_widgets(self, page):
        """
        Detecta checkboxes marcados en formularios PDF (widgets).
        Los PDFs con form fields tienen widgets con valor 'Yes'/'On' cuando están marcados.
        """
        try:
            widgets = list(page.widgets())
        except Exception:
            return None, 0, 'widgets_error'

        if not widgets:
            return None, 0, 'widgets_ninguno'

        marcados = []
        for w in widgets:
            if w.field_type_string not in ('CheckBox', 'RadioButton', 'Button'):
                continue
            val = (w.field_value or '').strip().lower()
            if val in ('yes', 'on', 'true', '1', 'x'):
                marcados.append({'y': w.rect.y0, 'x': w.rect.x0, 'nombre': w.field_name or ''})

        if not marcados:
            return None, 0, 'widgets_sin_marcados'

        # Si el nombre del campo contiene la categoría directamente
        # Verificar TODAS las opciones primero
        tiene_opcion1 = False
        tiene_opcion2 = False
        tiene_opcion3 = False
        tiene_no_percibido = False
        tiene_si_percibido = False

        for m in marcados:
            fn = (m['nombre'] or '').lower().replace(' ', '')
            if 'opcion1' in fn or 'opcion_1' in fn or 'alternativa_1' in fn or 'alt1' in fn:
                tiene_opcion1 = True
            if 'opcion2' in fn or 'opcion_2' in fn or 'alternativa_2' in fn or 'alt2' in fn:
                tiene_opcion2 = True
            if 'opcion3' in fn or 'opcion_3' in fn or 'alternativa_3' in fn or 'alt3' in fn:
                tiene_opcion3 = True
            if 'nohepercibido' in fn or 'nopercib' in fn:
                tiene_no_percibido = True
            if 'sihepercibido' in fn or 'sipercib' in fn:
                tiene_si_percibido = True

        # Priorizar opciones 2 y 3 primero
        if tiene_opcion3:
            return '3', 75, 'widgets'
        if tiene_opcion2:
            return '2', 75, 'widgets'

        # Para opción 1, verificar sub-opciones
        if tiene_si_percibido and not tiene_no_percibido:
            return '1A', 80, 'widgets'
        if tiene_no_percibido and not tiene_si_percibido:
            return '1B', 80, 'widgets'
        if tiene_si_percibido and tiene_no_percibido:
            return '1A', 70, 'widgets_ambiguo'
        if tiene_opcion1:
            return '1B', 65, 'widgets_sin_sub'

        # Mapear por posición Y (igual que drawings)
        for m in marcados:
            for rango_set in [self.CHECKBOX_Y_STD, self.CHECKBOX_Y_OLD, self.CHECKBOX_Y_WIDE]:
                opcion = self._mapear_y(m['y'], rango_set)
                if opcion:
                    return self._resolver_categoria(opcion, '', page) or ('1B' if opcion == 'opcion1' else None), 75, 'widgets_y'

        return None, 0, 'widgets_sin_mapeo'

    def _resolver_categoria(self, opcion, texto, page):
        if opcion == 'opcion2':
            return '2'
        elif opcion == 'opcion3':
            return '3'
        elif opcion == 'opcion1':
            sub = self._resolver_sub_opcion1(texto)
            if sub:
                return sub
            sub = self._resolver_sub_opcion1_spans(page)
            return sub or '1B'
        return None

    def _es_texto_no_percibido(self, texto):
        t = (texto or '').lower()
        return bool(
            re.search(r'\bno\s+he\s+percib\w*', t)
            or re.search(r'\bno\s+percib\w*', t)
        )

    def _es_texto_si_percibido(self, texto):
        t = (texto or '').lower()
        return bool(
            re.search(r'\bs[íi]\s+he\s+percib\w*', t)
            or re.search(r'\bsi\s+percib\w*', t)
        )

    def _resolver_sub_opcion1(self, texto):
        """Resuelve sub-opción verificando AMBAS opciones y comparando."""
        tiene_no = False
        tiene_si = False
        for line in texto.split('\n'):
            stripped = line.strip()
            lower = stripped.lower()
            # Verificar si esta línea tiene marca al inicio
            tiene_marca = (stripped.startswith(('-X', '- X', '[X]', '(X)', 'X ')) or
                          re.match(r'^[hHbB][&\$][Xx]\]', stripped) or
                          re.match(r'^[Ee][Xx]\]', stripped))
            if tiene_marca:
                if self._es_texto_no_percibido(lower):
                    tiene_no = True
                elif self._es_texto_si_percibido(lower):
                    tiene_si = True

        if tiene_si and not tiene_no:
            return '1A'
        elif tiene_no and not tiene_si:
            return '1B'
        elif tiene_si and tiene_no:
            return '1A'  # Ambiguo, preferir 1A
        return None

    def _resolver_sub_opcion1_spans(self, page):
        """Resuelve sub-opción desde spans verificando AMBAS opciones."""
        tiene_no = False
        tiene_si = False
        td = page.get_text('dict')
        for block in td.get('blocks', []):
            if block.get('type') != 0:
                continue
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    text = span.get('text', '').strip()
                    font = span.get('font', '')
                    bbox = span.get('bbox', (0, 0, 0, 0))
                    if text == 'X' and 'Bold' in font and 195 <= bbox[1] <= 280:
                        for span2 in line.get('spans', []):
                            t2 = span2.get('text', '').lower()
                            if self._es_texto_no_percibido(t2):
                                tiene_no = True
                            elif self._es_texto_si_percibido(t2):
                                tiene_si = True

        if tiene_si and not tiene_no:
            return '1A'
        elif tiene_no and not tiene_si:
            return '1B'
        elif tiene_si and tiene_no:
            return '1A'
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO 2: TEXTO "-X" (funciona con OCR y formato nativo)
    # ─────────────────────────────────────────────────────────────────────────

    def _detectar_por_texto(self, texto):
        """Detecta categoría por marcas -X en texto. Verifica AMBAS sub-opciones."""
        # Limpiar texto OCR típico (reemplazar variantes comunes)
        texto_limpio = texto.replace('[X]', '-X').replace('(X)', '-X')

        tiene_no = False
        tiene_si = False

        for line in texto_limpio.split('\n'):
            stripped = line.strip()
            lower    = stripped.lower()
            if self._linea_marcada(stripped) or stripped.startswith(('X ', '-X', '- X')):
                if self._es_texto_no_percibido(lower):
                    tiene_no = True
                elif self._es_texto_si_percibido(lower):
                    tiene_si = True

        if tiene_si and not tiene_no:
            return '1A', 90, 'texto_-X'
        elif tiene_no and not tiene_si:
            return '1B', 90, 'texto_-X'
        elif tiene_si and tiene_no:
            return '1A', 80, 'texto_-X_ambiguo'
        return None, 0, 'texto_sin_patron'

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO 3: SPANS BOLD (solo PDFs nativos)
    # ─────────────────────────────────────────────────────────────────────────

    def _detectar_por_spans(self, page):
        """Detecta categoría por spans Bold. Verifica AMBAS sub-opciones."""
        td = page.get_text('dict')
        bold_x_positions = []

        for block in td.get('blocks', []):
            if block.get('type') != 0:
                continue
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    text = span.get('text', '').strip()
                    font = span.get('font', '')
                    bbox = span.get('bbox', (0, 0, 0, 0))
                    if text == 'X' and 'Bold' in font:
                        bold_x_positions.append({'y': bbox[1], 'x': bbox[0]})

        if not bold_x_positions:
            return None, 0, 'spans_sin_bold_x'

        tiene_no = False
        tiene_si = False

        for pos in bold_x_positions:
            y = pos['y']
            if 195 <= y <= 280:  # Rango ampliado para sub-opciones
                for block in td.get('blocks', []):
                    if block.get('type') != 0:
                        continue
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            bbox = span.get('bbox', (0, 0, 0, 0))
                            if abs(bbox[1] - y) < 5 and span['text'].strip() != 'X':
                                t = span['text'].lower()
                                if self._es_texto_no_percibido(t):
                                    tiene_no = True
                                elif self._es_texto_si_percibido(t):
                                    tiene_si = True

        if tiene_si and not tiene_no:
            return '1A', 85, 'spans_bold'
        elif tiene_no and not tiene_si:
            return '1B', 85, 'spans_bold'
        elif tiene_si and tiene_no:
            return '1A', 75, 'spans_bold_ambiguo'

        return None, 0, 'spans_no_mapeado'

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODO 4: PALABRAS CLAVE ROBUSTAS (fallback máximo — OCR + formato antiguo)
    # ─────────────────────────────────────────────────────────────────────────

    def _detectar_por_keywords(self, texto):
        """
        Análisis por contexto de palabras clave cerca de marcas de selección.
        Tolerante a variantes de OCR, formato antiguo, OCR con errores.
        """
        # MÉTODO DIRECTO: Buscar patrón [checkbox marcado] + texto de opción
        # Esto detecta: h&X] No he percibido, [X] No he percibido, etc.
        patrones_checkbox_marcado = [
            r'[hHbB][&\$][Xx]\]',  # h&X], b$X]
            r'\[X\]',              # [X]
            r'\(X\)',              # (X)
            r'[Ee][Xx]\]',         # eX]
            r'X\s*\]',             # X ]
        ]

        texto_lower = texto.lower()

        # Buscar TODAS las marcas y sus contextos
        detecciones = []
        for patron in patrones_checkbox_marcado:
            matches = list(re.finditer(patron, texto, re.IGNORECASE))
            for match in matches:
                pos = match.end()
                contexto = texto_lower[pos:pos+150]

                if self._es_texto_no_percibido(contexto):
                    detecciones.append(('1B', pos, 'checkbox_directo'))
                elif self._es_texto_si_percibido(contexto):
                    detecciones.append(('1A', pos, 'checkbox_directo'))
                elif 'empleador principal' in contexto and 'no es' not in contexto:
                    return '2', 85, 'checkbox_directo'
                elif 'no es mi empleador' in contexto or 'no me efect' in contexto:
                    return '3', 85, 'checkbox_directo'

        # Si encontramos detecciones de 1A y/o 1B
        tiene_1A = any(d[0] == '1A' for d in detecciones)
        tiene_1B = any(d[0] == '1B' for d in detecciones)

        if tiene_1A and not tiene_1B:
            return '1A', 85, 'checkbox_directo'
        elif tiene_1B and not tiene_1A:
            return '1B', 85, 'checkbox_directo'
        elif tiene_1A and tiene_1B:
            # Ambos detectados - preferir 1A (la marca del "si he percibido" probablemente es más reciente)
            return '1A', 75, 'checkbox_directo_ambiguo'

        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            if not self._linea_marcada(linea):
                continue
            # Texto de contexto: la línea marcada + las 3 siguientes
            contexto = ' '.join(lineas[i:min(i+4, len(lineas))]).lower()
            contexto_norm = self._normalizar(contexto)

            if 'UNICO EMPLEADOR' in contexto_norm or 'UNICA EMPLEADORA' in contexto_norm:
                # Buscar sub-opción verificando AMBAS (hasta 10 líneas adelante)
                sub_lineas = lineas[i:min(i+10, len(lineas))]
                tiene_no = False
                tiene_si = False
                for sub_linea in sub_lineas:
                    sub_lower = sub_linea.lower()
                    sub_stripped = sub_linea.strip()
                    # Verificar si esta línea específica tiene marca Y contiene la frase
                    if self._linea_marcada(sub_linea) or sub_stripped.startswith(('[X]', '(X)', '-X', 'X ')):
                        if self._es_texto_no_percibido(sub_lower):
                            tiene_no = True
                        if self._es_texto_si_percibido(sub_lower):
                            tiene_si = True

                if tiene_si and not tiene_no:
                    return '1A', 80, 'keywords'
                elif tiene_no and not tiene_si:
                    return '1B', 80, 'keywords'
                elif tiene_si and tiene_no:
                    return '1A', 70, 'keywords_ambiguo'
                return '1B', 55, 'keywords_sin_sub'

            if re.search(r'EMPLEADOR PRINCIPAL', contexto_norm):
                if re.search(r'NO ES|NO ES SU|NO SOIS', contexto_norm):
                    return '3', 75, 'keywords'
                return '2', 75, 'keywords'

            if re.search(r'NO ES.*EMPLEADOR|NO ES.*EMPLEA', contexto_norm):
                return '3', 70, 'keywords'

        # MÉTODO ALTERNATIVO: Buscar estructura del documento y marcas cerca de opciones
        # Esto funciona mejor con OCR que distorsiona las marcas
        texto_norm = self._normalizar(texto)

        # Detectar marcas cerca de las opciones por proximidad en el texto
        # Buscar patrones de la estructura del documento
        opciones = {
            '1': self._buscar_patron_opcion(texto, texto_norm, [
                r'1[\.\-\~].*UNICO EMPLEADOR',
                r'UNICO EMPLEADOR',
                r'1[\.\-\~].*USIL.*ES MI UNICO',
            ]),
            '2': self._buscar_patron_opcion(texto, texto_norm, [
                r'2[\.\-\~].*EMPLEADOR PRINCIPAL',
                r'USIL ES MI EMPLEADOR PRINCIPAL',
                r'2[\.\-\~].*PERCIBIR.*ADICIONAL',
            ]),
            '3': self._buscar_patron_opcion(texto, texto_norm, [
                r'3[\.\-\~].*NO ES MI EMPLEADOR',
                r'USIL NO ES MI EMPLEADOR',
                r'3[\.\-\~].*NO ME EFECTU',
            ]),
        }

        # La opción marcada tiene una marca visual (X, ✓, cuadro, etc.) ANTES de su texto
        for opcion_num, (encontrada, posicion) in opciones.items():
            if encontrada:
                # Verificar si hay una marca cerca antes de esta opción
                if self._tiene_marca_antes(texto, posicion):
                    if opcion_num == '1':
                        # Sub-opción 1A vs 1B - verificar AMBAS y comparar
                        sub_texto = texto[posicion:posicion+600]
                        tiene_no = self._tiene_marca_sub_opcion(sub_texto, 'no he percib')
                        tiene_si = self._tiene_marca_sub_opcion(sub_texto, 'si he percib')

                        if tiene_si and not tiene_no:
                            return '1A', 85, 'keywords_struct'
                        elif tiene_no and not tiene_si:
                            return '1B', 85, 'keywords_struct'
                        elif tiene_si and tiene_no:
                            # Ambos marcados - buscar cuál tiene marca más clara
                            return '1A', 70, 'keywords_struct_ambiguo'
                        else:
                            return '1B', 60, 'keywords_struct_sin_sub'
                    elif opcion_num == '2':
                        return '2', 80, 'keywords_struct'
                    elif opcion_num == '3':
                        return '3', 80, 'keywords_struct'

        return None, 0, 'keywords_sin_patron'

    def _buscar_patron_opcion(self, texto, texto_norm, patrones):
        """Busca patrones y devuelve (encontrado, posicion)."""
        for patron in patrones:
            m = re.search(patron, texto_norm)
            if m:
                return True, m.start()
        return False, -1

    def _tiene_marca_antes(self, texto, posicion, rango=150):
        """Verifica si hay una marca visual antes de una posición."""
        inicio = max(0, posicion - rango)
        fragmento = texto[inicio:posicion]

        # Patrones de marcas comunes (incluyendo errores de OCR)
        marcas = [
            r'[\[\(]?\s*[Xx✓✗☑☒]\s*[\]\)]?',  # [X], (X), X, ✓
            r'-\s*[Xx]',  # -X
            r'[Ss][<\[\(][Kk\]]',  # S<], S[K] (errores típicos de OCR para checkbox)
            r'[Ss][Kk]\s*\d',  # SK 1 (error OCR)
            r'\[\s*[\/\|\\]\s*\]',  # [/], [|], [\]
            r'[hHbB][&\$][Xx]\]',  # h&X], b&X] (error OCR común)
            r'\[[Xx&]\]',  # [X], [&]
            r'[Ee][Xx]\]',  # eX] (error OCR)
            r'\bX\s*\]',  # X ] suelto
        ]

        for marca in marcas:
            if re.search(marca, fragmento):
                return True
        return False

    def _tiene_marca_sub_opcion(self, texto, frase_clave):
        """
        Verifica si una sub-opción está marcada.
        Busca marcas EN LA MISMA LÍNEA que la frase, no solo 'antes en el texto'.
        """
        texto_lower = texto.lower()
        frase_lower = frase_clave.lower()

        # Dividir en líneas y buscar la línea que contiene la frase
        for linea in texto.split('\n'):
            linea_lower = linea.lower()
            if frase_lower in linea_lower:
                # Verificar si esta línea tiene una marca al inicio
                if self._linea_marcada(linea):
                    return True
                # También verificar si hay marca justo antes de la frase en esta línea
                pos = linea_lower.find(frase_lower)
                fragmento_linea = linea[:pos]
                if self._fragmento_tiene_marca(fragmento_linea):
                    return True
        return False

    def _fragmento_tiene_marca(self, fragmento):
        """Verifica si un fragmento corto contiene una marca de checkbox."""
        marcas = [
            r'[Xx]',
            r'[✓✗☑☒]',
            r'[hHbB][&\$][Xx]\]',
            r'[Ee][Xx]\]',
            r'\[[Xx&\/\|\\]\]',
            r'\([Xx]\)',
            r'[Ss][<\[\(][Kk\]]',
        ]
        for marca in marcas:
            if re.search(marca, fragmento):
                return True
        return False

    def _linea_marcada(self, linea):
        """Detecta si una línea tiene una marca de selección (X, checkmark, etc.)."""
        stripped = linea.strip()
        # Patrones originales + errores comunes de OCR
        patrones = [
            r'^[-–•]\s*[Xx]\b',        # -X, –X, •X
            r'^\[X\]',                  # [X]
            r'^\(X\)',                  # (X)
            r'^X\s+[A-ZÁÉÍÓÚÑ]',        # X seguido de mayúsculas
            r'^[Ss][<\[\(][Kk\]]',      # S<], S[K] (error OCR)
            r'^[Ss][Kk]\s*\d',          # SK 1 (error OCR para checkbox)
            r'^\[\s*[\/\|\\]\s*\]',     # [/], [|]
            r'^[✓✗☑☒]\s*',             # Checkmarks unicode
            r'^[hHbB][&\$][Xx]\]',      # h&X], b$X] (error OCR común)
            r'^[Ee][Xx]\]',             # eX] (error OCR)
        ]
        for patron in patrones:
            if re.match(patron, stripped, re.IGNORECASE):
                return True
        return False

    def _normalizar(self, texto):
        """Remueve tildes y pasa a mayúsculas para comparación robusta."""
        return (texto
                .upper()
                .replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
                .replace('Ó', 'O').replace('Ú', 'U').replace('Ñ', 'N'))

    def _es_declaracion_quinta(self, texto_norm):
        """True si el texto contiene cualquier indicador de declaración de quinta."""
        return any(kw in texto_norm for kw in _QUINTA_KWORDS)

    # ─────────────────────────────────────────────────────────────────────────
    # LOTE / CARPETA
    # ─────────────────────────────────────────────────────────────────────────

    def analizar_lote(self, rutas, max_workers=8):
        """Analiza una lista de rutas (archivos o carpetas) en paralelo."""
        archivos = []
        for ruta in rutas:
            ruta = Path(ruta)
            if ruta.is_dir():
                # Buscar todos los formatos soportados
                for ext in _EXTENSIONES_SOPORTADAS:
                    archivos.extend(sorted(ruta.glob(f'*{ext}')))
                    archivos.extend(sorted(ruta.glob(f'*{ext.upper()}')))
            elif ruta.is_file() and ruta.suffix.lower() in _EXTENSIONES_SOPORTADAS:
                archivos.append(ruta)
            else:
                pass  # ignorar silenciosamente

        # Eliminar duplicados manteniendo orden
        archivos = list(dict.fromkeys(archivos))

        if not archivos:
            return []

        return self._procesar_paralelo(archivos, max_workers)

    def analizar_carpeta_recursivo(self, carpeta, max_workers=8):
        """Escanea recursivamente una carpeta y procesa todos los archivos soportados."""
        carpeta = Path(carpeta)
        if not carpeta.is_dir():
            return [self._error(f'Carpeta no encontrada: {carpeta}', str(carpeta))]

        archivos = []
        # Buscar todos los formatos soportados recursivamente
        for ext in _EXTENSIONES_SOPORTADAS:
            archivos.extend(sorted(carpeta.rglob(f'*{ext}')))
            archivos.extend(sorted(carpeta.rglob(f'*{ext.upper()}')))

        # Eliminar duplicados manteniendo orden
        archivos = list(dict.fromkeys(archivos))

        if not archivos:
            return []
        return self._procesar_paralelo(archivos, max_workers)

    def _procesar_paralelo(self, archivos, max_workers=8):
        """Procesa una lista de archivos en paralelo con ThreadPoolExecutor."""
        n = len(archivos)
        if n == 0:
            return []
        workers = min(max_workers, n, os.cpu_count() or 4)
        resultados = [None] * n

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {
                executor.submit(self.analizar_archivo, archivo): i
                for i, archivo in enumerate(archivos)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    resultados[idx] = future.result()
                except Exception as e:
                    resultados[idx] = self._error(str(e), str(archivos[idx]))

        return resultados

    def _ocr_documento_dni(self, archivo_path):
        """
        Extrae texto OCR de un archivo DNI/CUI (PDF o imagen).
        Usa caché por hash — archivos ya procesados responden en <1ms.
        Prueba rotaciones con salida temprana al encontrar datos suficientes.
        """
        archivo_path = Path(archivo_path)

        # ── Caché: si ya procesamos este archivo exacto, respuesta instantánea ──
        cached = _cache_get(archivo_path)
        if cached is not None:
            return cached

        # Config Tesseract optimizada para DNIs:
        # PSM 4 = columna única (layout de carné), OEM 1 = solo LSTM (más rápido)
        _TESS_DNI = '--psm 4 --oem 1'

        def _campos_en(texto):
            d = _extraer_datos_documento_dni(texto)
            return sum(1 for k, v in d.items() if v and k != 'nombre_completo'), d

        if archivo_path.suffix.lower() == '.pdf':
            try:
                doc = fitz.open(str(archivo_path))
                page = doc[0]

                # Texto nativo primero — cero OCR
                texto_nativo = page.get_text().strip()
                if len(re.sub(r'\s', '', texto_nativo)) > 30:
                    campos, datos = _campos_en(texto_nativo)
                    if campos >= 2:
                        doc.close()
                        datos['texto_crudo'] = texto_nativo
                        _cache_set(archivo_path, datos)
                        return datos

                if not _inicializar_ocr():
                    doc.close()
                    return None

                # ── Estrategia dual para PDFs escaneados ─────────────────────
                # 1) Renderizar la página completa (funciona bien para DNIs electrónicos blancos)
                mat = fitz.Matrix(4.0, 4.0)
                pix = page.get_pixmap(matrix=mat)
                img_page = _PIL_Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                img_page = _mejorar_contraste_dni(img_page)

                # 2) Extraer imágenes embebidas del PDF (funciona mejor para DNIs
                #    azules/fotos donde la imagen original es de mayor calidad que
                #    el render de la página completa)
                imagenes_embebidas = []
                try:
                    import io as _io
                    for img_info in page.get_images(full=True):
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue
                        image_bytes = base_image.get("image")
                        w = base_image.get("width", 0)
                        h = base_image.get("height", 0)
                        # Solo considerar imágenes de tamaño razonable (>200px en ambos lados)
                        if w >= 200 and h >= 200 and image_bytes:
                            pil_emb = _PIL_Image.open(_io.BytesIO(image_bytes))
                            # Escalar si es pequeña para mejorar OCR
                            lado_menor = min(pil_emb.width, pil_emb.height)
                            if lado_menor < 1200:
                                factor = max(2.0, 1200 / lado_menor)
                                new_size = (int(pil_emb.width * factor), int(pil_emb.height * factor))
                                pil_emb = pil_emb.resize(new_size, _PIL_Image.Resampling.LANCZOS)
                            imagenes_embebidas.append(pil_emb)
                except Exception:
                    pass

                doc.close()

                # Primero intentar con render de página
                img_base = img_page
            except Exception:
                return None
        elif archivo_path.suffix.lower() in _EXTENSIONES_IMAGEN:
            if not _inicializar_ocr():
                return None
            imagenes_embebidas = []
            try:
                img_base = _PIL_Image.open(str(archivo_path))
                img_base = _mejorar_imagen_dni(img_base)
            except Exception:
                return None
        else:
            return None

        mejor_datos = None
        mejor_campos = -1
        for angulo in [0, 90, 270, 180]:
            img_rot = img_base.rotate(angulo, expand=True) if angulo != 0 else img_base
            try:
                texto = _pytesseract.image_to_string(
                    img_rot, lang='spa+eng', config=_TESS_DNI
                )
                if len(re.sub(r'\s', '', texto)) < 20:
                    continue
                campos, datos = _campos_en(texto)
                datos['texto_crudo'] = texto
                if campos > mejor_campos:
                    mejor_campos = campos
                    mejor_datos = datos
                if campos >= 3:
                    break
            except Exception:
                continue

        # ── Fallback: imágenes embebidas del PDF ─────────────────────────
        # Si la renderización de página no produjo buenos resultados (< 2 campos),
        # o si no se pudo encontrar el número de DNI,
        # intentar con las imágenes embebidas directamente — esto funciona mucho
        # mejor para DNIs azules/fotos donde la imagen original tiene mayor calidad
        if (mejor_campos < 2 or not mejor_datos.get('numero')) and imagenes_embebidas:
            for emb_img in imagenes_embebidas:
                if mejor_campos >= 3 and mejor_datos.get('numero'):
                    break
                # Probar con color original y con escala de grises
                variantes = [emb_img]
                try:
                    if emb_img.mode in ('RGBA', 'P', 'LA'):
                        emb_rgb = emb_img.convert('RGB')
                    elif emb_img.mode != 'RGB':
                        emb_rgb = emb_img.convert('RGB')
                    else:
                        emb_rgb = emb_img
                    emb_gray = _PIL_ImageOps.grayscale(emb_rgb)
                    emb_gray = _PIL_ImageOps.autocontrast(emb_gray, cutoff=1)
                    variantes.append(emb_gray)
                except Exception:
                    pass

                for variante in variantes:
                    for psm_cfg in ['--psm 3 --oem 3', '--psm 4 --oem 3', '--psm 6 --oem 3']:
                        try:
                            texto = _pytesseract.image_to_string(
                                variante, lang='spa+eng', config=psm_cfg
                            )
                            if len(re.sub(r'\s', '', texto)) < 20:
                                continue
                            campos, datos = _campos_en(texto)
                            datos['texto_crudo'] = texto
                            if campos > mejor_campos or (campos == mejor_campos and datos.get('numero') and not mejor_datos.get('numero')):
                                mejor_campos = campos
                                mejor_datos = datos
                            if campos >= 3 and mejor_datos.get('numero'):
                                break
                        except Exception:
                            continue
                    if mejor_campos >= 3 and mejor_datos.get('numero'):
                        break

        _cache_set(archivo_path, mejor_datos)
        return mejor_datos

    def identificar_dni_persona(self, carpeta_path, nombre_persona=None):
        """
        Busca archivos DNI/CUI dentro de carpeta_path usando 2 estrategias:
          1) Archivos con 'dni' o 'cui' en el nombre
          2) Archivos cuyo nombre coincide con el nombre de la persona
             (ej: carpeta 'ROSAS TORRES NAYSHA LIZ' → archivo 'ROSAS TORRES NAYSHA LIZ.pdf')

        Retorna dict con: apellidos, prenombres, nombre_completo, numero, sexo,
                          archivo (nombre del archivo ganador), puntaje.
        Si no hay match >= 0.25 devuelve None.
        """
        carpeta = Path(carpeta_path)
        if not carpeta.is_dir():
            return None

        # Estrategia 1: archivos con 'dni' o 'cui' en el nombre (comportamiento original)
        archivos_dni = sorted([
            f for f in carpeta.rglob('*')
            if f.is_file()
            and f.suffix.lower() in _EXTENSIONES_SOPORTADAS
            and ('dni' in f.name.lower() or 'cui' in f.name.lower())
        ])

        # Estrategia 2: archivos cuyo nombre coincide con el nombre de la persona
        # Esto captura archivos como "Jimena Abigail Aguilar Grimaldo.pdf"
        # o "ROSAS TORRES NAYSHA LIZ.pdf" que son DNIs sin la etiqueta "DNI" en el nombre
        archivos_nombre = []
        # Palabras que indican que el archivo es un DOCUMENTO (no un DNI)
        # aunque contenga el nombre de la persona
        _EXCLUIR_DOC = {
            'CONTRATO', 'CARTA', 'OFERTA', 'CONSTANCIA', 'CERTIFICADO', 'CERT',
            'BOLETA', 'RECIBO', 'PLANILLA', 'MEMORAN', 'DIPLOMA', 'TITULO',
            'BACHILLER', 'CV', 'CURRICULUM', 'REPORTE', 'REPORTECV',
            'LIQUIDACION', 'EPS', 'VIDALEY', 'VIDA', 'SEGURO', 'TRABAJO',
            'FICHA', 'FICHAEPS', 'CUENTAS', 'DECLARACION', 'SISTEMA',
            'PENSIONES', 'FOTO', 'FOTOGRAFIA', 'IMG', 'FIRMADO', 'FIRMADA',
        }
        if nombre_persona:
            limpiar = lambda s: re.sub(r'[^A-ZÁÉÍÓÚÑ\s]', '', s.upper())
            palabras_persona = set(limpiar(nombre_persona).split()) - {'DE', 'LA', 'LOS', 'DEL'}
            if len(palabras_persona) >= 2:
                for f in carpeta.rglob('*'):
                    if not f.is_file() or f.suffix.lower() not in _EXTENSIONES_SOPORTADAS:
                        continue
                    if f in archivos_dni:  # ya incluido
                        continue
                    # Limpiar nombre de archivo (sin extensión)
                    nombre_archivo = limpiar(f.stem)
                    palabras_archivo = set(nombre_archivo.split()) - {'DE', 'LA', 'LOS', 'DEL', 'PDF', 'JPG', 'PNG'}
                    if not palabras_archivo:
                        continue
                    # Excluir archivos que son claramente documentos (no DNIs)
                    if palabras_archivo & _EXCLUIR_DOC:
                        continue
                    # Doble filtro para evitar falsos positivos:
                    # 1) Al menos 60% de las palabras de la persona están en el archivo
                    coincidencias = palabras_persona & palabras_archivo
                    ratio_persona = len(coincidencias) / len(palabras_persona)
                    # 2) Las palabras de persona representan al menos 50% del nombre del archivo
                    #    (evita que "41 CONTRATO ROSAS TORRES Naysha 3 marzo al 31 julio" pase)
                    ratio_archivo = len(coincidencias) / len(palabras_archivo) if palabras_archivo else 0
                    if ratio_persona >= 0.6 and ratio_archivo >= 0.5 and len(coincidencias) >= 2:
                        archivos_nombre.append(f)

        # Combinar: primero archivos por nombre (prioridad), luego los de etiqueta dni/cui
        # Los archivos con nombre de persona tienen más probabilidad de ser SU DNI
        # (vs. archivos "DNI CIPRIANO PORRAS..." que son de familiares)
        archivos_todos = archivos_nombre + archivos_dni

        if not archivos_todos:
            return None

        # Procesar DNI files en paralelo — cada archivo en su propio hilo
        # (Tesseract libera el GIL, por lo que threads reales se benefician)
        candidatos = []
        encontrado_solido = False

        # Marcar cuáles vinieron por coincidencia de nombre (bonus de confianza)
        archivos_nombre_set = set(archivos_nombre) if archivos_nombre else set()

        def _procesar_un_dni(archivo):
            try:
                datos = self._ocr_documento_dni(archivo)
                if not datos:
                    return None
                datos['archivo_dni'] = archivo.name
                # Score base por OCR/nombre de la carpeta
                score_base = _puntaje_match_dni(datos, nombre_persona) if nombre_persona else 0.5
                # Bonus si el nombre del archivo coincide con la persona
                # (ej: carpeta "ROSAS TORRES NAYSHA LIZ" + archivo "ROSAS TORRES NAYSHA LIZ.pdf")
                if archivo in archivos_nombre_set:
                    score_base = max(score_base, 0.70)  # mínimo 0.70 por coincidencia de nombre de archivo
                datos['puntaje'] = score_base
                return datos
            except Exception:
                return None

        workers = min(4, len(archivos_todos))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_procesar_un_dni, a): a for a in archivos_todos}
            for fut in as_completed(futures):
                datos = fut.result()
                if datos:
                    candidatos.append(datos)
                    if datos['puntaje'] >= 0.75:
                        encontrado_solido = True
                        # Cancelar futuros pendientes (no vale la pena seguir)
                        for f in futures:
                            f.cancel()
                        break

        if not candidatos:
            return None

        candidatos.sort(key=lambda d: d['puntaje'], reverse=True)
        mejor = candidatos[0]

        # Si no estructuró el número, pero sabemos que este es el documento correcto (por nombre)
        if not mejor.get('numero') and mejor.get('puntaje', 0) >= 0.5:
            texto_crudo = mejor.get('texto_crudo')
            if texto_crudo:
                mejor['numero'] = self._extraer_dni(texto_crudo)

        if mejor.get('numero') or mejor.get('nombre_completo'):
            return mejor
        return None

    def generar_resumen(self, resultados):
        total    = len(resultados)
        exitosos = [r for r in resultados if r['status'] == 'OK']
        errores  = [r for r in resultados if r['status'] == 'ERROR']
        warnings = [r for r in resultados if r['status'] == 'WARNING']
        conteo   = {}
        for r in exitosos:
            cat = r['categoria']
            conteo[cat] = conteo.get(cat, 0) + 1

        return {
            'total_procesados': total,
            'exitosos':         len(exitosos),
            'errores':          len(errores),
            'sin_clasificar':   len(warnings),
            'categorias':       conteo,
            'detalle_categorias': {
                cat: {'cantidad': conteo.get(cat, 0), 'info': info}
                for cat, info in CATEGORIAS.items()
            }
        }

    def _error(self, mensaje, archivo=''):
        return {
            'status': 'ERROR', 'archivo': str(archivo), 'nombre': '',
            'persona': '', 'categoria': None,
            'categoria_info': None, 'confianza': 0,
            'metodo': 'error', 'mensaje': mensaje
        }


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python clasificador_quinta.py <archivo | carpeta/>')
        print(f'Formatos soportados: {", ".join(_EXTENSIONES_SOPORTADAS)}')
        sys.exit(1)

    clf  = ClasificadorQuinta()
    ruta = Path(sys.argv[1])

    # Si es una carpeta, usar método recursivo; si son archivos, usar lote
    if ruta.is_dir():
        res = clf.analizar_carpeta_recursivo(ruta)
    else:
        rutas = [Path(a) for a in sys.argv[1:]]
        res = clf.analizar_lote(rutas)

    rsm = clf.generar_resumen(res)

    print('\n' + '=' * 65)
    print(' CLASIFICADOR DECLARACION JURADA DE QUINTA')
    print('=' * 65)
    for r in res:
        icon = {'OK': '+', 'ERROR': '!', 'WARNING': '?'}.get(r['status'], ' ')
        print(f'\n[{icon}] {r.get("archivo", "?")}')
        print(f'    Persona:   {r.get("persona") or r.get("nombre", "?")}')
        print(f'    Fecha:     {r.get("fecha", "?")}')
        if r['categoria']:
            print(f'    Categoria: {r["categoria"]} - {r["categoria_info"]["nombre"]}')
            print(f'    Confianza: {r["confianza"]}%  |  Metodo: {r["metodo"]}')
        else:
            print(f'    Estado:    {r["mensaje"]}')

    print('\n' + '-' * 65)
    print(f' RESUMEN: {rsm["exitosos"]}/{rsm["total_procesados"]} clasificados')
    for cat, det in rsm['detalle_categorias'].items():
        if det['cantidad'] > 0:
            print(f'   Cat {cat}: {det["cantidad"]}  — {det["info"]["nombre"]}')
    if rsm['errores'] > 0:
        print(f'   Errores: {rsm["errores"]}')
    if rsm['sin_clasificar'] > 0:
        print(f'   Sin clasificar: {rsm["sin_clasificar"]}')
    print('=' * 65)

import os
import re
import shutil
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None

class ProcesadorOfertas:
    """
    Motor de procesamiento de Cartas Oferta.
    Escanea carpetas de personas, identifica la carta oferta, 
    analiza términos económicos y las mueve a una carpeta destino.
    """
    
    KEYWORDS = {
        'Bono de transporte': [r'bono\s+de\s+transporte', r'bono\s+transporte'],
        'Prestación Alimentaria': [r'prestaci[oó]n\s+alimentaria', r'provisi[oó]n\s+alimentaria'],
        'Asignación de Movilidad': [r'asignaci[oó]n\s+de\s+movilidad', r'movilidad\s+local', r'gastos\s+de\s+movilidad']
    }

    def __init__(self, ruta_origen, ruta_destino):
        self.ruta_origen = Path(ruta_origen)
        self.ruta_destino = Path(ruta_destino)
        self._tesseract_ok = False
        self._init_tesseract()

    def _init_tesseract(self):
        """Configura Tesseract si está instalado en rutas comunes de Windows."""
        if not pytesseract:
            return
        rutas = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.path.expanduser(r'~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'),
            os.path.expanduser(r'~\AppData\Local\Tesseract-OCR\tesseract.exe'),
        ]
        for p in rutas:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break
        try:
            pytesseract.get_tesseract_version()
            self._tesseract_ok = True
        except Exception:
            self._tesseract_ok = False

    def _get_win_path(self, path: Path) -> str:
        """Devuelve ruta con prefijo largo en Windows para evitar WinError 3 por longitud."""
        p_str = str(path.absolute())
        if os.name == 'nt' and not p_str.startswith('\\\\?\\'):
            return f"\\\\?\\{p_str}"
        return p_str

    def _normalizar_texto(self, texto):
        return " ".join((texto or "").lower().split())

    def _ocr_imagen_pil(self, img):
        """Aplica OCR básico sobre una imagen PIL con preprocesado ligero."""
        if not (self._tesseract_ok and ImageOps):
            return ""
        try:
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            gray = ImageOps.grayscale(img)
            gray = ImageOps.autocontrast(gray, cutoff=1)
            txt = pytesseract.image_to_string(gray, lang='spa+eng', config='--psm 6 --oem 3')
            return txt or ""
        except Exception:
            return ""

    def _extraer_texto_ocr_pdf(self, file_path):
        if not self._tesseract_ok:
            return ""
        try:
            doc = fitz.open(self._get_win_path(Path(file_path)))
            partes = []
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                if not Image:
                    continue
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                txt = self._ocr_imagen_pil(img)
                if txt:
                    partes.append(txt)
            doc.close()
            return "\n".join(partes)
        except Exception:
            return ""

    def _extraer_texto_ocr_imagen(self, file_path):
        if not (self._tesseract_ok and Image):
            return ""
        try:
            img = Image.open(self._get_win_path(Path(file_path)))
            return self._ocr_imagen_pil(img)
        except Exception:
            return ""

    def es_carta_oferta(self, file_path):
        """Heurística para identificar si un archivo es una carta oferta."""
        name = file_path.name.lower()
        return 'carta' in name and 'oferta' in name

    def extraer_texto(self, file_path):
        """Extrae texto para triage; usa OCR si el texto nativo es insuficiente."""
        path = Path(file_path)
        ext = path.suffix.lower()
        try:
            texto = ""
            if ext == '.pdf':
                doc = fitz.open(self._get_win_path(path))
                for page in doc:
                    texto += page.get_text() or ""
                doc.close()
                if len(re.sub(r'\s+', '', texto)) < 60:
                    texto += "\n" + self._extraer_texto_ocr_pdf(path)
            elif ext in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}:
                texto = self._extraer_texto_ocr_imagen(path)
            return self._normalizar_texto(texto)
        except Exception as e:
            print(f"[ERROR] No se pudo leer {file_path}: {e}")
            return ""

    def triage_contenido(self, texto):
        """Identifica beneficios adicionales usando expresiones regulares."""
        encontrados = []
        for label, patterns in self.KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, texto):
                    encontrados.append(label)
                    break
        return encontrados if encontrados else ["Contrato Regular"]

    def ejecutar(self):
        """Ejecuta el proceso completo de escaneo y movimiento."""
        if not self.ruta_origen.exists():
            return {"status": "ERROR", "message": f"Ruta origen no existe: {self.ruta_origen}"}
        
        try:
            self.ruta_destino.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {"status": "ERROR", "message": f"No se pudo crear/acceder a la carpeta destino: {e}"}

        resultados = []
        
        # Escanear subcarpetas (Nivel 1: Nombres de Personas)
        for folder in self.ruta_origen.iterdir():
            if folder.is_dir():
                persona = folder.name
                carta_encontrada = False
                
                # Buscar en los archivos de la persona
                for file in folder.glob("*.pdf"):
                    if self.es_carta_oferta(file):
                        carta_encontrada = True
                        texto = self.extraer_texto(file)
                        hallazgos = self.triage_contenido(texto)
                        
                        # Nombre estandarizado para el destino
                        nombre_final = f"Carta Oferta - {persona}.pdf"
                        ruta_final = self.ruta_destino / nombre_final
                        
                        try:
                            # Se usa shutil.move para "mover" el archivo como solicitó el usuario
                            # Si ya existe, se sobrescribe (comportamiento de move en la misma unidad)
                            shutil.move(str(file), str(ruta_final))
                            
                            resultados.append({
                                'uuid': f"DOC-{os.urandom(2).hex().upper()}",
                                'persona': persona,
                                'archivo_origen': file.name,
                                'hallazgos': hallazgos,
                                'ruta_destino': str(self.ruta_destino),
                                'archivo_final': nombre_final,
                                'estado': 'MOVIDO_OK',
                                'timestamp': datetime.now().strftime("%H:%M:%S")
                            })
                        except Exception as e:
                            resultados.append({
                                'persona': persona,
                                'archivo_origen': file.name,
                                'estado': 'ERROR_MOVER',
                                'mensaje': str(e)
                            })
                        break # Solo procesamos una carta oferta por persona
                
                if not carta_encontrada:
                    # Opcional: registrar que no se encontró carta
                    pass
                    
        return {"status": "OK", "resultados": resultados}


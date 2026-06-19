import os
import re
import shutil
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from clasificador_quinta import ClasificadorQuinta
from procesador_ofertas import ProcesadorOfertas


def _cargar_overrides_categoria():
    """
    Carga overrides opcionales desde categoria_overrides.json.
    Estructura esperada:
      {
        "dni": {"72920386": "PRACT"},
        "persona": {"URIBE DEL AGUILA ANA LUCIA": "PRACT"}
      }
    """
    ruta = Path(__file__).with_name('categoria_overrides.json')
    if not ruta.exists():
        return {'dni': {}, 'persona': {}}
    try:
        data = json.loads(ruta.read_text(encoding='utf-8'))
        return {
            'dni': data.get('dni') or {},
            'persona': data.get('persona') or {}
        }
    except Exception:
        return {'dni': {}, 'persona': {}}


def _categoria_info_override(codigo):
    if codigo == 'PRACT':
        return {
            'codigo': 'PRACT',
            'nombre': 'Practicante (override)',
            'descripcion': 'Categoría asignada por configuración manual (override).',
            'color': '#607D8B'
        }
    return {
        'codigo': codigo,
        'nombre': f'Categoría {codigo} (override)',
        'descripcion': 'Categoría asignada por configuración manual (override).',
        'color': '#607D8B'
    }

# ─── Términos a detectar en la carta oferta ───────────────────────────────────
_TERMINOS_BENEFICIOS = [
    {
        'id':     'bono_transporte',
        'label':  'Bono de Transporte',
        'patron': r'bono\s+de\s+transporte',
    },
    {
        'id':     'prestacion_alimentaria',
        'label':  'Prestación Alimentaria',
        'patron': r'prestaci[oó]n\s+alimentaria',
    },
    {
        'id':     'asignacion_movilidad',
        'label':  'Asignación de Movilidad',
        'patron': r'asignaci[oó]n\s+de\s+movilidad',
    },
]

def _detectar_terminos_carta(texto):
    """Devuelve lista de labels de los términos encontrados en el texto."""
    if not texto:
        return []
    t = texto.lower()
    return [
        term['label']
        for term in _TERMINOS_BENEFICIOS
        if re.search(term['patron'], t)
    ]

class ProcesadorCombinado:
    """
    Combina el procesamiento de Cartas Oferta y DJ Quinta Categoría.
    Extrae el DNI, junta ambos documentos en una carpeta nueva por persona 
    y genera un reporte consolidado.
    """

    def __init__(self, ruta_origen, ruta_destino):
        self.ruta_origen = Path(ruta_origen)
        self.ruta_destino = Path(ruta_destino)
        self.clasificador_quinta = ClasificadorQuinta()
        self.procesador_ofertas = ProcesadorOfertas("", "")
        self.overrides_categoria = _cargar_overrides_categoria()

    def _get_win_path(self, path: Path) -> str:
        """Añade prefijo para rutas largas en Windows si es necesario."""
        p_str = str(path.absolute())
        if os.name == 'nt' and not p_str.startswith('\\\\?\\'):
            return f"\\\\?\\{p_str}"
        return p_str

    def procesar_persona(self, folder_persona):
        """Procesa una carpeta individual de una persona."""
        persona_nombre = folder_persona.name
        archivos = list(folder_persona.glob("*.*"))
        texto_carta = ''
        
        resultado = {
            'persona': persona_nombre,
            'dni': None,
            'carta_oferta': None,
            'dj_quinta': None,
            'estado': 'PENDIENTE',
            'mensaje': '',
            'terminos_carta': [],   # términos de beneficios encontrados en la carta oferta
        }

        # 0. Intentar extraer DNI de la carpeta como primera opción
        dni_carpeta = self.clasificador_quinta._extraer_dni_carpeta(folder_persona)
        if dni_carpeta:
            resultado['dni'] = dni_carpeta
        # 1. Buscar Carta Oferta
        for file in archivos:
            if self.procesador_ofertas.es_carta_oferta(file):
                resultado['carta_oferta'] = file
                texto_carta = self.procesador_ofertas.extraer_texto(file)
                # Detectar términos de beneficios
                resultado['terminos_carta'] = _detectar_terminos_carta(texto_carta)
                # Si no tenemos DNI, intentar extraer de la carta oferta
                if not resultado['dni']:
                    dni = self.clasificador_quinta._extraer_dni(texto_carta)
                    if dni:
                        resultado['dni'] = dni
                break

        # 2. Buscar DJ Quinta
        dj_quinta_fallback = None
        for file in archivos:
            if file.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png']:
                if resultado['carta_oferta'] and file.name == resultado['carta_oferta'].name:
                    continue

                res_quinta = self.clasificador_quinta.analizar_archivo(file)
                if res_quinta['status'] == 'OK':
                    resultado['dj_quinta'] = file
                    resultado['quinta_detalle'] = res_quinta
                    resultado['categoria'] = res_quinta.get('categoria')
                    resultado['categoria_info'] = res_quinta.get('categoria_info')
                    resultado['confianza_quinta'] = res_quinta.get('confianza', 0)

                    if res_quinta.get('dni') and not resultado['dni']:
                        resultado['dni'] = res_quinta['dni']

                    # Detectar términos también en el documento DJ Quinta
                    try:
                        import fitz as _fitz
                        doc = _fitz.open(self._get_win_path(file))
                        texto_quinta = '\n'.join(doc[i].get_text() for i in range(len(doc)))
                        doc.close()
                        terminos_quinta = _detectar_terminos_carta(texto_quinta)
                        existentes = resultado.get('terminos_carta', [])
                        resultado['terminos_carta'] = list(dict.fromkeys(existentes + terminos_quinta))
                    except Exception:
                        pass

                    # Si aún no hay DNI, buscar directamente en los campos/texto del PDF
                    if not resultado['dni'] and file.suffix.lower() == '.pdf':
                        dni_campos = self.clasificador_quinta._extraer_dni_campos_pdf(file)
                        if dni_campos:
                            resultado['dni'] = dni_campos
                    break
                elif res_quinta['status'] == 'WARNING' and not dj_quinta_fallback:
                    dj_quinta_fallback = (file, res_quinta)

        # Si no se encontró ningún documento OK, usar el de WARNING (ej. DNI escaneado como DJ)
        if not resultado['dj_quinta'] and dj_quinta_fallback:
            file, res_quinta = dj_quinta_fallback
            resultado['dj_quinta'] = file
            resultado['quinta_detalle'] = res_quinta
            resultado['categoria'] = res_quinta.get('categoria')
            resultado['categoria_info'] = res_quinta.get('categoria_info')
            resultado['confianza_quinta'] = res_quinta.get('confianza', 0)
            if res_quinta.get('dni') and not resultado['dni']:
                resultado['dni'] = res_quinta['dni']
            if not resultado['dni'] and file.suffix.lower() == '.pdf':
                dni_campos = self.clasificador_quinta._extraer_dni_campos_pdf(file)
                if dni_campos:
                    resultado['dni'] = dni_campos

        # 2a. Fallback de categoría: si no hay DJ Quinta válida, es practicante
        if not resultado.get('categoria'):
            resultado['categoria'] = 'PRACT'
            resultado['categoria_info'] = {
                'codigo': 'PRACT',
                'nombre': 'Practicante (inferido)',
                'descripcion': 'Categoría inferida porque no hay documento de declaración jurada de quinta.',
                'color': '#607D8B'
            }
            if not resultado.get('confianza_quinta'):
                resultado['confianza_quinta'] = 80

        # 2b. Identificar el DNI correcto entre todos los archivos DNI/CUI de la carpeta
        #     Usa OCR con rotaciones (0°/90°/180°/270°) y matching por nombre de persona
        #     Priorizamos SIEMPRE el DNI del documento oficial (si es confiable) sobre el DNI de los formularios.
        datos_dni = self.clasificador_quinta.identificar_dni_persona(folder_persona, persona_nombre)
        if datos_dni and datos_dni.get('numero'):
            resultado['dni'] = datos_dni['numero']  # Sobrescribe el DNI con la fuente de verdad

        # 2c. Último recurso — buscar en TODOS los PDFs de la carpeta
        if not resultado['dni']:
            for file in archivos:
                if file.suffix.lower() == '.pdf':
                    try:
                        import fitz as _fitz
                        doc = _fitz.open(self._get_win_path(file))
                        texto_completo = '\n'.join(doc[i].get_text() for i in range(min(len(doc), 3)))
                        doc.close()
                        dni = self.clasificador_quinta._extraer_dni(texto_completo)
                        if dni:
                            resultado['dni'] = dni
                            break
                    except Exception:
                        continue

        # 2d. Override manual de categoría por DNI o persona (si existe config)
        dni_over = self.overrides_categoria.get('dni', {})
        per_over = self.overrides_categoria.get('persona', {})
        categoria_override = None
        if resultado.get('dni'):
            categoria_override = dni_over.get(str(resultado['dni']).strip())
        if not categoria_override:
            persona_key = re.sub(r'^\d{4,8}\s*[-–]\s*', '', persona_nombre).strip().upper()
            categoria_override = per_over.get(persona_key)

        if categoria_override:
            resultado['categoria'] = categoria_override
            resultado['categoria_info'] = _categoria_info_override(categoria_override)
            resultado['confianza_quinta'] = 100
            resultado['mensaje'] = f'Categoría {categoria_override} por override manual'

        # 3. Acciones si se encontraron documentos
        if resultado['carta_oferta'] or resultado['dj_quinta']:
            # Nombre de carpeta destino: DNI primero si está disponible
            dni_val = resultado.get('dni')
            if dni_val:
                name_clean = re.sub(r'^\d{4,6}\s*[-–]\s*', '', persona_nombre).strip()
                dest_nombre = f"{dni_val} - {name_clean}"
            else:
                dest_nombre = persona_nombre

            dest_persona = self.ruta_destino / dest_nombre
            try:
                # Usar rutas largas para evitar WinError 3
                dest_persona_win = self._get_win_path(dest_persona)
                os.makedirs(dest_persona_win, exist_ok=True)

                # Mover archivos usando la API de sistema para mayor robustez
                if resultado['carta_oferta']:
                    src = self._get_win_path(resultado['carta_oferta'])
                    dst = os.path.join(dest_persona_win, f"Carta Oferta - {dest_nombre}{resultado['carta_oferta'].suffix}")
                    shutil.copy2(src, dst)

                if resultado['dj_quinta']:
                    src = self._get_win_path(resultado['dj_quinta'])
                    dst = os.path.join(dest_persona_win, f"DJ Quinta - {dest_nombre}{resultado['dj_quinta'].suffix}")
                    shutil.copy2(src, dst)
                
                resultado['estado'] = 'PROCESADO_OK'
                resultado['ruta_destino'] = str(dest_persona)
            except Exception as e:
                resultado['estado'] = 'ERROR_COPIA'
                resultado['mensaje'] = str(e)
        else:
            resultado['estado'] = 'NO_ENCONTRADO'
            resultado['mensaje'] = 'No se encontró Carta Oferta ni DJ Quinta'

        return resultado

    def ejecutar(self, max_workers=6, on_progress=None):
        """
        Ejecuta el proceso para todas las subcarpetas en la ruta origen.
        Limitado a 6 workers para evitar saturación de CPU por OCR y Tesseract.
        """
        if not self.ruta_origen.exists():
            return {"status": "ERROR", "message": f"Ruta origen no existe: {self.ruta_origen}"}
        
        # Asegurar destino con soporte de rutas largas
        os.makedirs(self._get_win_path(self.ruta_destino), exist_ok=True)
        
        subcarpetas = [d for d in self.ruta_origen.iterdir() if d.is_dir()]
        n = len(subcarpetas)
        resultados = []
        procesados = 0

        # Motor de procesamiento ultra-agresivo
        with ThreadPoolExecutor(max_workers=min(max_workers, n or 1)) as executor:
            futures = {executor.submit(self.procesar_persona, sc): sc for sc in subcarpetas}
            for future in as_completed(futures):
                procesados += 1
                try:
                    res = future.result()
                    # Convertir paths a strings para serialización
                    if res['carta_oferta']: res['carta_oferta'] = res['carta_oferta'].name
                    if res['dj_quinta']: res['dj_quinta'] = res['dj_quinta'].name
                    resultados.append(res)
                    
                    if on_progress:
                        on_progress(procesados, n, res)
                        
                except Exception as e:
                    err_res = {'persona': futures[future].name, 'estado': 'EXCEPTION', 'mensaje': str(e)}
                    resultados.append(err_res)
                    if on_progress:
                        on_progress(procesados, n, err_res)

        return {
            'status': 'OK',
            'resultados': resultados,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        proc = ProcesadorCombinado(sys.argv[1], sys.argv[2])
        resultado = proc.ejecutar()
        print(json.dumps(resultado, indent=2))

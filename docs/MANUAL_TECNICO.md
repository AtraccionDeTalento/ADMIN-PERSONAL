# Manual Técnico — Sistema DJ Quinta Categoría
**People Analytics · USIL**
**Documento:** MANUAL_TECNICO.md · v1.0 · 2026-06-01
**Audiencia:** Desarrolladores y personal de TI responsables del mantenimiento

---

## 1. Requisitos de Entorno

### Sistema Operativo
- Windows 10 / 11 (x64)
- El código incluye detección de `sys.platform == 'win32'` para comportamientos específicos de Windows

### Python
- **Versión mínima:** 3.10
- **Razón:** Uso de `match` no presente (compatible con 3.8+), pero `Pillow ≥ 10` requiere 3.8+; se recomienda 3.11 por mejoras de rendimiento en hilos

### Tesseract OCR (opcional pero recomendado)
- Instalador oficial: https://github.com/UB-Mannheim/tesseract/wiki
- Rutas detectadas automáticamente por el código:
  ```
  C:\Program Files\Tesseract-OCR\tesseract.exe
  C:\Program Files (x86)\Tesseract-OCR\tesseract.exe
  %APPDATA%\..\Local\Programs\Tesseract-OCR\tesseract.exe
  %APPDATA%\..\Local\Tesseract-OCR\tesseract.exe
  C:\Tesseract-OCR\tesseract.exe
  ```
- Sin Tesseract, los PDFs escaneados y las imágenes retornan `WARNING` en lugar de clasificarse

---

## 2. Instalación y Configuración

### 2.1 Primera instalación

```batch
:: Verificar Python
python --version          :: Debe ser 3.10+

:: Ejecutar instalador del sistema
INSTALAR.bat
```

`INSTALAR.bat` realiza:
1. Verifica Python en PATH
2. Crea `venv/` con `python -m venv venv`
3. Ejecuta `venv\Scripts\pip install -r requirements.txt`
4. Verifica la instalación con `python -c "import flask, fitz, openpyxl"`

### 2.2 Dependencias (requirements.txt)

```
flask>=2.3.0       # Servidor web y routing HTTP
pymupdf>=1.23.0    # Extracción de texto/gráficos de PDF (import fitz)
openpyxl>=3.1.0    # Generación y escritura de archivos .xlsx
werkzeug>=2.3.0    # Utilidades Flask; secure_filename para uploads
pytesseract>=0.3.10 # Wrapper Python para Tesseract OCR (opcional)
Pillow>=10.0.0     # Procesamiento de imágenes para OCR
```

### 2.3 Estructura del entorno virtual

```
venv/
├── Scripts/
│   ├── python.exe         ← intérprete visible en consola
│   ├── pythonw.exe        ← intérprete sin consola (usado por INICIAR.vbs)
│   ├── pip.exe
│   └── activate.bat
├── Lib/
│   └── site-packages/
│       ├── flask/
│       ├── fitz/          ← PyMuPDF
│       ├── openpyxl/
│       ├── PIL/           ← Pillow
│       └── pytesseract/
└── pyvenv.cfg
```

### 2.4 Configuración de overrides (`categoria_overrides.json`)

Permite asignar manualmente una categoría a un colaborador específico, sobreescribiendo cualquier resultado del clasificador automático.

```json
{
  "dni": {
    "72920386": "PRACT",
    "74563842": "1A"
  },
  "persona": {
    "URIBE DEL AGUILA ANA LUCIA": "PRACT",
    "CONDORI LIZARRAGA IVAN RENATO ANDRE": "1A"
  }
}
```

**Lógica de aplicación** (`procesador_combinado.py`, líneas 206-220):
1. Si el colaborador tiene DNI, se busca primero por DNI en `"dni"`.
2. Si no hay match por DNI, se limpia el prefijo numérico del nombre de carpeta y se busca en `"persona"`.
3. El override asigna confianza `100` y agrega el mensaje `"Categoría X por override manual"`.

**Categorías válidas para override:** `"1A"`, `"1B"`, `"2"`, `"3"`, `"PRACT"`

---

## 3. Descripción Detallada de Módulos

### 3.1 `clasificador_quinta.py` — Motor principal (1,845 líneas)

**Función:** Analizar un archivo PDF o imagen y determinar la categoría tributaria de quinta del colaborador.

#### Variables globales de módulo

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `_pytesseract` | módulo | Referencia lazy a pytesseract (None si no instalado) |
| `_PIL_Image`, `_PIL_ImageOps` | módulos | Referencia lazy a Pillow |
| `_OCR_DISPONIBLE` | bool | True si Tesseract fue encontrado e inicializado |
| `_google_vision` | módulo | Referencia lazy al cliente GCP Vision |
| `_VISION_DISPONIBLE` | bool | True si Google Vision está disponible |
| `_CACHE_DB` | str | Ruta al fichero shelve de caché (`cache_ocr_dni`) |
| `_EXTENSIONES_PDF` | set | `{'.pdf'}` |
| `_EXTENSIONES_IMAGEN` | set | `{'.jpg', '.jpeg', '.png', '.jfif', '.bmp', '.tiff', '.tif', '.gif', '.webp'}` |
| `_EXTENSIONES_SOPORTADAS` | set | Unión de PDF + imagen |
| `_SKIP_FILENAME_PATTERNS` | list[str] | Nombres que indican que NO es quinta (filtro rápido) |
| `_QUINTA_KWORDS` | list[str] | 13 frases que confirman que el doc ES quinta |
| `CATEGORIAS` | dict | Definición completa de las 4 categorías |

#### Funciones de módulo (nivel global)

```python
_cache_key(archivo_path: Path) -> str | None
```
Calcula MD5 de los primeros 128 KB del archivo. Clave del caché shelve.

```python
_cache_get(archivo_path: Path) -> dict | None
_cache_set(archivo_path: Path, datos: dict) -> None
```
Lectura/escritura del caché OCR. Captura toda excepción silenciosamente.

```python
_inicializar_ocr() -> bool
```
Lazy-load de pytesseract y Pillow. Detecta la ruta del ejecutable `tesseract.exe` en 5 ubicaciones comunes de Windows. Retorna False si no está disponible.

```python
_inicializar_google_vision() -> bool
```
Lazy-load del cliente `google.cloud.vision`. Inactivo por defecto — requiere credenciales GCP en `GOOGLE_APPLICATION_CREDENTIALS`.

```python
_ocr_google_vision(img_pil: PIL.Image) -> str | None
```
Envía imagen PIL a la API de text detection de GCP Vision. Solo se llama si el archivo tiene "dni" o "cui" en el nombre y GCP Vision está disponible.

```python
_mejorar_contraste_dni(img: PIL.Image) -> PIL.Image
```
Aplica escala de grises + autocontrast + UnsharpMask. Para imágenes ya en alta resolución.

```python
_mejorar_imagen_dni(img: PIL.Image) -> PIL.Image
```
Escala la imagen 3×–8× (según resolución base) + mismos filtros que `_mejorar_contraste_dni`. Para fotos de baja resolución de DNI/CUI.

```python
_es_posible_quinta(file_path: Path) -> bool
```
Filtro rápido por nombre de archivo. Retorna False si el nombre contiene patrones de documentos que nunca son quinta (carta oferta, contrato, boleta, etc.).

```python
_extraer_datos_documento_dni(texto: str) -> dict
```
Extrae `{apellidos, prenombres, nombre_completo, numero, sexo}` de texto OCR de un DNI/CUI peruano. Soporta formato CUI vertical, DNI horizontal clásico y MRZ (Machine Readable Zone).

```python
_puntaje_match_dni(datos_dni: dict, nombre_carpeta: str) -> float
```
Score 0.0–1.0 de coincidencia entre palabras del nombre del DNI y de la carpeta. Filtra stopwords: DE, LA, LOS, DEL.

#### Clase `ClasificadorQuinta`

##### Atributos de clase (rangos Y para detección de checkboxes)

```python
CHECKBOX_Y_STD = {'opcion1': (170, 210), 'opcion2': (230, 270), 'opcion3': (275, 320)}
CHECKBOX_Y_OLD = {'opcion1': (140, 180), 'opcion2': (200, 250), 'opcion3': (255, 310)}
CHECKBOX_Y_WIDE = {'opcion1': (100, 250), 'opcion2': (200, 350), 'opcion3': (280, 450)}
```

> Los rangos representan la coordenada Y (en puntos PDF) donde se espera encontrar cada opción en el formulario. `STD` es el formato actual, `OLD` el formato antiguo, `WIDE` es el fallback de último recurso.

##### Método principal

```python
analizar_archivo(archivo_path: Path | str) -> dict
```
Dispatcher: decide si llamar a `analizar_pdf` o `analizar_imagen` según la extensión.

##### `analizar_pdf(pdf_path: Path) -> dict`

Flujo completo:
1. `_es_posible_quinta()` — filtro rápido por nombre
2. `fitz.open()` — abrir PDF
3. `page.get_text()` — texto nativo página 1
4. `_necesita_ocr()` — ¿texto < 120 chars?
5. Si escaneado: `_texto_via_ocr()` — Tesseract con preprocesamiento
6. `_es_declaracion_quinta()` — verificar keywords de quinta
7. Cascada de 6 métodos de detección (ver sección 3.1.1)
8. `_extraer_dni()` — extracción de DNI del texto

##### `analizar_imagen(img_path: Path) -> dict`

Flujo:
1. `_inicializar_ocr()` — Tesseract disponible
2. Detectar si es documento DNI (por nombre de archivo)
3. Si es DNI: `_mejorar_imagen_dni()` + intentar Google Vision primero
4. Intentar 4 rotaciones (0°/180°/90°/270°) con PSM 6, 3, 4, 1
5. `_es_declaracion_quinta()` — verificar resultado
6. Cascada de 2 métodos de detección: texto y keywords

##### 3.1.1 Métodos de detección en cascada (para PDFs)

**Método 1 — Drawings** (`_detectar_por_drawings`)
- Extrae elementos gráficos con `page.get_drawings()`
- Identifica rectángulos pequeños (4–20 pt) como candidatos a checkbox
- Detecta si un checkbox está marcado: cuenta líneas que pasan por su interior
- Mapea la coordenada Y del checkbox marcado a `opcion1/2/3` usando los rangos Y

**Método 1b — Formato Antiguo** (`_detectar_formato_antiguo`)
- El formulario antiguo tiene opciones numeradas `1.-`, `2.-`, `3.-`
- Busca "X" como elemento de texto en el margen izquierdo (x < 200)
- Calcula distancia Y entre cada "X" y cada opción numerada
- Umbral de confianza: distancia ≤ 35 puntos PDF

**Método 1c — Widgets PDF** (`_detectar_por_widgets`)
- `page.widgets()` retorna campos de formulario (CheckBox, RadioButton)
- Valor marcado: `field_value` en `{'yes', 'on', 'true', '1', 'x'}`
- Prioriza match por nombre de campo (`opcion1`, `nohepercibido`, etc.)
- Fallback: mapeo por coordenada Y

**Método 2 — Texto -X** (`_detectar_por_texto`)
- Busca líneas que empiecen con `-X`, `[X]`, `(X)`, `X `
- Verifica si la misma línea contiene "no he percibido" (→ 1B) o "sí he percibido" (→ 1A)
- Más tolerante: funciona con texto OCR y formatos nativos

**Método 3 — Spans Bold** (`_detectar_por_spans`)
- Extrae spans con `font.contains('Bold')` y `text == 'X'`
- Solo aplica para PDFs nativos (el OCR no preserva datos de fuente)
- Busca texto asociado en la misma línea

**Método 4 — Keywords** (`_detectar_por_keywords`)
- Más permisivo: usa regex para detectar marcas con errores de OCR
  - `h&X]`, `b$X]` (errores comunes de Tesseract con checkboxes)
- Analiza contexto (150 chars) tras cada marca
- Estrategia alternativa: detecta estructura del documento + proximidad

##### Métodos de extracción de datos

```python
_extraer_dni(texto: str) -> str | None
```
3 estrategias en orden:
1. Patrones con etiqueta explícita (12 regex): `DNI:`, `N° DOC:`, `CUI:`, etc.
2. Ventana de contexto: busca "DNI"/"DOCUMENTO" + primer número de 8-12 dígitos en 80 chars
3. Fallback: todos los números de 8 dígitos, filtrando fechas (DDMMAAAA, AAAAMMDD)

```python
_extraer_dni_campos_pdf(pdf_path: Path) -> str | None
```
Extrae DNI de campos de formulario PDF fillable (DocuSign, Adobe Sign, Word→PDF). Prioriza campos cuyo nombre contenga "dni", "doc", "ident", "cui", "nro".

```python
_extraer_dni_carpeta(path: Path) -> str | None
```
Extrae DNI del nombre de la carpeta padre. Patrón: `^(\d{8})\s*[-–\s]`.

```python
identificar_dni_persona(carpeta_path: Path, nombre_persona: str) -> dict | None
```
Busca archivos con "dni" o "cui" en el nombre dentro de la carpeta. Aplica OCR con caché. Retorna el que tiene puntaje de coincidencia ≥ 0.25 con el nombre de persona. Usa `ThreadPoolExecutor(4)` interno con cancelación temprana al encontrar puntaje ≥ 0.75.

---

### 3.2 `procesador_ofertas.py` — Motor de Cartas Oferta (203 líneas)

#### Clase `ProcesadorOfertas`

**Constructor:** `__init__(ruta_origen: str, ruta_destino: str)`
- Convierte rutas a `Path`
- Llama `_init_tesseract()` para configurar Tesseract (si disponible)

**Constante de clase:**
```python
KEYWORDS = {
    'Bono de transporte': [r'bono\s+de\s+transporte', r'bono\s+transporte'],
    'Prestación Alimentaria': [r'prestaci[oó]n\s+alimentaria', r'provisi[oó]n\s+alimentaria'],
    'Asignación de Movilidad': [r'asignaci[oó]n\s+de\s+movilidad', r'movilidad\s+local', r'gastos\s+de\s+movilidad']
}
```

**Métodos clave:**

```python
es_carta_oferta(file_path: Path) -> bool
```
Heurística por nombre: retorna True si `'carta' in name and 'oferta' in name`.
> **Limitación:** Frágil ante nombres distintos a la convención esperada.

```python
extraer_texto(file_path: Path) -> str
```
Extracción de texto para triage:
- PDF: `fitz` texto nativo; si < 60 chars no espacios → OCR
- Imagen: OCR directo
- Normaliza (minúsculas + colapso de espacios)

```python
triage_contenido(texto: str) -> list[str]
```
Detecta beneficios adicionales con `KEYWORDS`. Retorna lista de labels o `["Contrato Regular"]` si ninguno.

```python
ejecutar() -> dict
```
Proceso completo de escaneo y movimiento:
1. Itera subcarpetas de `ruta_origen`
2. Para cada persona: busca carta oferta con `glob("*.pdf")`
3. Extrae texto + triage
4. `shutil.move()` → `ruta_destino/Carta Oferta - {persona}.pdf`
> **ATENCIÓN:** Usa `shutil.move()` — operación destructiva. Solo procesa la primera carta encontrada por persona.

---

### 3.3 `procesador_combinado.py` — Orquestador Dual (309 líneas)

#### Funciones de módulo

```python
_cargar_overrides_categoria() -> dict
```
Lee `categoria_overrides.json` desde el directorio del script. Retorna `{'dni': {}, 'persona': {}}` si no existe o hay error.

```python
_detectar_terminos_carta(texto: str) -> list[str]
```
Detecta los 3 beneficios usando regex (mismos que `_TERMINOS_BENEFICIOS` — lista de `{id, label, patron}`).

#### Clase `ProcesadorCombinado`

```python
__init__(ruta_origen: str, ruta_destino: str)
```
Instancia `ClasificadorQuinta`, `ProcesadorOfertas("","")`, carga overrides.

```python
_get_win_path(path: Path) -> str
```
Añade prefijo `\\?\` para rutas largas de Windows (evita `WinError 3`).

```python
procesar_persona(folder_persona: Path) -> dict
```
Pipeline completo por carpeta (ver diagrama en ARQUITECTURA.md).

**Estructura del resultado:**
```python
{
    'persona': str,          # nombre de carpeta
    'dni': str | None,       # DNI resuelto (8-12 dígitos)
    'carta_oferta': str,     # nombre del archivo (solo el nombre, sin ruta)
    'dj_quinta': str,        # nombre del archivo
    'categoria': str,        # 1A | 1B | 2 | 3 | PRACT | None
    'categoria_info': dict,
    'confianza_quinta': float,
    'terminos_carta': list,  # beneficios detectados
    'estado': str,           # PROCESADO_OK | NO_ENCONTRADO | ERROR_COPIA | EXCEPTION
    'ruta_destino': str,
    'mensaje': str
}
```

```python
ejecutar(max_workers: int = 6, on_progress: callable = None) -> dict
```
Ejecuta `ThreadPoolExecutor(min(6, N))`. Llama `on_progress(current, total, resultado)` después de cada persona completada. El servidor usa este callback para actualizar `_DUAL_TASKS`.

---

### 3.4 `servidor_dj_quinta.py` — Servidor Flask (755 líneas)

#### Configuración de la aplicación

```python
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024   # límite upload: 500 MB
app.config['UPLOAD_FOLDER'] = BASE_DIR / 'uploads_quinta'
```

#### Objeto global compartido

```python
clasificador = ClasificadorQuinta()   # instancia única, usada por todos los requests
_DUAL_TASKS = {}                      # {task_id: {status, current, total, resultados, ...}}
```

#### Función `_procesar_por_personas(subcarpetas: list[Path]) -> list[dict]`

Función helper interna del servidor (distinta de `ProcesadorCombinado`). Procesamiento en modo "solo quinta":
- Identifica la mejor declaración de quinta por carpeta
- Enriquece con datos del DNI verificado (`identificar_dni_persona`)
- Reporta "Sin declaración" para carpetas sin archivo quinta
- `max_workers = min(8, N)`

#### Generación de Excel (ruta `/api/v1/quinta/exportar-excel`)

Genera un workbook openpyxl con 2 hojas:
1. **"Clasificacion DJ Quinta"** — tabla con N°, Persona, DNI, Nombre, Categoría, Descripción. Colores por categoría. Filtros automáticos.
2. **"Resumen"** — estadísticas (total, exitosos, errores, conteo por categoría).

Entregado como stream en memoria (`BytesIO`) para evitar archivos temporales.

---

### 3.5 `launcher.py` — Arranque con Diagnóstico (216 líneas)

Script de Python puro que verifica el entorno antes de iniciar el servidor.

#### Clase `Color`
Constantes ANSI para terminal coloreada (`\033[92m`, etc.).

#### Función `diagnostico() -> bool`
Verifica en orden:
1. `venv/Scripts/python.exe` existe
2. `servidor_dj_quinta.py` existe
3. Python funcional (`python --version`)
4. Puerto 5010 disponible (`socket.connect_ex`)

Si el puerto está ocupado, intenta `taskkill /F /FI "WINDOWTITLE eq Sistema*"`.

#### Función `iniciar_servidor() -> bool`
Lanza `venv/Scripts/pythonw.exe servidor_dj_quinta.py` con `CREATE_NEW_CONSOLE`. Espera hasta 30 segundos verificando el puerto. Retorna `True` con timeout si el servidor tarda (asume éxito).

---

### 3.6 `select_folder.py` — Diálogo Nativo (16 líneas)

Ejecutado como **proceso hijo** por `servidor_dj_quinta.py` vía `subprocess.run()`. La separación de proceso es necesaria porque `tkinter` no es thread-safe con Flask en modo threading.

```python
# En servidor_dj_quinta.py (ruta /api/v1/utils/select-folder)
res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
folder = res.stdout.strip()   # ruta seleccionada por el usuario
```

---

## 4. Configuración de Inicio — INICIAR.vbs

El script VBS realiza las siguientes acciones:
1. Localiza `{dir}\venv\Scripts\pythonw.exe`
2. Si no existe: ofrece ejecutar `INSTALAR.bat` (síncrono, muestra ventana)
3. Verifica que Python funcione (`pythonw.exe --version`)
4. Libera el puerto 5010 si está en uso (via `netstat + taskkill`)
5. Lanza `pythonw.exe servidor_dj_quinta.py` asíncronamente (sin consola)
6. Espera 3 segundos (`WScript.Sleep 3000`)
7. Abre `http://localhost:5010` en el navegador predeterminado

---

## 5. Logging y Diagnóstico

El sistema no implementa logging estructurado. El diagnóstico está centralizado en:

| Archivo | Qué registra |
|---------|-------------|
| `logs_iniciar.txt` | Salida del launcher (timestamps + estado) |
| Consola (si se lanza con `python.exe`) | Errores de import, excepciones no capturadas |
| `_DUAL_TASKS[task_id]['traceback']` | Traceback de errores en tareas background |

Para activar logging durante desarrollo:
```bash
python servidor_dj_quinta.py
# El servidor muestra mensajes en consola
```

Para diagnóstico de PDFs específicos:
```bash
venv\Scripts\python.exe clasificador_quinta.py "ruta/al/archivo.pdf"
# Salida en consola con resultado y método de detección
```

---

## 6. Extensión del Sistema

### 6.1 Agregar un nuevo método de detección de categoría

1. En `clasificador_quinta.py`, añadir el método dentro de `ClasificadorQuinta`:
   ```python
   def _detectar_por_mi_metodo(self, page) -> tuple[str, float, str]:
       # Retorna: (categoria | None, confianza_0_100, nombre_metodo)
       ...
   ```
2. Agregar la llamada en `analizar_pdf()` después del Método 4:
   ```python
   if categoria is None:
       categoria, confianza, metodo = self._detectar_por_mi_metodo(page)
   ```

### 6.2 Agregar detección de un nuevo beneficio en cartas oferta

1. En `procesador_combinado.py`, agregar a `_TERMINOS_BENEFICIOS`:
   ```python
   {
       'id':     'seguro_vida',
       'label':  'Seguro de Vida',
       'patron': r'seguro\s+de\s+vida',
   }
   ```
2. El mismo patrón está duplicado en `procesador_ofertas.py::KEYWORDS`. Actualizar también:
   ```python
   KEYWORDS['Seguro de Vida'] = [r'seguro\s+de\s+vida']
   ```

> **Deuda técnica:** La lista de beneficios está duplicada en dos módulos (ver AUDITORIA_CODIGO.md DT-08).

### 6.3 Agregar un nuevo endpoint al servidor

```python
@app.route('/api/v1/mi_ruta', methods=['POST'])
def api_mi_funcion():
    data = request.json
    if not data or 'campo' not in data:
        return jsonify({'status': 'ERROR', 'message': 'Falta campo'}), 400
    # lógica
    return jsonify({'status': 'OK', 'resultado': ...}), 200
```

### 6.4 Personalizar rangos de categorías tributarias

Si SUNAT actualiza el formulario y los checkboxes cambian de posición:
1. Abrir un PDF de muestra con `_test_struct.py` (adaptando la ruta hardcodeada)
2. Anotar las coordenadas Y de los checkboxes
3. Actualizar `CHECKBOX_Y_STD` en `ClasificadorQuinta`

---

## 7. Procedimientos de Mantenimiento

### 7.1 Actualizar dependencias

```batch
venv\Scripts\pip install --upgrade flask pymupdf openpyxl werkzeug pytesseract Pillow
venv\Scripts\pip freeze > requirements_lock.txt   :: guardar versiones exactas
```

> Después de actualizar PyMuPDF, verificar que `fitz.open()` y `page.get_drawings()` funcionan con los PDFs existentes, ya que el API ha cambiado entre versiones mayores.

### 7.2 Limpiar caché OCR

```batch
:: Borrar el caché si está corrupto o muy grande
del cache_ocr_dni.db
del cache_ocr_dni.dir
del cache_ocr_dni.bak
```

O desde Python:
```python
import shelve, os
db_path = 'cache_ocr_dni'
for ext in ['', '.db', '.dir', '.bak']:
    try: os.remove(db_path + ext)
    except FileNotFoundError: pass
```

### 7.3 Eliminar entorno virtual huérfano

```batch
rmdir /s /q .venv
```

> Ver DT-01 en AUDITORIA_CODIGO.md.

### 7.4 Gestión del directorio de uploads

`uploads_quinta/` acumula archivos subidos vía browser que no son limpiados automáticamente (excepto por la ruta `/api/v1/ofertas/clasificar`). Limpiar periódicamente:

```batch
:: Borrar archivos de más de 7 días
forfiles /p uploads_quinta /s /m *.* /d -7 /c "cmd /c del @path" 2>nul
```

### 7.5 Reiniciar el servidor sin cerrar el navegador

Usar la ruta de reinicio:
```http
POST http://localhost:5010/api/v1/quinta/reiniciar
```
El servidor lanza un nuevo proceso Python y termina el actual después de 0.5 segundos.

> **Advertencia:** Las tareas en `_DUAL_TASKS` se pierden al reiniciar.

---

## 8. Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `INICIAR.vbs` no hace nada | `venv/` no existe | Ejecutar `INSTALAR.bat` |
| `INICIAR.vbs` abre consola y cierra | Python no en PATH o venv dañado | `DIAGNOSTICO.bat` → seguir indicaciones |
| Puerto 5010 ya en uso | Instancia previa no cerrada | `INICIAR.vbs` lo libera automáticamente; o `taskkill /F /IM pythonw.exe` |
| PDFs escaneados retornan WARNING | Tesseract no instalado | Instalar desde https://github.com/UB-Mannheim/tesseract/wiki |
| Categoría incorrecta | Formato de PDF no soportado por métodos actuales | Inspeccionar con `_test_struct.py`; actualizar `CHECKBOX_Y_STD` si es necesario |
| `WinError 3` en proceso combinado | Ruta > 260 caracteres | El código ya usa `\\?\` prefix; verificar que `_get_win_path` se llama en todos los `fitz.open()` |
| Caché retorna datos incorrectos | Archivo modificado pero MD5 no cambió (improbable) | Limpiar `cache_ocr_dni.*` |
| `.venv/` en lugar de `venv/` referenciado | Confusión entre entornos | Verificar que `INICIAR.vbs` apunta a `venv\Scripts\pythonw.exe` |

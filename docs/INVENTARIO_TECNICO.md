# INVENTARIO TÉCNICO — Sistema de Administración Personal
**People Analytics · Universidad San Ignacio de Loyola (USIL)**
**Fecha de análisis:** 2026-06-01
**Analista:** Claude Sonnet 4.6

---

## 1. QUÉ HACE EL SISTEMA

El **Sistema de Administración Personal** es una aplicación web local (Flask, puerto 5010) que automatiza dos procesos de RRHH que antes requerían revisión manual de PDFs:

**Funcionalidad 1 — Clasificador DJ Quinta Categoría**
Lee PDFs de *Declaración Jurada de Quinta Categoría* (el formulario tributario que todo colaborador nuevo entrega a RRHH) y determina automáticamente en qué categoría está el empleado:

| Categoría | Significado |
|-----------|-------------|
| **1A** | USIL es único empleador **y** el colaborador SÍ percibió renta quinta antes |
| **1B** | USIL es único empleador **y** el colaborador NO percibió renta quinta antes |
| **2** | USIL es empleador principal pero existen otros empleadores que también retienen quinta |
| **3** | USIL NO es el empleador principal — solicita que no le retengan |
| **PRACT** | Practicante (inferido o asignado por override manual) |

**Funcionalidad 2 — Proceso Combinado (Cartas Oferta + Quinta)**
Toma una carpeta de personas que contiene múltiples documentos mezclados (carta oferta, DJ quinta, DNI/CUI, otros), identifica los dos documentos clave, extrae el DNI del colaborador y los copia a una carpeta destino con nombres estandarizados. También detecta si la carta oferta incluye beneficios especiales (bono de transporte, prestación alimentaria, asignación de movilidad).

---

## 2. ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE ARRANQUE                             │
│  INICIAR.vbs  →  venv/Scripts/pythonw.exe  →  servidor_dj_quinta.py
│  launcher.py  (fallback con diagnóstico)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ Flask :5010
┌────────────────────────▼────────────────────────────────────────┐
│                  CAPA WEB (servidor_dj_quinta.py)               │
│                                                                 │
│  GET  /                → templates/quinta_categoria.html (SPA)  │
│                                                                 │
│  ┌─ API Quinta ─────────────────────────────────────────────┐   │
│  │  POST /api/v1/quinta/clasificar          (upload archivos)│   │
│  │  POST /api/v1/quinta/clasificar-rutas    (rutas locales)  │   │
│  │  POST /api/v1/quinta/clasificar-carpeta  (carpeta raíz)   │   │
│  │  POST /api/v1/quinta/exportar-excel      (genera .xlsx)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ API Ofertas ────────────────────────────────────────────┐   │
│  │  POST /api/v1/ofertas/procesar           (rutas origen/destino)│
│  │  POST /api/v1/ofertas/clasificar         (upload directo) │   │
│  │  POST /api/v1/ofertas/procesar-rutas     (lista de rutas) │   │
│  │  POST /api/v1/ofertas/exportar-excel     (reporte xlsx)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ API Combinado ──────────────────────────────────────────┐   │
│  │  POST /api/v1/combinado/procesar         (lanza tarea BG) │   │
│  │  GET  /api/v1/combinado/status/<task_id> (polling estado) │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Utils ──────────────────────────────────────────────────┐   │
│  │  POST /api/v1/utils/select-folder   (diálogo nativo Win) │   │
│  │  POST /api/v1/utils/open-folder     (abrir en Explorer)  │   │
│  │  POST /api/v1/quinta/reiniciar      (restart del proceso) │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │ importa
┌────────────────────────▼────────────────────────────────────────┐
│                   CAPA DE NEGOCIO                               │
│                                                                 │
│  clasificador_quinta.py   ←  Motor de clasificación PDF/imagen  │
│  procesador_ofertas.py    ←  Identificación y triage de cartas  │
│  procesador_combinado.py  ←  Orquesta ambos procesadores        │
│  select_folder.py         ←  Auxiliar Tkinter (proceso aparte)  │
└─────────────────────────────────────────────────────────────────┘
                         │ lee/escribe
┌────────────────────────▼────────────────────────────────────────┐
│                   CAPA DE DATOS / ARCHIVOS                      │
│                                                                 │
│  uploads_quinta/           ←  Archivos subidos vía browser      │
│  categoria_overrides.json  ←  Overrides manuales de categoría   │
│  cache_ocr_dni             ←  Caché shelve (MD5 → datos DNI)    │
│  FUNCIONALIDAD 2/          ←  Datos de prueba                   │
│    Data de Prueba/         ←  Entrada: carpetas por persona      │
│    DESTINO/                ←  Salida: PDFs renombrados y copiados│
│  Reporte_Cartas_Oferta.xlsx ← Último reporte generado           │
└─────────────────────────────────────────────────────────────────┘
```

**Patrón de concurrencia:** Todas las operaciones de lectura de PDF usan `ThreadPoolExecutor` (hasta 8 workers para quinta, 6 para combinado). Tesseract libera el GIL en Python, por lo que el paralelismo de hilos es efectivo.

**Sin base de datos:** El sistema no usa BD relacional. El estado de las tareas en curso vive en el dict en memoria `_DUAL_TASKS` (se pierde si el servidor se reinicia).

---

## 3. ESTRUCTURA DE CARPETAS

```
SISTEMA DE ADMIN PERSONAL/
│
├── ── ARCHIVOS EJECUTABLES / ARRANQUE ──
│   ├── INICIAR.vbs              (punto de entrada recomendado — doble clic)
│   ├── launcher.py              (arranque con diagnóstico — fallback)
│   ├── INSTALAR.bat             (setup inicial: crea venv, instala deps)
│   └── DIAGNOSTICO.bat          (verificación de entorno)
│
├── ── NÚCLEO DE LA APLICACIÓN ──
│   ├── servidor_dj_quinta.py    (Flask app, 755 líneas — todas las rutas)
│   ├── clasificador_quinta.py   (motor de análisis PDF/imagen, 1845 líneas)
│   ├── procesador_ofertas.py    (motor de cartas oferta, 203 líneas)
│   ├── procesador_combinado.py  (orquestador dual, 309 líneas)
│   └── select_folder.py         (auxiliar Tkinter, 16 líneas)
│
├── ── CONFIGURACIÓN ──
│   ├── requirements.txt         (6 dependencias: flask, pymupdf, openpyxl, werkzeug, pytesseract, Pillow)
│   └── categoria_overrides.json (overrides manuales: 9 DNIs, 9 nombres)
│
├── ── INTERFAZ WEB ──
│   └── templates/
│       └── quinta_categoria.html  (SPA completa, 92 KB — JavaScript + CSS inline)
│
├── ── ENTORNOS VIRTUALES (AMBOS PRESENTES — deuda técnica) ──
│   ├── venv/          (entorno activo — referenciado por INICIAR.vbs y launcher.py)
│   └── .venv/         (entorno huérfano — no referenciado por ningún script)
│
├── ── DATOS / RUNTIME ──
│   ├── uploads_quinta/            (archivos subidos vía browser — vacía en reposo)
│   ├── cache_ocr_dni              (shelve DB — caché de resultados OCR por MD5)
│   ├── Reporte_Cartas_Oferta.xlsx (último reporte generado, 5.3 KB)
│   └── logs_iniciar.txt           (log del launcher)
│
├── ── DATOS DE PRUEBA ──
│   └── FUNCIONALIDAD 2/
│       ├── C.txt                  (notas de voz/requirements del usuario)
│       ├── Data de Prueba/        (10 carpetas de personas, 119 archivos)
│       └── DESTINO/               (46 carpetas de salida con 85 archivos procesados)
│
├── ── SCRIPTS DE PRUEBA (desarrollo) ──
│   ├── _test_diag.py    (clasificación de batch de PDFs)
│   ├── _test_full.py    (lectura raw de texto PDF específico)
│   ├── _test_struct.py  (inspección de estructura PDF: coordenadas + drawings)
│   └── _test_texto.py   (inspección de texto por chunks)
│
├── ── DOCUMENTACIÓN ──
│   ├── README.md          (guía de usuario / instalación)
│   ├── PRIMERO_LEE.txt    (instrucciones rápidas para nuevas PCs)
│   └── docs/              (carpeta de documentación técnica — recién creada)
│
└── ── CACHÉ PYTHON ──
    └── __pycache__/       (bytecode compilado — 7 archivos .pyc)
```

---

## 4. DEPENDENCIAS

### Python (requirements.txt)

| Librería | Versión mínima | Uso |
|----------|---------------|-----|
| `flask` | ≥ 2.3.0 | Framework web HTTP |
| `pymupdf` (fitz) | ≥ 1.23.0 | Extracción de texto y gráficos de PDF |
| `openpyxl` | ≥ 3.1.0 | Generación de reportes Excel (.xlsx) |
| `werkzeug` | ≥ 2.3.0 | Utilidades Flask (secure_filename) |
| `pytesseract` | ≥ 0.3.10 | Wrapper Python para Tesseract OCR (opcional) |
| `Pillow` | ≥ 10.0.0 | Procesamiento de imágenes para OCR |

### Dependencias de sistema (externas, no en requirements)

| Herramienta | Requerido | Uso |
|-------------|-----------|-----|
| **Python 3.10+** | Sí | Runtime |
| **Tesseract OCR** | Opcional | PDFs escaneados e imágenes. Sin él, solo funciona con PDFs de texto nativo |
| **Google Cloud Vision API** | Opcional | OCR alternativo para DNIs (requiere credenciales GCP — código presente pero sin uso activo documentado) |

### Dependencias built-in utilizadas

`os`, `sys`, `re`, `json`, `shelve`, `hashlib`, `threading`, `subprocess`, `socket`, `webbrowser`, `concurrent.futures`, `pathlib`, `datetime`, `io`, `shutil`, `tkinter`

---

## 5. MÓDULOS Y SUS RESPONSABILIDADES

### `clasificador_quinta.py` — 1,845 líneas

**El módulo más complejo del sistema.** Motor de análisis de PDFs e imágenes.

#### Variables globales / constantes
| Nombre | Tipo | Descripción |
|--------|------|-------------|
| `_pytesseract` | módulo | Instancia de pytesseract (lazy-loaded) |
| `_PIL_Image`, `_PIL_ImageOps` | módulos | Pillow (lazy-loaded) |
| `_OCR_DISPONIBLE` | bool | Flag de disponibilidad de Tesseract |
| `_google_vision` | módulo | Cliente Google Vision (lazy-loaded) |
| `_VISION_DISPONIBLE` | bool | Flag de disponibilidad de GCP Vision |
| `_CACHE_DB` | str | Ruta del shelve de caché OCR |
| `_EXTENSIONES_PDF` | set | `{'.pdf'}` |
| `_EXTENSIONES_IMAGEN` | set | 9 extensiones (jpg, png, tiff, etc.) |
| `_EXTENSIONES_SOPORTADAS` | set | Unión de PDF + imagen |
| `_SKIP_FILENAME_PATTERNS` | list | Nombres que indica que NO es quinta (carta oferta, contrato, etc.) |
| `_QUINTA_KWORDS` | list | 13 frases que confirman que el documento ES quinta |
| `CATEGORIAS` | dict | Definición de las 4 categorías con nombre, descripción y color |

#### Funciones de módulo (nivel global)
| Función | Descripción |
|---------|-------------|
| `_cache_key(archivo_path)` | MD5 de primeros 128 KB del archivo |
| `_cache_get(archivo_path)` | Lee del shelve por hash |
| `_cache_set(archivo_path, datos)` | Escribe en shelve |
| `_inicializar_ocr()` | Lazy-load de pytesseract + detección de ruta Tesseract |
| `_inicializar_google_vision()` | Lazy-load del cliente GCP Vision |
| `_ocr_google_vision(img_pil)` | Envía imagen PIL a GCP Vision API |
| `_mejorar_contraste_dni(img)` | Contraste + nitidez sin escalar (DNIs en alta res) |
| `_mejorar_imagen_dni(img)` | Escala 3×–8× + contraste (fotos de baja res) |
| `_es_posible_quinta(file_path)` | Heurística por nombre de archivo para filtrado rápido |
| `_extraer_datos_documento_dni(texto)` | Extrae apellidos/prenombres/número/sexo de texto OCR de DNI/CUI |
| `_puntaje_match_dni(datos_dni, nombre_carpeta)` | Score 0.0–1.0 de coincidencia nombre carpeta vs DNI |

#### Clase `ClasificadorQuinta`
**Responsabilidad:** Analizar un archivo (PDF o imagen) y devolver la categoría tributaria.

**Atributos de clase:**
| Atributo | Descripción |
|----------|-------------|
| `CHECKBOX_Y_STD` | Rangos Y para formato estándar de DJ quinta |
| `CHECKBOX_Y_OLD` | Rangos Y para formato antiguo |
| `CHECKBOX_Y_WIDE` | Rangos amplios como último recurso |

**Métodos públicos:**
| Método | Firma simplificada | Descripción |
|--------|-------------------|-------------|
| `analizar_archivo` | `(archivo_path) → dict` | Dispatcher por extensión (PDF vs imagen) |
| `analizar_pdf` | `(pdf_path) → dict` | Análisis completo de PDF (5 métodos de detección en cascada) |
| `analizar_imagen` | `(img_path) → dict` | OCR con múltiples rotaciones (0°/90°/180°/270°) |
| `analizar_lote` | `(rutas, max_workers=8) → list[dict]` | Procesa lista de rutas en paralelo |
| `analizar_carpeta_recursivo` | `(carpeta, max_workers=8) → list[dict]` | Escaneo recursivo de carpeta |
| `identificar_dni_persona` | `(carpeta_path, nombre_persona) → dict|None` | Busca archivos DNI/CUI en carpeta y devuelve el que coincide con el nombre |
| `generar_resumen` | `(resultados) → dict` | Estadísticas agregadas (total, exitosos, por categoría) |

**Métodos de detección (en orden de cascada para PDFs):**
| Método | Técnica | Confianza típica |
|--------|---------|-----------------|
| `_detectar_por_drawings` | Checkboxes gráficos (rectangles + líneas) | 70–95% |
| `_detectar_formato_antiguo` | "X" como texto + proximidad a opciones numeradas | 65–92% |
| `_detectar_por_widgets` | Widgets de formulario PDF (CheckBox/RadioButton) | 65–80% |
| `_detectar_por_texto` | Marcas `-X`, `[X]`, `(X)` en texto plano | 80–90% |
| `_detectar_por_spans` | Spans Bold "X" (solo PDFs nativos) | 75–85% |
| `_detectar_por_keywords` | Keywords contextuales + patrones regex | 55–85% |

**Métodos de extracción de datos:**
| Método | Extrae |
|--------|--------|
| `_extraer_dni` | DNI/CE con 3 estrategias (etiqueta, ventana contextual, fallback) |
| `_extraer_dni_campos_pdf` | DNI desde campos de formulario fillable |
| `_extraer_dni_carpeta` | DNI desde nombre de carpeta (`12345678 - NOMBRE`) |
| `_extraer_nombre` | Nombre desde texto del documento o carpeta padre |
| `_extraer_persona_carpeta` | Nombre de persona desde carpeta padre (`12345 - APELLIDOS`) |
| `_extraer_fecha` | Fecha de aceptación del documento |

**Métodos auxiliares:**
`_necesita_ocr`, `_texto_via_ocr`, `_resolver_categoria`, `_resolver_sub_opcion1`, `_resolver_sub_opcion1_spans`, `_es_texto_no_percibido`, `_es_texto_si_percibido`, `_detectar_por_drawings`, `_mapear_y`, `_normalizar`, `_es_declaracion_quinta`, `_linea_marcada`, `_tiene_marca_antes`, `_tiene_marca_sub_opcion`, `_fragmento_tiene_marca`, `_ocr_documento_dni`, `_procesar_paralelo`, `_error`

---

### `procesador_ofertas.py` — 203 líneas

**Clase `ProcesadorOfertas`**

Responsabilidad: identificar cartas oferta en carpetas de personas, extraer texto, detectar beneficios y mover archivos a destino estandarizado.

| Atributo de clase | Descripción |
|-------------------|-------------|
| `KEYWORDS` | Dict de 3 términos (bono transporte, prestación alimentaria, asignación movilidad) con patrones regex |

| Método | Descripción |
|--------|-------------|
| `__init__(ruta_origen, ruta_destino)` | Configura rutas + inicializa Tesseract |
| `_init_tesseract()` | Busca Tesseract en rutas comunes de Windows |
| `_get_win_path(path)` | Prefijo `\\?\` para rutas largas en Windows |
| `_normalizar_texto(texto)` | Minúsculas + colapso de espacios |
| `_ocr_imagen_pil(img)` | OCR con Tesseract sobre imagen PIL |
| `_extraer_texto_ocr_pdf(file_path)` | Renderiza PDF → imagen → OCR página a página |
| `_extraer_texto_ocr_imagen(file_path)` | OCR directo sobre imagen |
| `es_carta_oferta(file_path)` | Heurística: `'carta' and 'oferta'` en nombre de archivo |
| `extraer_texto(file_path)` | Texto PDF nativo; fallback OCR si <60 caracteres |
| `triage_contenido(texto)` | Detecta beneficios adicionales con KEYWORDS; retorna `["Contrato Regular"]` si ninguno |
| `ejecutar()` | Escanea ruta_origen, identifica cartas, ejecuta triage, mueve a destino |

---

### `procesador_combinado.py` — 309 líneas

**Responsabilidad:** Orquestar ambos procesadores para generar la carpeta final `{DNI} - {NOMBRE}` con carta oferta + DJ quinta renombradas.

#### Funciones de módulo
| Función | Descripción |
|---------|-------------|
| `_cargar_overrides_categoria()` | Lee `categoria_overrides.json` |
| `_categoria_info_override(codigo)` | Retorna dict de info para categoría override |
| `_detectar_terminos_carta(texto)` | Detecta 3 términos de beneficios con regex |

**Constante `_TERMINOS_BENEFICIOS`:** Lista de 3 dicts `{id, label, patron}` para bono transporte, prestación alimentaria, asignación movilidad.

**Clase `ProcesadorCombinado`**

| Método | Descripción |
|--------|-------------|
| `__init__(ruta_origen, ruta_destino)` | Instancia ClasificadorQuinta + ProcesadorOfertas + carga overrides |
| `_get_win_path(path)` | Prefijo `\\?\` para Windows |
| `procesar_persona(folder_persona)` | Pipeline completo para una persona: 1) DNI de carpeta, 2) carta oferta, 3) DJ quinta, 4) fallback PRACT, 5) DNI desde DNI-doc, 6) override, 7) copia a destino |
| `ejecutar(max_workers=6, on_progress=None)` | ThreadPoolExecutor sobre todas las subcarpetas; llama callback `on_progress(curr, tot, res)` |

**Pipeline de `procesar_persona` (pasos ordenados):**
1. Extrae DNI del nombre de carpeta (`_extraer_dni_carpeta`)
2. Busca carta oferta por heurística de nombre → extrae texto + detecta términos + intenta extraer DNI
3. Busca DJ quinta en archivos restantes → clasifica, extrae DNI, detecta términos en DJ quinta también
4. Fallback: si hay "practicante" en carta oferta y no se clasificó quinta → categoría PRACT
5. Si aún no hay DNI → `identificar_dni_persona` (OCR de archivos dni/cui)
6. Último recurso → busca en todos los PDFs de la carpeta
7. Aplica override si el DNI o nombre de persona tiene entrada en `categoria_overrides.json`
8. Crea carpeta destino `{DNI} - {NOMBRE}`, copia carta oferta y DJ quinta renombradas

---

### `servidor_dj_quinta.py` — 755 líneas

**Responsabilidad:** Servidor Flask + manejo de rutas HTTP + generación de Excel.

**Objetos globales:**
- `app` = instancia Flask
- `clasificador` = instancia `ClasificadorQuinta()` (única, compartida entre requests)
- `_DUAL_TASKS` = dict en memoria de tareas en background

**Helper `_procesar_por_personas(subcarpetas)`:** Detecta carpetas por persona, procesa en paralelo con hasta 8 workers, enriquece resultados con datos del DNI verificado.

**Helper `_err_result(archivo, mensaje)`:** Factoría de resultados de error con estructura homogénea.

---

### `launcher.py` — 216 líneas

**Responsabilidad:** Script de arranque alternativo con diagnóstico interactivo.

| Función | Descripción |
|---------|-------------|
| `diagnostico()` | Verifica venv, servidor py, Python funcional, puerto 5010 libre |
| `iniciar_servidor()` | Lanza `pythonw.exe servidor_dj_quinta.py` como subproceso |
| `abrir_navegador()` | `webbrowser.open("http://localhost:5010")` |
| `main()` | Orquesta diagnóstico → iniciar → abrir navegador → wait for input |

**Clase `Color`:** Constantes ANSI para colores de terminal.

---

### `select_folder.py` — 16 líneas

Auxiliar Tkinter que se ejecuta como **proceso independiente** (no en el hilo de Flask) para abrir el diálogo nativo de selección de carpeta de Windows. Devuelve la ruta por stdout.

---

## 6. FLUJO DE DATOS DE INICIO A FIN

### Flujo 1 — Clasificación de carpeta con subcarpetas (caso más complejo)

```
Usuario                Browser              servidor_dj_quinta.py       clasificador_quinta.py
   │                     │                          │                           │
   ├─ Selecciona carpeta─►│                          │                           │
   │                     ├─ POST /select-folder ───►│                           │
   │                     │◄─ {path: "C:/..."} ──────┤                           │
   │                     ├─ POST /clasificar-carpeta►│                           │
   │                     │                          ├─ detecta subcarpetas       │
   │                     │                          ├─ _procesar_por_personas ──►│
   │                     │                          │                           ├─ ThreadPoolExecutor(8)
   │                     │                          │                           │  para cada carpeta:
   │                     │                          │                           ├─ _extraer_persona_carpeta
   │                     │                          │                           ├─ busca archivos soportados
   │                     │                          │                           ├─ identificar_dni_persona
   │                     │                          │                           │  └─ _ocr_documento_dni (shelve cache)
   │                     │                          │                           ├─ analizar_archivo(cada PDF)
   │                     │                          │                           │  └─ analizar_pdf:
   │                     │                          │                           │     1. _detectar_por_drawings
   │                     │                          │                           │     2. _detectar_formato_antiguo
   │                     │                          │                           │     3. _detectar_por_widgets
   │                     │                          │                           │     4. _detectar_por_texto
   │                     │                          │                           │     5. _detectar_por_spans
   │                     │                          │                           │     6. _detectar_por_keywords
   │                     │                          │◄─ lista de resultados ────┤
   │                     │                          ├─ generar_resumen          │
   │                     │◄─ {resultados, resumen} ─┤                           │
   ├◄─ Tabla categorías ─┤                          │                           │
   │                     │                          │                           │
   ├─ Descarga Excel ───►│                          │                           │
   │                     ├─ POST /exportar-excel ──►│                           │
   │                     │                          ├─ openpyxl workbook        │
   │                     │◄─ archivo .xlsx ─────────┤                           │
```

### Flujo 2 — Proceso Combinado (Cartas Oferta + Quinta)

```
Usuario  →  POST /api/v1/combinado/procesar  →  servidor
           {origen: "...", destino: "..."}

servidor  →  crea task_id  →  lanza Thread

Thread:
  ProcesadorCombinado.ejecutar()
    └── ThreadPoolExecutor(6)
         └── para cada subcarpeta:
              procesar_persona(folder)
                1. DNI desde nombre de carpeta
                2. es_carta_oferta() → extraer_texto() → triage_contenido()
                3. analizar_archivo() → detecta DJ quinta → extrae categoría
                4. fallback: "practicante" en carta → PRACT
                5. identificar_dni_persona() → OCR archivos dni/cui
                6. busca DNI en todos los PDFs
                7. aplica categoria_overrides.json
                8. shutil.copy2() → carpeta destino con nombres estandarizados

Browser  →  GET /api/v1/combinado/status/{task_id}  →  polling cada N segundos
           ← {status, current, total, resultados}
```

---

## 7. PUNTOS DE ENTRADA

| Punto de entrada | Cómo activarlo | Qué hace |
|-----------------|----------------|----------|
| `INICIAR.vbs` | Doble clic en Explorer | Verifica venv, libera puerto 5010, lanza `pythonw.exe servidor_dj_quinta.py`, abre browser |
| `launcher.py` | Doble clic en Explorer o `python launcher.py` | Diagnóstico + lanza servidor + abre browser |
| `python servidor_dj_quinta.py` | Terminal manual | Solo servidor, sin browser automático |
| `python clasificador_quinta.py <ruta>` | Terminal | Modo standalone CLI (sin Flask) |
| `python procesador_combinado.py <origen> <destino>` | Terminal | Ejecuta proceso combinado desde CLI |
| `INSTALAR.bat` | Doble clic | Crea venv + instala requirements |
| `DIAGNOSTICO.bat` | Doble clic | Verifica entorno sin iniciar servidor |

---

## 8. ARCHIVOS NO UTILIZADOS / REDUNDANTES

| Archivo | Estado | Detalle |
|---------|--------|---------|
| `.venv/` (carpeta) | **Huérfano** | Entorno virtual no referenciado por ningún script. `INICIAR.vbs` y `launcher.py` apuntan solo a `venv/`. Ocupa ~2,035 archivos sin propósito. |
| `_test_diag.py` | **Solo desarrollo** | Hardcodea ruta `c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA` — no funciona en otras PCs. |
| `_test_full.py` | **Solo desarrollo** | Rutas hardcodeadas a archivos específicos del equipo del desarrollador. |
| `_test_struct.py` | **Solo desarrollo** | Ídem. |
| `_test_texto.py` | **Solo desarrollo** | Ídem. |
| `FUNCIONALIDAD 2/C.txt` | **Notas de voz** | Fragmento de transcripción de voz del usuario con requisitos. No es código ni configuración. |
| `logs_iniciar.txt` | **Vacío** | Archivo de log presente pero con contenido mínimo (solo header). |
| `Reporte_Cartas_Oferta.xlsx` | **Artefacto de ejecución** | Último reporte generado, sobreescrito en cada exportación. |
| `cache_ocr_dni` | **Caché activa** | Archivo shelve con resultados OCR. No es huérfano, pero no debe migrarse entre PCs sin limpiar. |

---

## 9. DEUDA TÉCNICA

### Crítica
| # | Problema | Archivo | Impacto |
|---|----------|---------|---------|
| DT-01 | **Dos entornos virtuales (`venv/` y `.venv/`) coexisten** | raíz | Confusión en mantenimiento. Si alguien instala deps en `.venv/` el sistema no las ve. |
| DT-02 | **Estado de tareas en memoria (`_DUAL_TASKS`)** | `servidor_dj_quinta.py:59` | Si el servidor se reinicia durante un proceso largo, el cliente queda en polling infinito sin respuesta. No hay timeout ni limpieza de tareas viejas. |
| DT-03 | **Google Vision referenciado pero nunca activado en producción** | `clasificador_quinta.py:129-156` | Código presente que requiere credenciales GCP no documentadas. Puede generar errores silenciosos si alguien configura `GOOGLE_APPLICATION_CREDENTIALS` por error. |

### Alta
| # | Problema | Archivo | Impacto |
|---|----------|---------|---------|
| DT-04 | **Scripts de prueba con rutas hardcodeadas al PC del desarrollador** | `_test_*.py` | Fallan en cualquier otra PC sin modificación. |
| DT-05 | **`FUNCIONALIDAD 2/DESTINO/` contiene carpetas duplicadas** (`72622524 - RAMIREZ...` y `72622524 - 72622524 - RAMIREZ...`) | `FUNCIONALIDAD 2/DESTINO/` | Indica que el proceso combinado generó carpetas dobles en alguna ejecución. Posible bug en la lógica de creación de nombre destino. |
| DT-06 | **`procesador_ofertas.py::ejecutar()` usa `shutil.move()`** | `procesador_ofertas.py:177` | A diferencia de `procesador_combinado` que usa `shutil.copy2()`, este método **mueve** (destructivo). Si hay error a mitad del proceso, los archivos origen ya no existen. |
| DT-07 | **Sin límite de crecimiento de `_DUAL_TASKS`** | `servidor_dj_quinta.py:59` | Cada llamada a `/combinado/procesar` agrega una entrada que nunca se elimina. En uso intensivo, memoria crece sin límite. |

### Media
| # | Problema | Archivo | Impacto |
|---|----------|---------|---------|
| DT-08 | **La detección de carta oferta es solo por nombre** (`es_carta_oferta`) | `procesador_ofertas.py:110-113` | Heurística frágil: busca `'carta' and 'oferta'` en nombre de archivo. Archivos como `doc_contrato_de_oferta.pdf` o cartas con nombres distintos no son detectadas. |
| DT-09 | **Sin autenticación / CSRF** | `servidor_dj_quinta.py` | Servidor localhost sin protección. No crítico en entorno empresarial controlado pero cualquier proceso local puede hacer POST a las APIs. |
| DT-10 | **`uploads_quinta/` no tiene limpieza automática** | `servidor_dj_quinta.py:52` | Archivos subidos vía browser se acumulan indefinidamente (solo la ruta `api_clasificar_ofertas` borra después de procesar). |
| DT-11 | **La caché OCR (`cache_ocr_dni`) no tiene TTL ni invalidación** | `clasificador_quinta.py:57-89` | Si un archivo se reemplaza por uno diferente con el mismo nombre, la caché puede servir datos obsoletos (aunque usa MD5 del contenido, no solo nombre — mitigado). |
| DT-12 | **Codificación UTF-8 de `FUNCIONALIDAD 2/C.txt` corrupta** | `FUNCIONALIDAD 2/C.txt` | Texto con caracteres mojibake (`â€™`, `Ã³`, etc.) — guardado en Windows-1252 pero leído como UTF-8. |

### Baja
| # | Problema | Archivo | Impacto |
|---|----------|---------|---------|
| DT-13 | **`_test_full.py` y `_test_texto.py` tienen rutas de archivos que ya no existen** | `_test_*.py` | Scripts de diagnóstico que fallan silenciosamente con archivos de prueba que ya no están en las rutas hardcodeadas. |
| DT-14 | **`README.md` menciona `INICIAR.vbs` → `INICIAR.bat`** (inconsistencia de nombre) | `README.md:87` | Guía de troubleshooting menciona `INSTALAR.vbs` que no existe; el archivo correcto es `INICIAR.vbs`. |
| DT-15 | **`select_folder.py` importa tkinter sin fallback** | `select_folder.py` | En entornos sin display (servidor headless), el proceso hijo cuelga o falla sin error claro. |

---

## 10. RIESGOS DE MANTENIMIENTO

| Riesgo | Probabilidad | Impacto | Descripción |
|--------|-------------|---------|-------------|
| **Cambio de formato del formulario DJ Quinta** | Alta | Alto | La lógica de detección depende de coordenadas Y fijas (`CHECKBOX_Y_STD/OLD/WIDE`) y patrones de texto específicos. Si SUNAT cambia el formato del formulario, los métodos 1 y 1b dejan de funcionar. Los métodos 2–4 son más robustos. |
| **Actualización de Tesseract** | Media | Medio | El código usa PSM modes específicos (`--psm 6`, `--psm 4`). Versiones futuras de Tesseract pueden cambiar el comportamiento por defecto. |
| **Credenciales GCP Vision** | Baja | Bajo | Si se habilita Google Vision, requiere gestión de credenciales y facturación. Sin documentación de configuración. |
| **Rutas de colaboradores con nombres muy largos** | Media | Bajo | Windows limita rutas a 260 caracteres. El sistema mitiga esto con prefijo `\\?\` en `_get_win_path()`, pero solo en `procesador_combinado.py` y `procesador_ofertas.py`. `clasificador_quinta.py` no siempre usa este prefijo. |
| **Archivos PDF con codificación inusual** | Media | Medio | PyMuPDF puede fallar con PDFs cifrados, dañados o generados con herramientas no estándar. El manejo de errores captura la excepción pero puede producir falsos negativos silenciosos. |
| **Escala del conjunto de datos** | Baja | Medio | El sistema no tiene paginación ni límites de resultado en la UI. Con >500 personas en una carpeta, la respuesta HTTP puede superar los límites del navegador. |
| **Dependencia de `venv/` en la ruta de instalación** | Alta | Alto | Los scripts esperan `{dir}\venv\Scripts\pythonw.exe`. Si el usuario mueve o renombra la carpeta raíz, el sistema deja de funcionar y requiere reinstalación. |

---

## RESUMEN EJECUTIVO

El Sistema de Administración Personal es un **sistema de automatización documental** de complejidad media-alta, enfocado en un problema muy específico: clasificar automáticamente las declaraciones juradas de quinta categoría de los colaboradores y consolidar sus documentos de ingreso.

**Fortalezas técnicas:**
- Motor de clasificación robusto con 6 métodos en cascada + fallback OCR
- Procesamiento paralelo efectivo (ThreadPoolExecutor, hasta 8 workers)
- Caché de OCR por hash MD5 que elimina reprocesamiento en re-ejecuciones
- Portabilidad: todas las rutas son relativas, venv local por PC
- Override manual vía JSON para casos excepcionales

**Mayores preocupaciones:**
- El doble entorno virtual (`.venv/` huérfano) es la deuda más inmediata a resolver
- Las carpetas duplicadas en `FUNCIONALIDAD 2/DESTINO/` sugieren un bug en producción no resuelto
- El proceso de Cartas Oferta (`procesador_ofertas::ejecutar`) usa `shutil.move` (destructivo), a diferencia del combinado que usa `copy2`
- No hay persistencia de estado para tareas en background — un restart pierde el progreso

**Línea de código total estimada:** ~3,128 líneas (excluyendo venv, HTML y scripts de prueba)

---

*Documento generado automáticamente mediante análisis estático del repositorio.*
*Revisar contra código fuente ante cualquier discrepancia.*

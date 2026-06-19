# API Reference — Sistema DJ Quinta Categoría
**People Analytics · USIL**
**Documento:** API_REFERENCE.md · v1.0 · 2026-06-01
**Base URL:** `http://localhost:5010`

---

## Convenciones

- Todos los endpoints que reciben JSON esperan `Content-Type: application/json`
- Los endpoints de upload esperan `Content-Type: multipart/form-data`
- Todos los endpoints retornan `Content-Type: application/json` salvo los de descarga de archivos
- El campo `status` en la respuesta es siempre `"OK"` o `"ERROR"`
- El campo `status` en cada resultado individual puede ser `"OK"`, `"WARNING"` o `"ERROR"`

### Esquema del objeto Resultado Individual

```jsonc
{
  "status":         "OK | WARNING | ERROR",
  "archivo":        "nombre_del_archivo.pdf",
  "nombre":         "GARCIA LOPEZ JOSE",          // extraído del documento
  "persona":        "GARCIA LOPEZ JOSE",          // extraído del nombre de carpeta
  "dni":            "12345678",                   // null si no se encontró
  "categoria":      "1A | 1B | 2 | 3 | null",
  "categoria_info": {
    "codigo":       "1A",
    "nombre":       "Único Empleador - Con renta quinta previa",
    "descripcion":  "USIL es su único empleador. SÍ percibió renta de quinta...",
    "color":        "#2196F3"
  },
  "confianza":      95,                           // 0-100
  "metodo":         "drawings+texto",             // técnica de detección usada
  "mensaje":        "Categoría 1A: Único Empleador - Con renta quinta previa"
}
```

### Esquema del objeto Resumen

```jsonc
{
  "total_procesados": 10,
  "exitosos":         8,
  "errores":          1,
  "sin_clasificar":   1,
  "categorias": {
    "1A": 3,
    "1B": 4,
    "2":  1,
    "3":  0
  },
  "detalle_categorias": {
    "1A": {"cantidad": 3, "info": {...}},
    "1B": {"cantidad": 4, "info": {...}},
    "2":  {"cantidad": 1, "info": {...}},
    "3":  {"cantidad": 0, "info": {...}}
  }
}
```

---

## Sección 1: Interfaz de Usuario

### `GET /`
**Alias:** `GET /quinta`

Retorna la SPA completa (Single Page Application).

**Respuesta:** `text/html` — contenido de `templates/quinta_categoria.html`

---

## Sección 2: API de Clasificación DJ Quinta

### `POST /api/v1/quinta/clasificar`

Recibe archivos subidos desde el navegador (drag & drop o selector). Los archivos se guardan temporalmente en `uploads_quinta/`.

**Formato de request:** `multipart/form-data`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `files` | file[] | Uno o más archivos PDF, JPG, PNG, TIFF, etc. |

**Extensiones aceptadas:** `.pdf`, `.jpg`, `.jpeg`, `.png`, `.jfif`, `.bmp`, `.tiff`, `.tif`, `.gif`, `.webp`

**Respuesta exitosa (200):**
```json
{
  "status": "OK",
  "resultados": [ ... ],
  "resumen": { ... }
}
```

**Errores:**
```json
// Sin archivos enviados
{ "status": "ERROR", "message": "Sin archivos" }                   // 400

// Ningún archivo con extensión válida
{ "status": "ERROR", "message": "No se encontraron archivos válidos. Formatos soportados: ..." }  // 400
```

---

### `POST /api/v1/quinta/clasificar-rutas`

Clasifica archivos especificados por rutas absolutas locales en el servidor.

**Request JSON:**
```json
{
  "rutas": [
    "C:/Documentos/persona1/declaracion.pdf",
    "C:/Documentos/persona2/",
    "C:/Documentos/foto_quinta.jpg"
  ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `rutas` | string[] | Lista de rutas absolutas (archivos o carpetas) |

> Si una ruta es una **carpeta**, se escanean todos los archivos soportados directamente dentro de ella (no recursivo).
> Si una ruta es un **archivo** con extensión soportada, se procesa directamente.

**Respuesta exitosa (200):**
```json
{
  "status": "OK",
  "resultados": [ ... ],
  "resumen": { ... }
}
```

**Errores:**
```json
{ "status": "ERROR", "message": "Se requiere campo \"rutas\"" }    // 400
{ "status": "ERROR", "message": "\"rutas\" debe ser lista no vacía" }  // 400
```

> Las rutas inválidas no generan error HTTP — se incluyen como resultados individuales con `status: "ERROR"`.

---

### `POST /api/v1/quinta/clasificar-carpeta`

Escanea una carpeta raíz. Si tiene subcarpetas, las trata como carpetas-persona y reporta también las personas sin declaración. Si no tiene subcarpetas, procesa todos los archivos directamente.

**Request JSON:**
```json
{
  "carpeta": "C:/DOCUMENTOS/COLABORADORES 2026"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `carpeta` | string | Ruta absoluta a la carpeta raíz |

**Respuesta exitosa — con subcarpetas (200):**
```json
{
  "status": "OK",
  "resultados": [ ... ],
  "resumen": { ... },
  "total_personas": 25
}
```

**Respuesta exitosa — sin subcarpetas (200):**
```json
{
  "status": "OK",
  "resultados": [ ... ],
  "resumen": { ... },
  "total_personas": 12
}
```

**Errores:**
```json
{ "status": "ERROR", "message": "Se requiere campo \"carpeta\"" }  // 400
{ "status": "ERROR", "message": "Carpeta no encontrada: ..." }     // 404
{ "status": "ERROR", "message": "La ruta no es una carpeta: ..." } // 400
```

---

### `POST /api/v1/quinta/exportar-excel`

Genera y descarga un archivo `.xlsx` formateado con los resultados de clasificación.

**Request JSON:**
```json
{
  "resultados": [ ... ],
  "resumen": { ... }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `resultados` | array | Lista de objetos resultado (obtenidos de los endpoints anteriores) |
| `resumen` | object | Objeto resumen (opcional — se usa para la hoja "Resumen") |

**Respuesta exitosa (200):**
`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
`Content-Disposition: attachment; filename=clasificacion_quinta_YYYYMMDD_HHMMSS.xlsx`

Cuerpo: stream binario del archivo Excel.

**Estructura del Excel generado:**

**Hoja 1: "Clasificacion DJ Quinta"**
- Fila 1: Título con fondo azul oscuro
- Fila 2: Timestamp de generación
- Fila 4: Encabezados (N°, Persona (Carpeta), DNI (Declaración), Nombre (Declaración), Cat., Descripción Categoría)
- Filas 5+: Datos con filas alternadas en blanco/azul muy claro
- Celda "Cat.": fondo de color según categoría (azul=1A, verde=1B, naranja=2, rojo=3)
- Filtros automáticos activados

**Hoja 2: "Resumen"**
- Total Procesados, Clasificados OK, Sin Clasificar, Errores
- Conteo por categoría (1A, 1B, 2, 3)

**Error:**
```json
{ "status": "ERROR", "message": "Sin datos para exportar" }   // 400
```

---

## Sección 3: API de Cartas Oferta

### `POST /api/v1/ofertas/procesar`

Procesa cartas oferta desde una carpeta de personas (origen) hacia una carpeta destino. **Mueve** (no copia) los archivos.

> **ATENCIÓN:** Esta operación es destructiva. Los archivos se eliminan de la carpeta origen.

**Request JSON:**
```json
{
  "origen":  "C:/Ingresos/Pendientes",
  "destino": "C:/Ingresos/Cartas Procesadas"
}
```

**Respuesta exitosa (200):**
```json
{
  "status": "OK",
  "resultados": [
    {
      "uuid":           "DOC-A3F8",
      "persona":        "GARCIA LOPEZ JOSE",
      "archivo_origen": "Carta Oferta JOSE.pdf",
      "hallazgos":      ["Bono de Transporte", "Prestación Alimentaria"],
      "ruta_destino":   "C:/Ingresos/Cartas Procesadas",
      "archivo_final":  "Carta Oferta - GARCIA LOPEZ JOSE.pdf",
      "estado":         "MOVIDO_OK",
      "timestamp":      "14:32:55"
    }
  ]
}
```

**Posibles estados por resultado:**

| Estado | Descripción |
|--------|-------------|
| `MOVIDO_OK` | Carta encontrada, analizada y movida exitosamente |
| `ERROR_MOVER` | Se encontró la carta pero hubo error al moverla |

> Las personas sin carta oferta no generan entrada en `resultados`.

**Error:**
```json
{ "status": "ERROR", "message": "Rutas origen y destino requeridas" }  // 400
{ "status": "ERROR", "message": "Ruta origen no existe: ..." }          // 200 (dentro del body)
```

---

### `POST /api/v1/ofertas/clasificar`

Analiza cartas oferta subidas directamente desde el navegador. **No mueve archivos.**

**Formato de request:** `multipart/form-data`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `files` | file[] | Archivos PDF de cartas oferta |

**Respuesta exitosa (200):**
```json
{
  "status": "OK",
  "resultados": [
    {
      "persona":        "Carga Directa",
      "archivo_origen": "Carta_Oferta_Jose.pdf",
      "hallazgos":      ["Bono de Transporte"],
      "estado":         "PROCESADO_RAM",
      "timestamp":      "14:32:55"
    }
  ]
}
```

---

### `POST /api/v1/ofertas/procesar-rutas`

Analiza cartas oferta por rutas locales. **No mueve archivos.**

**Request JSON:**
```json
{
  "rutas": [
    "C:/Docs/Carta Oferta Garcia.pdf",
    "C:/Docs/Carta Oferta Rodriguez.pdf"
  ]
}
```

**Respuesta exitosa (200):**
```json
{
  "status": "OK",
  "resultados": [
    {
      "persona":        "Ruta Manual",
      "archivo_origen": "Carta Oferta Garcia.pdf",
      "hallazgos":      ["Contrato Regular"],
      "ruta_destino":   "C:/Docs",
      "estado":         "PROCESADO_LOCAL",
      "timestamp":      "14:32:55"
    }
  ]
}
```

---

### `POST /api/v1/ofertas/exportar-excel`

Genera y descarga un reporte Excel de cartas oferta procesadas. Guarda el archivo como `Reporte_Cartas_Oferta.xlsx` en el directorio del servidor y lo entrega como descarga.

**Request JSON:**
```json
{
  "resultados": [ ... ]
}
```

**Respuesta exitosa (200):**
`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

**Columnas del Excel:** UUID, Archivo Origen, Hallazgos Triage, Persona/Ruta, Estado, Fecha/Hora

---

## Sección 4: API del Proceso Combinado

El proceso combinado opera de forma asíncrona. El cliente inicia la tarea y luego consulta el estado periódicamente (polling).

### `POST /api/v1/combinado/procesar`

Inicia el proceso combinado en segundo plano.

**Request JSON:**
```json
{
  "origen":  "C:/Ingresos/Por Procesar",
  "destino": "C:/Ingresos/Procesados"
}
```

**Respuesta exitosa (200):**
```json
{
  "status":  "OK",
  "task_id": "TASK-143255-A3F8"
}
```

**El `task_id`** tiene formato `TASK-{HHMMSS}-{4hexchars}`.

**Errores:**
```json
{ "status": "ERROR", "message": "Rutas origen y destino requeridas" }  // 400
```

> La validación de existencia de la carpeta origen ocurre **dentro del hilo** — puede retornar `ERROR` en el estado de la tarea, no en la respuesta HTTP.

---

### `GET /api/v1/combinado/status/{task_id}`

Consulta el estado de una tarea en ejecución.

**Parámetros de URL:**

| Parámetro | Descripción |
|-----------|-------------|
| `task_id` | ID de tarea retornado por `/combinado/procesar` |

**Respuesta — en ejecución (200):**
```json
{
  "status":     "RUNNING",
  "current":    5,
  "total":      25,
  "resultados": [
    {
      "persona":         "GARCIA LOPEZ JOSE",
      "dni":             "12345678",
      "carta_oferta":    "Carta Oferta.pdf",
      "dj_quinta":       "DJ Quinta firmada.pdf",
      "categoria":       "1B",
      "categoria_info":  { ... },
      "confianza_quinta": 92,
      "terminos_carta":  ["Bono de Transporte"],
      "estado":          "PROCESADO_OK",
      "ruta_destino":    "C:/Ingresos/Procesados/12345678 - GARCIA LOPEZ JOSE",
      "mensaje":         ""
    }
  ],
  "start_time": "2026-06-01T14:30:00",
  "end_time":   null,
  "message":    "Procesando 5/25"
}
```

**Respuesta — completado (200):**
```json
{
  "status":     "COMPLETED",
  "current":    25,
  "total":      25,
  "resultados": [ ... ],
  "start_time": "2026-06-01T14:30:00",
  "end_time":   "2026-06-01T14:32:15",
  "message":    "Completado con éxito"
}
```

**Respuesta — error (200):**
```json
{
  "status":    "ERROR",
  "message":   "FileNotFoundError: Carpeta origen no encontrada: ...",
  "traceback": "Traceback (most recent call last):\n  File ..."
}
```

**Posibles valores de `status`:**

| Valor | Descripción |
|-------|-------------|
| `RUNNING` | Procesando — continuar polling |
| `COMPLETED` | Finalizado exitosamente |
| `ERROR` | Error fatal en la tarea |

**Posibles valores de `estado` por resultado individual:**

| Valor | Descripción |
|-------|-------------|
| `PROCESADO_OK` | Documentos encontrados y copiados |
| `NO_ENCONTRADO` | No se encontró carta ni DJ quinta |
| `ERROR_COPIA` | Error al copiar los archivos al destino |
| `EXCEPTION` | Excepción no controlada en esa persona |

**Error:**
```json
{ "status": "ERROR", "message": "Tarea no encontrada" }   // 404
```

> **Patrón de polling recomendado:** consultar cada 1-2 segundos mientras `status == "RUNNING"`.

---

## Sección 5: Utilidades

### `POST /api/v1/utils/select-folder`

Abre el diálogo nativo de selección de carpeta de Windows. Solo funciona en Windows con sesión de usuario activa.

**Request:** Body vacío o `{}`

**Respuesta — carpeta seleccionada (200):**
```json
{
  "status": "OK",
  "path":   "C:\\Users\\Analista\\Documentos\\Ingresos 2026"
}
```

**Respuesta — cancelado (200):**
```json
{
  "status":  "CANCEL",
  "message": "Selección cancelada"
}
```

**Error (500):**
```json
{
  "status":  "ERROR",
  "message": "descripción del error"
}
```

> Internamente lanza `select_folder.py` como subproceso independiente para evitar conflictos de hilos entre Tkinter y Flask.

---

### `POST /api/v1/utils/open-folder`

Abre una carpeta en el Explorador de Windows (o Finder en macOS, xdg-open en Linux).

**Request JSON:**
```json
{
  "path": "C:/Ingresos/Procesados/12345678 - GARCIA LOPEZ JOSE"
}
```

**Respuesta exitosa (200):**
```json
{ "status": "OK" }
```

**Error:**
```json
{ "status": "ERROR", "message": "Ruta no válida" }   // 400
```

---

### `POST /api/v1/quinta/reiniciar`

Reinicia el servidor Flask. El proceso actual lanza un nuevo proceso Python y luego se termina a sí mismo.

> **Advertencia:** Las tareas en `_DUAL_TASKS` se pierden. Las conexiones activas del navegador se cortan. El cliente debe refrescar la página manualmente.

**Request:** Body vacío

**Respuesta (200):**
```json
{
  "status":  "OK",
  "message": "Reiniciando..."
}
```

> La respuesta se retorna antes de que el servidor se detenga (implementado con un hilo con `sleep(0.5)`).

---

## Apéndice: Códigos HTTP utilizados

| Código | Descripción | Cuándo ocurre |
|--------|-------------|--------------|
| `200` | OK | Operación exitosa (incluye resultados con `status: "ERROR"` individuales) |
| `400` | Bad Request | Falta un parámetro requerido o tipo incorrecto |
| `404` | Not Found | Carpeta no existe (clasificar-carpeta) o tarea no encontrada (status) |
| `500` | Internal Server Error | Error inesperado del servidor (raro — la mayoría se captura internamente) |

---

## Apéndice: Métodos de detección reportados en `metodo`

| Valor | Técnica |
|-------|---------|
| `drawings` | Checkboxes gráficos (rectángulos + líneas) |
| `drawings+texto` | Drawings + texto para sub-opción 1A/1B |
| `fmt_antiguo` | Formato antiguo: "X" texto + posición Y relativa |
| `widgets` | Widgets de formulario PDF |
| `texto_-X` | Marcas `-X`, `[X]`, `(X)` en texto |
| `spans_bold` | Spans con fuente Bold y texto "X" |
| `keywords` | Palabras clave con contexto |
| `keywords_struct` | Estructura del documento + proximidad de marcas |
| `checkbox_directo` | Checkbox detectado con variantes OCR (h&X], etc.) |
| `*+OCR` | Cualquier método + fallback OCR (PDF escaneado) |
| `*+OCR_IMG_0°` | Método + OCR sobre imagen sin rotar |
| `*+GoogleVision` | Método + Google Cloud Vision OCR |
| `error` | Error de procesamiento |
| `escaneado_sin_ocr` | PDF escaneado pero Tesseract no disponible |
| `no_es_quinta` | Ningún archivo de la carpeta era DJ quinta |
| `sin_archivo` | Carpeta vacía o sin archivos soportados |

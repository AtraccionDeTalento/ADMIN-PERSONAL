# Arquitectura del Sistema — DJ Quinta Categoría
**People Analytics · USIL**
**Documento:** ARQUITECTURA.md · v1.0 · 2026-06-01

---

## 1. Visión General

El sistema sigue una arquitectura de **aplicación web local de capa única** (monolito liviano), donde un servidor Flask actúa como hub central que:
- Sirve la interfaz de usuario (Single Page Application estática)
- Expone una API REST interna consumida por esa misma SPA
- Orquesta módulos de negocio especializados en análisis documental

No existe base de datos relacional, ni autenticación, ni conexión a servicios externos (salvo la integración opcional con Google Cloud Vision, inactiva por defecto). Todo opera en `localhost`.

```
┌────────────────────────────────────────────────────────────────────┐
│                        MÁQUINA DEL USUARIO                        │
│                                                                    │
│  ┌──────────────┐     HTTP :5010      ┌───────────────────────┐   │
│  │   Navegador  │ ◄──────────────────► │  Flask (servidor_dj_  │   │
│  │   (Chrome /  │                      │  quinta.py)           │   │
│  │   Edge / FF) │                      │                       │   │
│  └──────────────┘                      │  ┌─────────────────┐  │   │
│                                        │  │  clasificador_  │  │   │
│  ┌──────────────┐                      │  │  quinta.py      │  │   │
│  │  INICIAR.vbs │──► pythonw.exe ─────►│  └─────────────────┘  │   │
│  │  launcher.py │                      │  ┌─────────────────┐  │   │
│  └──────────────┘                      │  │  procesador_    │  │   │
│                                        │  │  combinado.py   │  │   │
│  ┌──────────────┐                      │  └─────────────────┘  │   │
│  │  select_     │◄── subprocess ───────│  ┌─────────────────┐  │   │
│  │  folder.py   │                      │  │  procesador_    │  │   │
│  └──────────────┘                      │  │  ofertas.py     │  │   │
│                                        │  └─────────────────┘  │   │
│  ┌──────────────┐                      └───────────────────────┘   │
│  │  Sistema de  │◄── shelve / shutil / fitz / pytesseract          │
│  │  archivos    │                                                   │
│  └──────────────┘                                                   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Modelo de Capas

```mermaid
graph TD
    subgraph "Capa de Presentación"
        UI[quinta_categoria.html\nSPA — 92 KB\nHTML + CSS + JS vanilla]
    end

    subgraph "Capa de Arranque"
        VBS[INICIAR.vbs\nSilencioso]
        LPY[launcher.py\nDiagnóstico]
        INST[INSTALAR.bat\nSetup]
        DIAG[DIAGNOSTICO.bat\nVerificación]
    end

    subgraph "Capa Web — Flask :5010"
        SRV[servidor_dj_quinta.py\n755 líneas\n14 rutas HTTP]
    end

    subgraph "Capa de Negocio"
        CLF[clasificador_quinta.py\n1845 líneas\nClasificadorQuinta]
        PRO[procesador_ofertas.py\n203 líneas\nProcesadorOfertas]
        CMB[procesador_combinado.py\n309 líneas\nProcesadorCombinado]
        SEL[select_folder.py\n16 líneas\nTkinter helper]
    end

    subgraph "Capa de Datos"
        PDF[(Archivos PDF\ne imágenes)]
        OVR[(categoria_overrides\n.json)]
        CACHE[(cache_ocr_dni\nShelve MD5)]
        UPL[(uploads_quinta/\narchivos temporales)]
        DST[(FUNCIONALIDAD 2/\nDESTINO/)]
    end

    subgraph "Dependencias Externas"
        TESS[Tesseract OCR\nopcional]
        GCV[Google Vision API\nopcional — inactivo]
    end

    VBS --> SRV
    LPY --> SRV
    UI <-->|HTTP REST| SRV
    SRV --> CLF
    SRV --> PRO
    SRV --> CMB
    SRV -->|subprocess| SEL
    CMB --> CLF
    CMB --> PRO
    CLF <--> CACHE
    CLF --> PDF
    CLF -->|pytesseract| TESS
    CLF -.->|opcional| GCV
    PRO --> PDF
    CMB --> DST
    SRV --> UPL
    CMB --> OVR
```

---

## 3. Diagrama de Componentes

```mermaid
graph LR
    subgraph "servidor_dj_quinta.py"
        R1["/\n/quinta\nGET"]
        R2["/api/v1/quinta/clasificar\nPOST"]
        R3["/api/v1/quinta/clasificar-rutas\nPOST"]
        R4["/api/v1/quinta/clasificar-carpeta\nPOST"]
        R5["/api/v1/quinta/exportar-excel\nPOST"]
        R6["/api/v1/ofertas/procesar\nPOST"]
        R7["/api/v1/ofertas/clasificar\nPOST"]
        R8["/api/v1/ofertas/procesar-rutas\nPOST"]
        R9["/api/v1/ofertas/exportar-excel\nPOST"]
        R10["/api/v1/combinado/procesar\nPOST"]
        R11["/api/v1/combinado/status/{id}\nGET"]
        R12["/api/v1/utils/select-folder\nPOST"]
        R13["/api/v1/utils/open-folder\nPOST"]
        R14["/api/v1/quinta/reiniciar\nPOST"]
        TASKS[_DUAL_TASKS\nDict en memoria]
    end

    subgraph "clasificador_quinta.py"
        CLS[ClasificadorQuinta]
        M1[analizar_archivo]
        M2[analizar_pdf]
        M3[analizar_imagen]
        M4[_procesar_paralelo\nThreadPoolExecutor]
        M5[identificar_dni_persona]
        M6[generar_resumen]
    end

    subgraph "procesador_combinado.py"
        PCB[ProcesadorCombinado]
        PC1[procesar_persona]
        PC2[ejecutar\nmax_workers=6]
    end

    subgraph "procesador_ofertas.py"
        POF[ProcesadorOfertas]
        PO1[es_carta_oferta]
        PO2[extraer_texto]
        PO3[triage_contenido]
        PO4[ejecutar]
    end

    R2 --> M4
    R3 --> M4
    R4 --> CLS
    R5 -->|openpyxl| xlsx[.xlsx]
    R6 --> POF
    R10 --> PCB
    R11 --> TASKS
    PCB --> CLS
    PCB --> POF
```

---

## 4. Modelo de Concurrencia

El sistema usa **hilos de Python** (`threading.Thread` + `ThreadPoolExecutor`) para el paralelismo de I/O-bound (lectura de PDFs, OCR con Tesseract). Tesseract libera el GIL de Python durante el procesamiento, por lo que el paralelismo real es efectivo.

```mermaid
sequenceDiagram
    participant Browser
    participant Flask
    participant TPE as ThreadPoolExecutor
    participant W1 as Worker-1
    participant W2 as Worker-2
    participant W8 as Worker-N (≤8)

    Browser->>Flask: POST /clasificar-carpeta\n{carpeta: "C:/..."}
    Flask->>Flask: detecta N subcarpetas
    Flask->>TPE: _procesar_por_personas(subcarpetas)\nmax_workers = min(8, N)
    TPE->>W1: analizar carpeta-persona-1
    TPE->>W2: analizar carpeta-persona-2
    TPE->>W8: analizar carpeta-persona-N
    W1-->>TPE: resultado-1
    W2-->>TPE: resultado-2
    W8-->>TPE: resultado-N
    TPE-->>Flask: lista[resultados]
    Flask->>Flask: generar_resumen(resultados)
    Flask-->>Browser: {status:"OK", resultados:[], resumen:{}}
```

**Tarea de larga duración (proceso combinado):**

```mermaid
sequenceDiagram
    participant Browser
    participant Flask
    participant Thread as BackgroundThread
    participant TPE as ThreadPoolExecutor(6)

    Browser->>Flask: POST /combinado/procesar\n{origen, destino}
    Flask->>Flask: genera task_id\n_DUAL_TASKS[task_id] = {status: RUNNING}
    Flask->>Thread: Thread(target=_run).start()
    Flask-->>Browser: {status:"OK", task_id:"TASK-..."}

    loop Polling cada ~2 segundos
        Browser->>Flask: GET /combinado/status/{task_id}
        Flask-->>Browser: {status, current, total, resultados}
    end

    Thread->>TPE: ProcesadorCombinado.ejecutar()
    TPE-->>Thread: resultados completos
    Thread->>Flask: _DUAL_TASKS[task_id]["status"] = "COMPLETED"

    Browser->>Flask: GET /combinado/status/{task_id}
    Flask-->>Browser: {status:"COMPLETED", resultados:[...]}
```

---

## 5. Pipeline de Clasificación PDF

Para cada archivo PDF, se ejecutan hasta 6 métodos de detección en cascada. El primero que produce un resultado con confianza suficiente corta la ejecución.

```mermaid
flowchart TD
    A[archivo PDF] --> B{¿nombre indica\nno-quinta?}
    B -->|sí| ERR1[ERROR: omitido]
    B -->|no| C[fitz.open + get_text]
    C --> D{¿texto nativo\n< 120 chars?}
    D -->|sí — escaneado| E[OCR vía Tesseract\n_texto_via_ocr]
    D -->|no| F{¿es declaración\nde quinta?}
    E --> F
    F -->|no| ERR2[ERROR: no es quinta]
    F -->|sí| G[Método 1: Drawings\ncheckboxes gráficos]
    G -->|categoría encontrada| OK[resultado OK]
    G -->|no encontrado| H[Método 1b: Formato Antiguo\nX texto + posición Y]
    H -->|categoría encontrada| OK
    H -->|no encontrado| I[Método 1c: Widgets PDF\nform fields]
    I -->|categoría encontrada| OK
    I -->|no encontrado| J[Método 2: Texto -X\nmarcas en texto plano]
    J -->|categoría encontrada| OK
    J -->|no encontrado| K[Método 3: Spans Bold\nsolo PDFs nativos]
    K -->|categoría encontrada| OK
    K -->|no encontrado| L[Método 4: Keywords\ncontexto + regex]
    L -->|categoría encontrada| OK
    L -->|no encontrado| WARN[WARNING: revisar manualmente]

    OK --> M{¿es opción 1?}
    M -->|sí| N{sub-opción\nSí/No percibió}
    N -->|Sí percibió| CAT1A[Categoría 1A]
    N -->|No percibió| CAT1B[Categoría 1B]
    M -->|opción 2| CAT2[Categoría 2]
    M -->|opción 3| CAT3[Categoría 3]
```

---

## 6. Pipeline del Proceso Combinado

```mermaid
flowchart TD
    START([carpeta origen\ncon subcarpetas]) --> ITER[itera sobre N subcarpetas\nThreadPoolExecutor 6 workers]
    ITER --> P1

    subgraph "procesar_persona — por carpeta"
        P1[1. DNI desde nombre de carpeta\nej: 12345678 - NOMBRE] --> P2
        P2[2. Busca carta oferta\npor nombre: carta + oferta] --> P3
        P3{¿carta\nencontrada?} -->|sí| P3A[extrae texto PDF\ntriage de beneficios\nintenta extraer DNI]
        P3 -->|no| P4
        P3A --> P4
        P4[3. Busca DJ quinta\nen archivos restantes] --> P5
        P5{¿quinta\nclasificada?} -->|sí| P5A[registra categoría\nextrae DNI]
        P5 -->|no| P6
        P5A --> P6
        P6[4. Fallback practicante\nsi carta menciona practicante] --> P7
        P7{¿DNI\nobtenido?} -->|no| P7A[5. OCR en archivos dni/cui\nidentificar_dni_persona]
        P7 -->|sí| P8
        P7A --> P8
        P8{¿DNI aún\nnulo?} -->|sí| P8A[6. Busca DNI en\ntodos los PDFs]
        P8 -->|no| P9
        P8A --> P9
        P9[7. Aplica overrides\ncategoria_overrides.json] --> P10
        P10{¿documentos\nencontrados?} -->|sí| P10A[8. Crea carpeta DNI - NOMBRE\ncopia archivos renombrados]
        P10 -->|no| P10B[estado: NO_ENCONTRADO]
        P10A --> DONE([resultado: PROCESADO_OK])
        P10B --> DONE
    end

    DONE --> AGG[agrega resultados\ntask_id en _DUAL_TASKS]
```

---

## 7. Diagrama de Dependencias entre Módulos

```mermaid
graph LR
    SRV[servidor_dj_quinta.py] --> CLF[clasificador_quinta.py]
    SRV --> PRO[procesador_ofertas.py]
    SRV --> CMB[procesador_combinado.py]
    SRV -->|subprocess| SEL[select_folder.py]
    CMB --> CLF
    CMB --> PRO

    CLF --> FITZ[PyMuPDF/fitz]
    CLF --> TESS[pytesseract\nopcional]
    CLF --> PIL[Pillow\nopcional]
    CLF --> GCV[google-cloud-vision\nopcional-inactivo]
    CLF --> SHELVE[shelve built-in]

    PRO --> FITZ
    PRO --> TESS
    PRO --> PIL

    SRV --> FLASK[Flask + Werkzeug]
    SRV --> OPXL[openpyxl]

    SEL --> TK[tkinter built-in]
```

---

## 8. Modelo de Datos — Objeto Resultado de Clasificación

Todos los endpoints de clasificación retornan resultados con el siguiente esquema:

```mermaid
classDiagram
    class ResultadoClasificacion {
        +String status         "OK | WARNING | ERROR"
        +String archivo        "nombre del archivo analizado"
        +String nombre         "nombre extraído del documento"
        +String persona        "nombre extraído de la carpeta padre"
        +String dni            "DNI/CE extraído (8-12 dígitos)"
        +String categoria      "1A | 1B | 2 | 3 | PRACT | null"
        +Dict categoria_info   "{codigo, nombre, descripcion, color}"
        +Float confianza       "0-100 — nivel de certeza de la clasificación"
        +String metodo         "técnica usada: drawings | texto_-X | etc."
        +String mensaje        "descripción legible del resultado"
    }

    class ResumenClasificacion {
        +Int total_procesados
        +Int exitosos
        +Int errores
        +Int sin_clasificar
        +Dict categorias       "{1A:N, 1B:N, 2:N, 3:N}"
        +Dict detalle_categorias
    }

    class ResultadoCombinado {
        +String persona        "nombre de carpeta de persona"
        +String dni            "DNI resuelto"
        +String carta_oferta   "nombre del archivo de carta"
        +String dj_quinta      "nombre del archivo de quinta"
        +String categoria      "categoría asignada"
        +Dict categoria_info
        +Float confianza_quinta
        +List terminos_carta   "beneficios detectados"
        +String estado         "PROCESADO_OK | NO_ENCONTRADO | ERROR_COPIA"
        +String ruta_destino   "ruta de la carpeta generada"
        +String mensaje
    }
```

---

## 9. Flujo de Inicio del Sistema

```mermaid
sequenceDiagram
    participant User as Usuario
    participant VBS as INICIAR.vbs
    participant WScript
    participant Cmd as cmd.exe
    participant PythonW as pythonw.exe
    participant Flask as servidor_dj_quinta.py
    participant Browser

    User->>VBS: doble clic
    VBS->>WScript: CreateObject FileSystemObject
    VBS->>VBS: verifica venv/Scripts/pythonw.exe
    alt venv no encontrado
        VBS->>User: MsgBox "¿Ejecutar INSTALAR.bat?"
        User->>VBS: sí
        VBS->>Cmd: INSTALAR.bat (síncrono)
    end
    VBS->>Cmd: libera puerto 5010\n(netstat + taskkill)
    VBS->>PythonW: servidor_dj_quinta.py (asíncrono, sin consola)
    PythonW->>Flask: import + app.run(:5010)
    VBS->>VBS: WScript.Sleep 3000
    VBS->>Browser: shell.Run "http://localhost:5010"
    Browser->>Flask: GET /
    Flask-->>Browser: quinta_categoria.html (SPA)
```

---

## 10. Caché OCR — Diseño

El caché usa Python `shelve` (wrapper sobre `dbm`) con clave **MD5 de los primeros 128 KB** del archivo. Esto garantiza:
- Respuesta instantánea en re-ejecuciones (mismo archivo → misma clave)
- Invalidación automática si el contenido cambia (diferente MD5 → miss)
- Cero dependencias externas (built-in Python)

```
archivo.pdf → MD5(primeros 128 KB) → "a3f8c2..."
                                          │
                                    shelve.open(cache_ocr_dni)
                                          │
                             ┌────────────┴──────────────┐
                             │ hit                       │ miss
                             ▼                           ▼
                    datos guardados              OCR Tesseract
                    {apellidos, prenombres,      → guardar resultado
                     numero, sexo, ...}          → retornar datos
```

**Limitación conocida:** El caché no tiene TTL ni límite de tamaño. En uso prolongado puede crecer de forma ilimitada. Se recomienda eliminarlo manualmente si supera 100 MB (`del cache_ocr_dni.*`).

---

## 11. Decisiones de Diseño Relevantes

| Decisión | Alternativa considerada | Razón elegida |
|----------|------------------------|---------------|
| Flask monolito local | FastAPI / Electron nativo | Simplicidad de despliegue: un solo `pip install`, funciona sin Node.js |
| `shelve` para caché | Redis / SQLite | Cero dependencias, no requiere servidor externo |
| Hilos (ThreadPoolExecutor) | Multiprocessing | Tesseract libera GIL; hilos son suficientes para I/O-bound OCR |
| `pythonw.exe` como runtime | `python.exe` | Sin ventana de consola visible al usuario |
| SPA sin framework | React / Vue | Portabilidad total: un solo archivo HTML autónomo |
| Subprocess para diálogo de carpeta | Tkinter en el hilo Flask | Tkinter bloquea el event loop de Flask en modo threading |
| `shutil.copy2` en proceso combinado | `shutil.move` | No destructivo; el origen se mantiene intacto ante fallos |

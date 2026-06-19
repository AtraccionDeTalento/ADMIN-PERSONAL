# Sistema de Administración Personal — DJ Quinta Categoría
**People Analytics · Universidad San Ignacio de Loyola (USIL)**
**Versión:** 2.0 (Portable) · **Puerto:** 5010 · **Última actualización:** Mayo 2026

---

## Descripción

Aplicación web local que automatiza dos procesos críticos del área de Recursos Humanos:

1. **Clasificación de Declaraciones Juradas de Quinta Categoría** — Lee PDFs (nativos o escaneados) y determina la categoría tributaria (1A, 1B, 2, 3) de cada colaborador nuevo, eliminando la revisión manual documento por documento.

2. **Proceso Combinado de Ingreso** — Toma carpetas con múltiples documentos de incorporación (carta oferta, DJ quinta, DNI/CUI, otros archivos), identifica los documentos clave, extrae el DNI, detecta beneficios salariales adicionales y reorganiza todo en carpetas estandarizadas por colaborador.

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Servidor web | Python 3.10+ · Flask ≥ 2.3 |
| Extracción PDF | PyMuPDF (fitz) ≥ 1.23 |
| OCR (opcional) | Tesseract OCR + pytesseract ≥ 0.3.10 |
| Procesamiento imagen | Pillow ≥ 10.0 |
| Generación Excel | openpyxl ≥ 3.1 |
| Frontend | HTML/CSS/JS vanilla (SPA sin framework) |
| Caché | Python `shelve` (built-in) |
| Concurrencia | `concurrent.futures.ThreadPoolExecutor` |

---

## Inicio Rápido

### Primera instalación

```
1. Instalar Python 3.10+  →  https://www.python.org/downloads/
   (marcar "Add Python to PATH" durante la instalación)

2. Doble clic en:  INSTALAR.bat
   (crea entorno virtual + instala dependencias — 2-5 min)

3. Doble clic en:  INICIAR.vbs
   (inicia el servidor y abre el navegador automáticamente)

4. Navegar a:  http://localhost:5010
```

### Inicio posterior (PC ya configurada)

```
Doble clic en:  INICIAR.vbs
```

### Si INICIAR.vbs no responde

```
Doble clic en:  launcher.py    ← diagnóstico automático
  — o bien —
Ejecutar:       DIAGNOSTICO.bat
```

---

## Estructura de Archivos (nivel raíz)

```
SISTEMA DE ADMIN PERSONAL/
│
├── INICIAR.vbs                ← Punto de entrada recomendado
├── launcher.py                ← Arranque alternativo con diagnóstico
├── INSTALAR.bat               ← Setup inicial (ejecutar una sola vez por PC)
├── DIAGNOSTICO.bat            ← Verificación de entorno
│
├── servidor_dj_quinta.py      ← Servidor Flask — todas las rutas HTTP
├── clasificador_quinta.py     ← Motor de análisis PDF/imagen
├── procesador_ofertas.py      ← Procesador de Cartas Oferta
├── procesador_combinado.py    ← Orquestador proceso dual
├── select_folder.py           ← Diálogo nativo de selección de carpeta
│
├── requirements.txt           ← Dependencias Python
├── categoria_overrides.json   ← Overrides manuales de categoría por DNI/nombre
│
├── templates/
│   └── quinta_categoria.html  ← Interfaz web completa (SPA)
│
├── venv/                      ← Entorno virtual Python (no compartir entre PCs)
├── uploads_quinta/            ← Archivos subidos temporalmente vía browser
├── cache_ocr_dni              ← Caché de resultados OCR (shelve)
│
├── FUNCIONALIDAD 2/           ← Datos de prueba y salida del proceso combinado
│   ├── Data de Prueba/        ← Carpetas de personas (entrada)
│   └── DESTINO/               ← Documentos procesados (salida)
│
├── docs/                      ← Documentación técnica
│   ├── README.md              ← Este archivo
│   ├── ARQUITECTURA.md
│   ├── MANUAL_TECNICO.md
│   ├── MANUAL_USUARIO.md
│   ├── API_REFERENCE.md
│   ├── AUDITORIA_CODIGO.md
│   └── PORTAFOLIO_PROYECTO.md
│
└── PRIMERO_LEE.txt            ← Instrucciones rápidas para nuevas PCs
```

---

## Categorías Tributarias

| Código | Nombre | Descripción |
|--------|--------|-------------|
| **1A** | Único Empleador — Con renta quinta previa | USIL es el único empleador. El colaborador SÍ percibió renta de quinta antes de ingresar. |
| **1B** | Único Empleador — Sin renta quinta previa | USIL es el único empleador. El colaborador NO percibió renta de quinta antes de ingresar. |
| **2** | Empleador Principal + Otros ingresos | USIL es el empleador principal pero existen otros empleadores que también retienen quinta. |
| **3** | No es Empleador Principal | USIL NO es el empleador principal. Solicita que no se le retenga quinta. |
| **PRACT** | Practicante | Asignado por override manual o inferido desde la carta oferta. |

---

## Documentación Adicional

| Documento | Audiencia | Contenido |
|-----------|-----------|-----------|
| [ARQUITECTURA.md](ARQUITECTURA.md) | Arquitectos / Tech Leads | Diagramas de componentes, capas, flujos de datos |
| [MANUAL_TECNICO.md](MANUAL_TECNICO.md) | Desarrolladores | Módulos, clases, funciones, configuración, extensión |
| [MANUAL_USUARIO.md](MANUAL_USUARIO.md) | Analistas de RRHH | Guía de uso paso a paso, errores comunes |
| [API_REFERENCE.md](API_REFERENCE.md) | Integradores / Devs | Endpoints, esquemas JSON, ejemplos |
| [AUDITORIA_CODIGO.md](AUDITORIA_CODIGO.md) | QA / Auditores | Deuda técnica, riesgos, recomendaciones |
| [PORTAFOLIO_PROYECTO.md](PORTAFOLIO_PROYECTO.md) | Gerencia / Stakeholders | Resumen ejecutivo, valor de negocio |
| [INVENTARIO_TECNICO.md](INVENTARIO_TECNICO.md) | Desarrolladores | Inventario completo de código y análisis |

---

## Contacto y Soporte

**Área:** People Analytics — Universidad San Ignacio de Loyola
**Repositorio:** Carpeta local en OneDrive compartido del equipo
**Entorno:** Windows 10/11 — ejecución local en localhost

> Este sistema no requiere conexión a internet para funcionar (salvo Google Vision, que es opcional y no está habilitado por defecto).

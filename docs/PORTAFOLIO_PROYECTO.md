# Portafolio de Proyecto — Sistema de Administración Personal
**People Analytics · Universidad San Ignacio de Loyola (USIL)**
**Documento:** PORTAFOLIO_PROYECTO.md · v1.0 · 2026-06-01

---

## Ficha del Proyecto

| Campo | Detalle |
|-------|---------|
| **Nombre** | Sistema de Administración Personal — DJ Quinta Categoría |
| **Área** | People Analytics — USIL |
| **Versión** | 2.0 (Portable) |
| **Estado** | Completo — En uso productivo |
| **Tecnología principal** | Python 3.10+ · Flask · PyMuPDF · Tesseract OCR |
| **Tipo** | Aplicación de escritorio / web local |
| **Puerto** | 5010 (localhost) |
| **Usuarios objetivo** | Analistas de Recursos Humanos — USIL |

---

## 1. Resumen Ejecutivo

El Sistema de Administración Personal automatiza la clasificación tributaria de colaboradores nuevos a partir de sus Declaraciones Juradas de Quinta Categoría, eliminando un proceso manual que requería la revisión individual de cada documento PDF.

El sistema también automatiza la organización de la carpeta de documentos de ingreso de cada colaborador, identificando los archivos clave (carta oferta y declaración jurada), extrayendo datos relevantes (DNI, categoría tributaria, beneficios salariales) y consolidándolos en una estructura de carpetas estandarizada.

**Resultado:** Lo que antes tomaba horas de revisión manual se completa en minutos con alta precisión.

---

## 2. Problema que Resuelve

### Contexto
Cuando un colaborador nuevo ingresa a USIL, el área de RRHH recibe múltiples documentos por persona (en promedio ~30 documentos según el usuario del sistema). Entre ellos, dos son críticos para el proceso de nómina:

1. **La Carta Oferta** — documento contractual que puede incluir beneficios adicionales (bono de transporte, prestación alimentaria, asignación de movilidad)
2. **La Declaración Jurada de Quinta Categoría** — formulario tributario que determina cómo se retiene el impuesto a la renta al colaborador

### Proceso anterior (manual)
- El analista de RRHH abría cada carpeta de persona
- Buscaba manualmente la DJ quinta entre decenas de documentos
- Leía el formulario PDF para identificar cuál opción estaba marcada
- Registraba la categoría en una planilla
- Repetía para cada colaborador nuevo

**Volumen de trabajo:** Para un proceso de ingreso de 50 personas, esto implicaba revisar potencialmente 1,500 documentos para localizar 50 declaraciones y leer cada una manualmente.

### Solución implementada
El sistema reemplaza completamente la revisión manual con un pipeline automatizado que:
- Identifica automáticamente la declaración jurada entre todos los documentos
- Determina la categoría tributaria con 6 métodos de detección en cascada
- Soporta PDFs digitales y documentos escaneados (vía OCR)
- Procesa múltiples colaboradores en paralelo (hasta 8 simultáneos)
- Genera reportes Excel formateados listos para entregar

---

## 3. Funcionalidades Implementadas

### 3.1 Clasificador DJ Quinta Categoría

| Funcionalidad | Estado |
|---------------|--------|
| Clasificación de PDFs digitales (texto nativo) | ✅ Implementado |
| Clasificación de PDFs escaneados (con OCR) | ✅ Implementado |
| Clasificación de imágenes (JPG, PNG, TIFF, etc.) | ✅ Implementado |
| 6 métodos de detección en cascada | ✅ Implementado |
| Procesamiento paralelo (hasta 8 workers) | ✅ Implementado |
| Modo carpeta-por-persona con reporte de faltantes | ✅ Implementado |
| Override manual de categoría por DNI o nombre | ✅ Implementado |
| Exportación de resultados a Excel formateado | ✅ Implementado |
| Caché OCR para re-ejecuciones instantáneas | ✅ Implementado |
| Soporte de 4 categorías tributarias (1A, 1B, 2, 3) | ✅ Implementado |
| Extracción de DNI del documento | ✅ Implementado |
| Identificación de DNI desde documentos DNI/CUI | ✅ Implementado |

### 3.2 Proceso Combinado (Cartas Oferta + Quinta)

| Funcionalidad | Estado |
|---------------|--------|
| Identificación automática de carta oferta (por nombre) | ✅ Implementado |
| Extracción de texto de cartas oferta (PDF + OCR) | ✅ Implementado |
| Detección de 3 tipos de beneficios adicionales | ✅ Implementado |
| Clasificación DJ quinta dentro del mismo proceso | ✅ Implementado |
| Extracción de DNI (5 estrategias en cascada) | ✅ Implementado |
| Creación de carpetas destino estandarizadas | ✅ Implementado |
| Renombrado de archivos con formato estándar | ✅ Implementado |
| Procesamiento en segundo plano con polling de estado | ✅ Implementado |
| Progreso en tiempo real en la interfaz | ✅ Implementado |
| Override manual de categoría | ✅ Implementado |
| Soporte de rutas largas en Windows (>260 chars) | ✅ Implementado |

### 3.3 Interfaz y Experiencia de Usuario

| Funcionalidad | Estado |
|---------------|--------|
| Interfaz web local (sin instalación de browser especial) | ✅ Implementado |
| Arrastrar y soltar archivos | ✅ Implementado |
| Selección de carpeta con diálogo nativo de Windows | ✅ Implementado |
| Tabla de resultados con colores por categoría | ✅ Implementado |
| Barra de progreso en tiempo real | ✅ Implementado |
| Arranque silencioso (sin ventana de consola) | ✅ Implementado |
| Auto-reparación de entorno virtual al inicio | ✅ Implementado |
| Diagnóstico automático de problemas | ✅ Implementado |
| Instalación portable (funciona en cualquier PC) | ✅ Implementado |

---

## 4. Arquitectura Técnica — Resumen

```
┌─────────────────────────────────────────────────────────────────┐
│  Capa de arranque: INICIAR.vbs → pythonw.exe (sin consola)     │
├─────────────────────────────────────────────────────────────────┤
│  Servidor web: Flask :5010 — 14 endpoints REST                 │
├─────────────────────────────────────────────────────────────────┤
│  Motor de clasificación: 6 métodos en cascada                  │
│  ├── Checkboxes gráficos (PyMuPDF drawings)                    │
│  ├── Texto marcado (-X, [X], (X))                              │
│  ├── Widgets de formulario PDF                                 │
│  ├── Formato antiguo (X + posición Y)                         │
│  ├── Spans bold                                                │
│  └── Keywords contextuales + regex tolerante a OCR            │
├─────────────────────────────────────────────────────────────────┤
│  Paralelismo: ThreadPoolExecutor (6-8 workers)                 │
│  Caché: shelve por hash MD5 (respuesta <1ms en re-ejecución)   │
├─────────────────────────────────────────────────────────────────┤
│  Salida: JSON API + Excel formateado (openpyxl)                │
└─────────────────────────────────────────────────────────────────┘
```

**Líneas de código:** ~3,344 (Python) + 92 KB (HTML/JS/CSS)
**Dependencias externas:** 6 paquetes Python + Tesseract OCR (opcional)
**Sin base de datos:** Estado en memoria + archivos JSON + shelve

---

## 5. Valor de Negocio

### Ahorro de tiempo estimado

| Proceso | Tiempo manual | Tiempo automatizado | Ahorro |
|---------|--------------|--------------------|----|
| Clasificar DJ quinta (50 personas, PDFs digitales) | ~2-3 horas | ~1-2 minutos | ~99% |
| Clasificar DJ quinta (50 personas, escaneados) | ~2-3 horas | ~5-15 minutos | ~95% |
| Proceso combinado completo (50 personas) | ~4-6 horas | ~5-15 minutos | ~97% |

### Reducción de errores
- Eliminación de errores de transcripción manual
- Detección automática de documentos faltantes (personas sin declaración)
- Trazabilidad del método de detección y nivel de confianza por resultado

### Estandarización de documentos
- Carpetas de destino con nombres uniformes: `{DNI} - {APELLIDOS NOMBRE}`
- Archivos renombrados con formato estándar: `Carta Oferta - {DNI} - {NOMBRE}.pdf`
- Reporte Excel formateado para entrega a nómina

---

## 6. Decisiones de Diseño Destacadas

### Portabilidad total
El sistema no requiere instalación de servidor, base de datos ni servicios externos. Funciona con un `pip install` y un doble clic. Se puede copiar la carpeta completa a cualquier PC Windows y ejecutar.

### Degradación elegante ante falta de OCR
Si Tesseract no está instalado, el sistema clasifica PDFs digitales normalmente y reporta claramente qué documentos necesitan OCR. No falla — funciona con las capacidades disponibles.

### Seis métodos en cascada para máxima cobertura
Los formularios de DJ quinta circulan en múltiples versiones y formatos (versión nueva, versión antigua, firmados digitalmente, escaneados, fotografiados). Cada método de detección cubre un subconjunto de estos casos. La cascada garantiza que se intenta el método más preciso primero y se recurre a métodos más permisivos solo si es necesario.

### Override manual como válvula de seguridad
Para los casos que el sistema no puede resolver automáticamente (documentos muy deteriorados, practicantes sin DJ quinta), el mecanismo de overrides en JSON permite que el equipo de RRHH registre la decisión manual sin modificar código.

---

## 7. Casos de Uso Documentados

**Caso 1 — Ingreso masivo de colaboradores**
Coordinador de Training descarga los documentos de 60 colaboradores nuevos. Cada uno tiene una carpeta propia con ~30 documentos. El proceso combinado identifica carta oferta y DJ quinta, extrae el DNI de cada persona y genera 60 carpetas limpias en minutos.

**Caso 2 — Auditoría de categorías tributarias**
El equipo de nómina necesita verificar la categoría de todos los colaboradores ingresados en el primer trimestre. Se carga la carpeta con todas las declaraciones (PDFs digitales). El sistema clasifica todos y exporta un Excel con colores para entrega directa.

**Caso 3 — Colaborador sin declaración**
Al procesar una carpeta, el sistema reporta "Sin declaración" para tres personas. RRHH contacta a esos colaboradores para que entreguen el documento faltante.

**Caso 4 — Clasificación ambigua**
Un PDF escaneado de baja calidad no puede ser clasificado automáticamente. El sistema reporta `?` con mensaje "Verificar manualmente". RRHH revisa el documento físico y actualiza el override en `categoria_overrides.json`.

---

## 8. Limitaciones Conocidas

| Limitación | Impacto | Estado |
|-----------|---------|--------|
| Detección de carta oferta solo por nombre de archivo | Cartas con nombres no estándar no son detectadas | Pendiente mejora |
| Carpetas duplicadas generadas en algunas ejecuciones | Limpieza manual requerida | Bug confirmado — ver DT-05 |
| Sin persistencia de estado para tareas largas | Reinicio del servidor pierde progreso visible | Pendiente mejora |
| PDFs escaneados requieren Tesseract OCR | Sin Tesseract, solo PDFs digitales | Documentado — instalación opcional |
| Rangos Y de checkboxes hardcodeados | Actualización manual si cambia el formulario | Bajo riesgo a corto plazo |

---

## 9. Comparación con Herramientas Previas

| Criterio | Proceso Manual | Power BI / Excel | **Este Sistema** |
|----------|---------------|-----------------|-----------------|
| Tiempo por 50 personas | 3-6 horas | No aplica | 2-15 minutos |
| Requiere revisar cada PDF | Sí | Sí | No |
| Soporta PDFs escaneados | Sí (manual) | No | Sí (con OCR) |
| Genera reporte automático | No | Parcial | Sí (Excel formateado) |
| Detecta documentos faltantes | No | No | Sí |
| Detecta beneficios en carta oferta | No | No | Sí |
| Requiere licencia | No | Sí | No |
| Instalación requerida | No | Office/Power BI | Python + INSTALAR.bat |

---

## 10. Próximas Mejoras Sugeridas

Basadas en el análisis de la auditoría de código y las limitaciones documentadas:

### Corto plazo (1-2 semanas)
1. Corregir bug de carpetas duplicadas (DT-05) — 1 línea
2. Limpiar entorno virtual huérfano `.venv/` (DT-01)
3. Cambiar `shutil.move` a `shutil.copy2` en `procesador_ofertas` (DT-06)

### Mediano plazo (1-3 meses)
4. Mejorar detección de carta oferta por contenido, no solo por nombre
5. Persistir estado de tareas en SQLite para sobrevivir reinicios del servidor
6. Agregar logging estructurado para diagnóstico de producción
7. Implementar pruebas automatizadas con PDFs anonimizados

### Largo plazo (3-6 meses)
8. Interfaz de gestión de overrides desde la propia UI (sin editar JSON)
9. Integración con el sistema principal People Analytics (API Central puerto 8000)
10. Exportación directa al sistema de nómina

---

## 11. Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| **Líneas de código Python** | ~3,344 |
| **Número de módulos** | 5 (+ 4 scripts auxiliares) |
| **Endpoints REST** | 14 |
| **Métodos de detección de categoría** | 6 en cascada |
| **Extensiones de archivo soportadas** | 10 (PDF + 9 formatos de imagen) |
| **Nivel máximo de paralelismo** | 8 workers simultáneos |
| **Tamaño del frontend (SPA)** | 92 KB (HTML/CSS/JS) |
| **Dependencias Python** | 6 paquetes |
| **Colaboradores de prueba en dataset** | ~46 (en carpeta DESTINO/) |

---

*Documento generado por análisis técnico completo del repositorio.*
*People Analytics — Universidad San Ignacio de Loyola · Junio 2026*

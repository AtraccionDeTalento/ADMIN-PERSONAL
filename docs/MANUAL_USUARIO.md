# Manual de Usuario — Sistema DJ Quinta Categoría
**People Analytics · USIL**
**Documento:** MANUAL_USUARIO.md · v1.0 · 2026-06-01
**Audiencia:** Analistas y especialistas de Recursos Humanos

---

## ¿Qué hace este sistema?

Este sistema reemplaza la revisión manual de dos tareas que antes consumían horas de trabajo:

**Tarea 1 — Clasificar Declaraciones Juradas de Quinta Categoría**
Cuando un colaborador nuevo ingresa, entrega una declaración jurada indicando su situación tributaria. El sistema lee esos documentos (PDF o foto) y determina automáticamente en cuál de las 4 categorías tributarias se encuentra.

**Tarea 2 — Organizar documentos de ingreso**
Cuando se tiene una carpeta por colaborador con múltiples documentos (carta oferta, DJ quinta, DNI, otros), el sistema identifica los documentos clave, extrae el DNI del colaborador y los organiza en carpetas limpias y estandarizadas.

---

## Antes de empezar

**Primera vez en esta computadora:** Alguien de TI o el propio analista debe haber ejecutado `INSTALAR.bat`. Si no lo ha hecho, el sistema no arrancará.

**Inicio rápido:**
1. Buscar el archivo `INICIAR.vbs` en la carpeta del sistema
2. Hacer **doble clic** sobre él
3. Esperar unos 3-5 segundos
4. El navegador se abrirá automáticamente en la dirección `http://localhost:5010`

> El sistema funciona en su computadora sin necesidad de internet. La dirección `localhost:5010` es completamente local.

---

## La Interfaz Principal

Al abrir el sistema verá una pantalla con dos secciones principales:

```
┌─────────────────────────────────────────────────────────────────┐
│  [PESTAÑA 1]  Clasificador DJ Quinta   │  [PESTAÑA 2]  Cartas  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Zona de carga de archivos (arrastrar y soltar)                │
│                                                                 │
│  [ Seleccionar carpeta ]    [ Analizar archivos ]              │
│                                                                 │
│  ─── Resultados ───────────────────────────────────────────    │
│  │ N° │ Persona │ DNI │ Nombre │ Cat. │ Descripción │         │
│  └─────────────────────────────────────────────────────────    │
│                                                                 │
│  [ Exportar Excel ]                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## FUNCIONALIDAD 1 — Clasificar Declaraciones Juradas

### ¿Cuándo usar esto?

Cuando tiene uno o más PDFs de Declaración Jurada de Quinta Categoría y necesita saber en qué categoría tributaria está cada colaborador.

---

### Método A: Arrastrar y soltar archivos individuales

1. Abrir la carpeta donde están los PDFs de declaración en el Explorador de Windows
2. Seleccionar uno o varios PDFs (puede usar `Ctrl+A` para todos)
3. Arrastrarlos y soltarlos en la zona punteada de la pantalla
4. Hacer clic en **"Analizar"**
5. Esperar unos segundos (el tiempo depende de cuántos archivos sean)
6. Ver los resultados en la tabla de abajo

---

### Método B: Analizar una carpeta completa

Este es el método más potente. Ideal cuando tiene una carpeta raíz con subcarpetas, una por colaborador:

```
Ejemplo de estructura:
├── 12345678 - GARCIA LOPEZ JOSE
│   ├── declaracion_quinta.pdf
│   └── DNI.jpg
├── 87654321 - RODRIGUEZ PEREZ ANA
│   └── DJ Quinta Ana Rodriguez.pdf
└── ...
```

Pasos:
1. Hacer clic en **"Seleccionar Carpeta"**
2. En el diálogo de Windows que aparece, navegar hasta la carpeta raíz
3. Hacer clic en **"Seleccionar Carpeta"** en el diálogo
4. Hacer clic en **"Analizar Carpeta"**
5. Esperar a que procese todas las carpetas
6. Revisar los resultados

> **Nota sobre carpetas sin documento:** Si una subcarpeta no tiene ningún PDF de quinta categoría, el sistema lo reportará como "Sin declaración". Esto permite identificar colaboradores pendientes.

---

### Entendiendo los resultados

La tabla de resultados muestra:

| Columna | Qué significa |
|---------|--------------|
| **N°** | Número de fila |
| **Persona (Carpeta)** | Nombre extraído de la carpeta del colaborador |
| **DNI (Declaración)** | DNI que aparece en el documento |
| **Nombre (Declaración)** | Nombre del colaborador en el documento |
| **Cat.** | Categoría tributaria asignada (1A, 1B, 2, 3) |
| **Descripción** | Explicación de qué significa esa categoría |

**Colores de categoría:**

| Color | Categoría | Qué significa |
|-------|-----------|--------------|
| 🔵 Azul | **1A** | USIL es su único empleador. Ya percibió renta quinta antes de ingresar. |
| 🟢 Verde | **1B** | USIL es su único empleador. Primera vez que percibe renta quinta. |
| 🟠 Naranja | **2** | USIL es su empleador principal, pero tiene otros empleos adicionales. |
| 🔴 Rojo | **3** | USIL no es su empleador principal. No se le retiene quinta. |
| — | **?** | No se pudo clasificar. Requiere revisión manual. |
| — | **ERR** | Error al procesar el archivo. |

---

### Exportar los resultados a Excel

Una vez procesados todos los archivos:
1. Hacer clic en **"Exportar Excel"**
2. El archivo se descarga automáticamente con el nombre `clasificacion_quinta_YYYYMMDD_HHMMSS.xlsx`
3. El Excel tiene dos hojas:
   - **"Clasificacion DJ Quinta"** — tabla detallada con colores
   - **"Resumen"** — estadísticas: total procesados, exitosos, errores, conteo por categoría

---

## FUNCIONALIDAD 2 — Procesar Documentos de Ingreso (Combinado)

### ¿Cuándo usar esto?

Cuando tiene carpetas con múltiples documentos de ingreso por colaborador (carta oferta, DJ quinta, DNI, contratos, etc.) y necesita:
- Extraer y organizar solo la carta oferta y la DJ quinta
- Identificar el DNI del colaborador
- Crear carpetas limpias con nombres estandarizados: `{DNI} - {NOMBRE}`
- Detectar si la carta tiene beneficios especiales (bono transporte, prestación alimentaria, etc.)

**Estructura de entrada esperada:**
```
Carpeta Origen/
├── GARCIA LOPEZ JOSE           ← carpeta con todos sus docs
│   ├── Carta Oferta - GARCIA.pdf
│   ├── DJ Quinta firmada.pdf
│   ├── DNI-Frontal.jpg
│   ├── contrato.pdf
│   └── otros documentos...
├── RODRIGUEZ PEREZ ANA
│   └── ...
└── ...
```

**Estructura de salida generada:**
```
Carpeta Destino/
├── 12345678 - GARCIA LOPEZ JOSE     ← carpeta renombrada con DNI
│   ├── Carta Oferta - 12345678 - GARCIA LOPEZ JOSE.pdf
│   └── DJ Quinta - 12345678 - GARCIA LOPEZ JOSE.pdf
├── 87654321 - RODRIGUEZ PEREZ ANA
│   └── ...
└── ...
```

---

### Pasos para el proceso combinado

1. En la interfaz, seleccionar la pestaña **"Cartas Oferta + Quinta"** (o el tab correspondiente)
2. Hacer clic en **"Seleccionar Carpeta Origen"** → navegar a la carpeta con los documentos de ingreso
3. Hacer clic en **"Seleccionar Carpeta Destino"** → seleccionar (o crear) la carpeta donde se guardarán los resultados
4. Hacer clic en **"Iniciar Proceso"**
5. Observar la barra de progreso: se actualiza en tiempo real mientras procesa cada persona
6. Al terminar, revisar el resumen de resultados

---

### Entendiendo los resultados del proceso combinado

| Estado | Qué significa |
|--------|--------------|
| **PROCESADO_OK** | Se encontraron carta oferta y/o DJ quinta. Archivos copiados correctamente. |
| **NO_ENCONTRADO** | No se encontró ningún documento reconocible en la carpeta. Revisar manualmente. |
| **ERROR_COPIA** | Se encontraron los documentos pero hubo un error al copiar (ruta muy larga, permisos, etc.). |

**Sobre los beneficios detectados:**

El sistema identifica automáticamente si la carta oferta menciona:
- **Bono de Transporte**
- **Prestación Alimentaria**
- **Asignación de Movilidad**

Si no detecta ninguno, reporta: **"Contrato Regular"**.

---

### Overrides manuales de categoría

Para colaboradores cuya declaración no puede ser clasificada automáticamente (PDFs muy deteriorados, formatos inusuales, practicantes que no tienen DJ quinta), existe un mecanismo de asignación manual.

Contactar al administrador del sistema para actualizar el archivo `categoria_overrides.json` con el DNI del colaborador y la categoría correcta.

---

## Situaciones comunes y soluciones

### "El sistema no abre cuando hago doble clic en INICIAR.vbs"

**Causa más probable:** No se ha ejecutado `INSTALAR.bat` en esta computadora.

**Solución:**
1. Hacer doble clic en `INSTALAR.bat`
2. Esperar hasta que aparezca el mensaje de instalación completa (2-5 minutos)
3. Intentar nuevamente con `INICIAR.vbs`

Si sigue sin funcionar: hacer doble clic en `launcher.py` — mostrará diagnóstico detallado.

---

### "Aparece el navegador pero la página no carga"

El servidor puede tardar unos segundos más. Esperar 10-15 segundos y refrescar la página (`F5`).

Si después de 30 segundos sigue sin cargar, hacer doble clic en `launcher.py` para ver qué error está ocurriendo.

---

### "Documentos escaneados no se clasifican"

Si sus PDFs son fotografías o documentos escaneados (en lugar de PDFs generados digitalmente), el sistema necesita OCR (reconocimiento óptico de caracteres). Para verificar si está disponible:

- Ejecutar `DIAGNOSTICO.bat`
- Si muestra `✗ Tesseract OCR: No instalado` → contactar a TI para instalarlo

Con PDFs digitales (generados por computadora), el sistema funciona sin OCR.

---

### "La categoría asignada parece incorrecta"

Posibles causas:
1. **El PDF estaba en blanco** — el colaborador no marcó ninguna opción. Devolver la DJ quinta para completar.
2. **Formato de PDF inusual** — el sistema soporta múltiples formatos pero algunos diseños muy personalizados pueden no ser reconocidos.
3. **Resolución insuficiente** — si es una imagen o escaneo de muy baja calidad.

En estos casos, el campo "Cat." mostrará `?` o `ERR`. Revisar manualmente el PDF y, si es posible, actualizar el override manual del colaborador.

---

### "El proceso combinado creó carpetas con nombres duplicados"

Ejemplo: aparecen `72622524 - RAMIREZ MUÑOZ...` y `72622524 - 72622524 - RAMIREZ MUÑOZ...`.

Esto ocurre cuando la carpeta de origen ya tenía un DNI en su nombre Y el sistema también detectó ese DNI. Solución: unificar las carpetas manualmente y eliminar el duplicado.

---

### "El proceso combinado tarda mucho"

El tiempo depende de:
- **Número de personas:** el sistema procesa 6 en paralelo
- **Calidad de los PDFs:** documentos escaneados requieren OCR, que es más lento
- **Presencia de archivos DNI/CUI:** el sistema intenta OCR en esos archivos para extraer datos

Para 50 personas con documentos digitales: aproximadamente 1-2 minutos.
Para 50 personas con documentos escaneados: puede tomar 5-15 minutos.

---

## Preguntas frecuentes

**¿Modifica o elimina los archivos originales?**
El proceso combinado **copia** los archivos (no los elimina del origen). El proceso de Cartas Oferta simple sí **mueve** (elimina del origen). Antes de usar el proceso simple de cartas, asegurarse de tener respaldo.

**¿Puedo usar el sistema en red compartida?**
El sistema está diseñado para uso local en una sola computadora. Aunque técnicamente puede acceder a carpetas de red (OneDrive, SharePoint, unidades mapeadas), el rendimiento puede ser menor y puede haber problemas con rutas muy largas.

**¿Qué pasa si cierro el navegador mientras procesa?**
El proceso continúa en segundo plano (el servidor sigue corriendo). Puede volver a abrir el navegador en `http://localhost:5010` y el estado del proceso seguirá siendo visible si la tarea no ha terminado.

**¿Cómo saber si el servidor está corriendo?**
Abrir el navegador e ir a `http://localhost:5010`. Si carga la interfaz, el servidor está activo. Si no carga, iniciar con `INICIAR.vbs`.

**¿Los datos se envían a internet?**
No. Todo el procesamiento ocurre localmente en su computadora. Ningún documento o dato sale de su equipo.

**¿Cuántos archivos puede procesar a la vez?**
No hay límite definido, pero el sistema acepta hasta 500 MB por carga de archivos (vía arrastrar y soltar). Para procesamiento de carpetas, funciona con cientos de personas sin problema.

---

## Glosario

| Término | Significado |
|---------|-------------|
| **DJ Quinta** | Declaración Jurada de Quinta Categoría — formulario tributario que indica la situación laboral del colaborador respecto a retenciones de renta de quinta |
| **Categoría 1A** | Único empleador con renta quinta previa |
| **Categoría 1B** | Único empleador sin renta quinta previa |
| **Categoría 2** | Empleador principal + otros ingresos |
| **Categoría 3** | USIL no es el empleador principal |
| **PRACT** | Practicante |
| **OCR** | Optical Character Recognition — tecnología que permite leer texto de imágenes y documentos escaneados |
| **Override** | Asignación manual de categoría que sobreescribe el resultado automático |
| **localhost** | Dirección de la computadora local en la red |
| **Triage** | Proceso de identificar y clasificar el contenido de un documento |

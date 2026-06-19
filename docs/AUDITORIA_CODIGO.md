# Auditoría de Código — Sistema DJ Quinta Categoría
**People Analytics · USIL**
**Documento:** AUDITORIA_CODIGO.md · v1.0 · 2026-06-01
**Tipo de auditoría:** Análisis estático — sin ejecución del código

---

## Resumen Ejecutivo

El sistema presenta un núcleo de clasificación técnicamente sofisticado con 6 métodos de detección en cascada, paralelismo efectivo y caché de OCR bien diseñado. Su deuda técnica principal reside en aspectos de operabilidad y robustez (doble entorno virtual, estado volátil de tareas, operación destructiva no documentada) más que en la lógica de negocio, la cual es sólida.

**Calificación por dimensión:**

| Dimensión | Calificación | Notas |
|-----------|-------------|-------|
| Lógica de negocio | ★★★★☆ | Algoritmo de cascada robusto, múltiples fallbacks |
| Mantenibilidad | ★★★☆☆ | Falta de pruebas formales; scripts de test con rutas hardcodeadas |
| Robustez operacional | ★★★☆☆ | Estado volátil en memoria; `shutil.move` sin respaldo |
| Seguridad | ★★★☆☆ | Sin auth, apropiado para localhost; superficie mínima |
| Rendimiento | ★★★★☆ | Paralelismo efectivo; caché OCR bien diseñado |
| Portabilidad | ★★★★☆ | Rutas relativas; venv local; buena documentación de instalación |

---

## 1. Deuda Técnica Catalogada

### DT-01 — Entorno Virtual Duplicado (CRÍTICO)
**Archivo:** Raíz del proyecto
**Impacto:** Confusión en mantenimiento y actualizaciones de dependencias

Existen dos entornos virtuales:
- `venv/` — referenciado por `INICIAR.vbs` y `launcher.py` (activo)
- `.venv/` — no referenciado por ningún script (huérfano)

Si un desarrollador instala dependencias en `.venv/` (comportamiento predeterminado de muchos IDEs que buscan `.venv/` primero), el servidor no las verá.

**Recomendación:**
```batch
rmdir /s /q .venv
```
Y configurar el IDE para usar `venv/` explícitamente.

---

### DT-02 — Estado de Tareas Volátil (CRÍTICO)
**Archivo:** `servidor_dj_quinta.py`, línea 59
**Impacto:** Pérdida de progreso visible + polling infinito en el cliente

```python
_DUAL_TASKS = {}  # Dict en memoria — se pierde al reiniciar
```

El proceso combinado puede tardar varios minutos. Si el servidor se reinicia (por actualización, error, reinicio manual), el cliente queda en polling indefinido porque el `task_id` ya no existe y retorna `404`.

Adicionalmente, `_DUAL_TASKS` crece ilimitadamente: cada llamada a `/combinado/procesar` agrega una entrada que nunca se limpia.

**Recomendación:**
```python
# Limpiar tareas completadas/con error hace más de 1 hora
import time
def _limpiar_tareas_viejas():
    ahora = time.time()
    a_borrar = [
        k for k, v in _DUAL_TASKS.items()
        if v['status'] in ('COMPLETED', 'ERROR')
        and (ahora - time.mktime(time.strptime(v['start_time'], "%Y-%m-%dT%H:%M:%S"))) > 3600
    ]
    for k in a_borrar:
        del _DUAL_TASKS[k]
```
A largo plazo: persistir en SQLite (`sqlite3` built-in) o en un archivo JSON.

---

### DT-03 — Google Cloud Vision Integrado pero No Documentado (CRÍTICO)
**Archivo:** `clasificador_quinta.py`, líneas 129-156 y 447-452
**Impacto:** Riesgo de activación accidental con facturación inesperada

El código importa e invoca `google.cloud.vision` si `GOOGLE_APPLICATION_CREDENTIALS` está en el entorno. No hay documentación de cuándo se habilitó, quién tiene las credenciales ni cuál es el coste.

**Recomendación:** Agregar una flag de feature explícita:
```python
_GOOGLE_VISION_ENABLED = os.environ.get('PA_GOOGLE_VISION', '').lower() == '1'

def _inicializar_google_vision():
    if not _GOOGLE_VISION_ENABLED:
        return False
    # ...resto del código
```

---

### DT-04 — Scripts de Prueba con Rutas Hardcodeadas (ALTA)
**Archivos:** `_test_diag.py`, `_test_full.py`, `_test_struct.py`, `_test_texto.py`
**Impacto:** Pruebas no ejecutables en ninguna PC salvo la del desarrollador

Todos los scripts de prueba usan rutas absolutas al perfil del desarrollador:
```python
carpeta = Path('c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA')
```

**Recomendación:** Convertirlos a rutas relativas usando `FUNCIONALIDAD 2/Data de Prueba/`:
```python
BASE = Path(__file__).parent
carpeta = BASE / 'FUNCIONALIDAD 2' / 'Data de Prueba'
```

O eliminarlos del repositorio y mover los datos de prueba a una carpeta `tests/fixtures/`.

---

### DT-05 — Carpetas Duplicadas en DESTINO (ALTA)
**Archivo:** `FUNCIONALIDAD 2/DESTINO/`
**Impacto:** Confirma un bug en producción no resuelto

Se observan carpetas con nombres duplicados:
```
40611256 - 40611256 - ESCUDERO ARENS DIEGO
40611256 - ESCUDERO ARENS DIEGO
72622524 - 72622524 - RAMIREZ MUÑOZ MAYRA ROCIO
72622524 - RAMIREZ MUÑOZ MAYRA ROCIO
```

**Análisis:** La carpeta de origen ya contenía el DNI en su nombre (`40611256 - ESCUDERO...`). `_extraer_dni_carpeta` extrajo "40611256" y luego la lógica de nombrado aplicó `f"{dni_val} - {name_clean}"` donde `name_clean` no limpió correctamente el prefijo DNI preexistente.

**Reproducción:** En `procesador_combinado.py`, línea 227:
```python
name_clean = re.sub(r'^\d{4,6}\s*[-–]\s*', '', persona_nombre).strip()
```
El regex `\d{4,6}` solo captura 4-6 dígitos, pero un DNI tiene 8. Si `persona_nombre = "40611256 - ESCUDERO ARENS DIEGO"`, el regex no lo limpia (8 dígitos > 6).

**Corrección:**
```python
name_clean = re.sub(r'^\d{4,8}\s*[-–]\s*', '', persona_nombre).strip()
#                         ^^^^ cambiar 4,6 por 4,8
```

---

### DT-06 — `procesador_ofertas::ejecutar` usa `shutil.move` (ALTA)
**Archivo:** `procesador_ofertas.py`, línea 177
**Impacto:** Pérdida de archivos ante fallos a mitad del proceso

```python
shutil.move(str(file), str(ruta_final))  # DESTRUCTIVO
```

A diferencia de `ProcesadorCombinado` que usa `shutil.copy2()`, este método elimina el archivo de origen. Si la ejecución se interrumpe (error de permisos, disco lleno, reinicio) después de mover algunos archivos pero no todos, no hay forma de recuperar el estado original.

**Recomendación:** Cambiar a `shutil.copy2()` + eliminar solo si la copia fue exitosa:
```python
shutil.copy2(str(file), str(ruta_final))
# Solo si se requiere "mover": descomentar la línea siguiente
# os.remove(str(file))
```

---

### DT-07 — Sin Límite de Crecimiento de `_DUAL_TASKS` (ALTA)
**Archivo:** `servidor_dj_quinta.py`, línea 59
**Ver también:** DT-02 (relacionado)

Cada invocación a `/combinado/procesar` acumula una tarea con todos sus resultados (cada resultado puede tener decenas de KBs). En uso intensivo, el proceso Python puede consumir cientos de MB de RAM.

**Recomendación:** Implementar TTL o límite de tareas almacenadas (ver DT-02).

---

### DT-08 — Detección de Beneficios Duplicada en Dos Módulos (MEDIA)
**Archivos:** `procesador_combinado.py` líneas 50-66 · `procesador_ofertas.py` líneas 26-29

La lógica de detección de beneficios (bono transporte, prestación alimentaria, asignación movilidad) está implementada de forma independiente en ambos módulos con patrones regex similares pero no idénticos.

| Módulo | Constante | Patrón para "Asignación de Movilidad" |
|--------|-----------|--------------------------------------|
| `procesador_combinado.py` | `_TERMINOS_BENEFICIOS` | `r'asignaci[oó]n\s+de\s+movilidad'` |
| `procesador_ofertas.py` | `KEYWORDS` | `r'asignaci[oó]n\s+de\s+movilidad'`, `r'movilidad\s+local'`, `r'gastos\s+de\s+movilidad'` |

`procesador_combinado.py` tiene menos patrones alternativos.

**Recomendación:** Centralizar en un módulo utilitario:
```python
# utils_terminos.py
TERMINOS = {
    'Bono de Transporte': [r'bono\s+de\s+transporte', r'bono\s+transporte'],
    'Prestación Alimentaria': [...],
    'Asignación de Movilidad': [...],
}
def detectar_terminos(texto: str) -> list[str]: ...
```

---

### DT-09 — Sin Autenticación ni CSRF (MEDIA)
**Archivo:** `servidor_dj_quinta.py`
**Contexto:** Sistema localhost — riesgo controlado

Cualquier proceso local o script puede hacer POST a las APIs del servidor. Sin tokens CSRF, un sitio web malicioso podría potencialmente desencadenar operaciones si el usuario visita ese sitio con el servidor activo.

**Evaluación:** El riesgo es bajo dado que opera en localhost y no está expuesto a internet. Sin embargo, para entornos donde varios usuarios comparten la misma máquina o se accede via VPN, añadir autenticación básica sería recomendable.

**Recomendación mínima (si se expone en red local):**
```python
from flask_httpauth import HTTPTokenAuth
auth = HTTPTokenAuth(scheme='Bearer')
VALID_TOKEN = os.environ.get('PA_API_TOKEN', 'cambia-esto')

@auth.verify_token
def verify_token(token): return token == VALID_TOKEN

@app.route('/api/v1/quinta/clasificar', methods=['POST'])
@auth.login_required
def api_clasificar(): ...
```

---

### DT-10 — `uploads_quinta/` sin Limpieza Automática (MEDIA)
**Archivo:** `servidor_dj_quinta.py`, línea 52

La ruta `/api/v1/quinta/clasificar` guarda archivos en `uploads_quinta/` pero nunca los elimina. En uso intensivo, esta carpeta puede crecer indefinidamente.

Solo `/api/v1/ofertas/clasificar` tiene limpieza (usando una carpeta `tmp_ofertas/`):
```python
try: os.remove(filepath)
except: pass
```

**Recomendación:** Agregar limpieza post-procesamiento en `api_clasificar`:
```python
# Después de procesar, limpiar archivos subidos
for ruta in rutas_guardadas:
    try: ruta.unlink()
    except: pass
```

---

### DT-11 — Detección de Carta Oferta Basada Solo en Nombre (MEDIA)
**Archivo:** `procesador_ofertas.py`, línea 110-113

```python
def es_carta_oferta(self, file_path):
    name = file_path.name.lower()
    return 'carta' in name and 'oferta' in name
```

Esta heurística falla si:
- La carta se llama `"Propuesta Economica.pdf"`, `"Ofrecimiento Laboral.pdf"` u otro nombre no estándar
- El archivo está en inglés (`"Job Offer Letter.pdf"`)

**Recomendación:** Agregar validación por contenido como fallback:
```python
def es_carta_oferta(self, file_path):
    name = file_path.name.lower()
    if 'carta' in name and 'oferta' in name:
        return True
    # Fallback: verificar contenido
    texto = self.extraer_texto(file_path)[:500]
    INDICADORES = ['carta de oferta', 'oferta laboral', 'ofrecemos', 'remuneración mensual']
    return any(ind in texto.lower() for ind in INDICADORES)
```

---

### DT-12 — `cache_ocr_dni` sin TTL ni Límite de Tamaño (MEDIA)
**Archivo:** `clasificador_quinta.py`, líneas 57-89

El caché shelve usa MD5 del contenido como clave, lo que es correcto para invalidación por cambio de contenido. Sin embargo, archivos eliminados del sistema siguen en el caché indefinidamente.

**Recomendación:** Agregar fecha de creación al caché y limpieza periódica:
```python
_cache_set(archivo_path, {'datos': datos, 'timestamp': time.time()})

# Al inicializar:
def _limpiar_cache_viejo(dias=30):
    limite = time.time() - (dias * 86400)
    with shelve.open(_CACHE_DB) as db:
        viejos = [k for k, v in db.items() if v.get('timestamp', 0) < limite]
        for k in viejos: del db[k]
```

---

### DT-13 — Codificación Corrupta en `FUNCIONALIDAD 2/C.txt` (BAJA)
**Archivo:** `FUNCIONALIDAD 2/C.txt`

El archivo contiene texto con caracteres mojibake (`â€™`, `Ã³`, `Ã¡`). Fue guardado en Windows-1252 pero el sistema lo trata como UTF-8. No afecta la ejecución del sistema pero indica un problema en el proceso de captura de requisitos.

---

### DT-14 — Inconsistencia en README.md (BAJA)
**Archivo:** `README.md`, línea 87

El README menciona `INSTALAR.vbs` en la sección de troubleshooting, pero el archivo real se llama `INICIAR.vbs`. Son dos archivos distintos — `INSTALAR.bat` es el instalador.

---

### DT-15 — Rangos Y de Checkboxes Hardcodeados (BAJA)
**Archivo:** `clasificador_quinta.py`, líneas 383-399

Los rangos de coordenadas Y (`CHECKBOX_Y_STD`, `CHECKBOX_Y_OLD`, `CHECKBOX_Y_WIDE`) están hardcodeados como atributos de clase. Si SUNAT cambia el formato del formulario, estos valores deben actualizarse manualmente en el código.

**Recomendación futura:** Externalizar a `config.json` para permitir actualización sin modificar código.

---

## 2. Análisis de Seguridad

### Superficie de ataque
El sistema opera exclusivamente en `127.0.0.1:5010`. No está expuesto a internet. La superficie de ataque está limitada a:
- Procesos locales en la misma máquina
- Scripts o páginas web que puedan hacer fetch a localhost (CSRF)

### Validación de entrada

| Endpoint | Validación actual | Estado |
|----------|------------------|--------|
| Upload de archivos | Verifica extensión; usa `secure_filename` | Adecuado |
| Rutas locales | Strip de comillas; verifica existencia | Aceptable |
| JSON endpoints | Verifica presencia de campos requeridos | Básico |
| `open-folder` | Verifica existencia de ruta | Adecuado |

**Riesgo de Path Traversal:** La ruta `/api/v1/utils/open-folder` acepta cualquier ruta del sistema. Un atacante local podría usar `os.startfile()` para ejecutar archivos arbitrarios. Riesgo bajo en contexto de PC personal de trabajo.

### Ejecución de código externo
El endpoint `/api/v1/quinta/reiniciar` ejecuta `subprocess.Popen([sys.executable, __file__])`. Esto es seguro ya que usa la ruta del intérprete y el script actual, sin concatenación de strings controlada por usuario.

`select_folder.py` se ejecuta como subprocess con ruta fija — sin riesgo de inyección.

---

## 3. Análisis de Rendimiento

### Puntos de cuello de botella identificados

**OCR con Tesseract** es la operación más costosa:
- PDF nativo: ~50-100ms por archivo
- PDF escaneado: ~500ms-2s por página (dependiendo de resolución y complejidad)
- Imagen DNI de baja resolución: ~1-3s (escalado 3×-8× + múltiples rotaciones)

**Mitigaciones implementadas:**
- `ThreadPoolExecutor` (hasta 8 workers para quinta, 6 para combinado)
- Caché shelve por hash MD5 para resultados OCR de DNIs
- Salida temprana en identificación de DNI cuando puntaje ≥ 0.75
- Filtro rápido `_es_posible_quinta()` para saltar archivos no candidatos
- Recursión controlada en `_texto_via_ocr()` con límite de scale=4.0

**Estimaciones de tiempo:**

| Escenario | Tiempo estimado |
|-----------|----------------|
| 1 PDF nativo | < 0.5s |
| 1 PDF escaneado (Tesseract disponible) | 1-3s |
| 50 personas, PDFs nativos | 3-8s |
| 50 personas, PDFs escaneados | 30-90s |
| 50 personas, con archivos DNI por OCR (primera ejecución) | 2-5 min |
| 50 personas, con archivos DNI por OCR (segunda ejecución, caché) | 10-30s |

---

## 4. Análisis de Calidad de Código

### Métricas de tamaño

| Archivo | Líneas | Clases | Funciones/Métodos |
|---------|--------|--------|-------------------|
| `clasificador_quinta.py` | 1,845 | 1 | ~35 |
| `servidor_dj_quinta.py` | 755 | 0 | 16 rutas + 2 helpers |
| `procesador_combinado.py` | 309 | 1 | 5 |
| `procesador_ofertas.py` | 203 | 1 | 10 |
| `launcher.py` | 216 | 1 | 5 |
| `select_folder.py` | 16 | 0 | 1 |
| **Total** | **~3,344** | | |

### Aspectos positivos del código

- **Manejo de compatibilidad `pythonw.exe`:** Los módulos redirigen `stdout`/`stderr` a `/dev/null` cuando son `None`, lo que permite ejecutar sin consola sin errores.
- **Lazy loading de OCR:** Tesseract y Pillow se inicializan solo cuando se necesitan, no al importar.
- **Graceful degradation:** El sistema funciona sin OCR (solo PDFs nativos).
- **Soporte de rutas largas Windows:** Prefijo `\\?\` en `procesador_combinado` y `procesador_ofertas`.
- **Consistencia de respuesta:** Todos los endpoints de clasificación retornan el mismo esquema de objeto resultado.

### Patrones de código cuestionables

**Import dentro de funciones** (múltiples instancias):
```python
# En servidor_dj_quinta.py, api_exportar_excel:
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# En procesador_combinado.py, procesar_persona:
import fitz as _fitz
from pathlib import Path as _P
```
Los imports locales tienen su justificación (diferir la carga hasta que se necesiten), pero el patrón inconsistente complica la comprensión del grafo de dependencias.

**Silenciamiento excesivo de excepciones:**
```python
except Exception:
    return None  # Sin logging, sin contexto
```
Aparece en ~15 funciones. Si algo falla silenciosamente en el caché o la extracción de DNI, no hay trazabilidad.

**Constante `PRIMERO_LEE.txt` incluye emojis** en código ASCII estricto — causará problemas en terminales sin soporte Unicode.

---

## 5. Riesgos de Mantenimiento

| Riesgo | Probabilidad | Impacto | Mitigación recomendada |
|--------|-------------|---------|----------------------|
| **Cambio de formato del formulario DJ Quinta** | Alta | Alto | Externalizar rangos Y a configuración; agregar modo "debug formato" |
| **Actualización de PyMuPDF con cambios de API** | Media | Alto | Fijar versión en requirements: `pymupdf==1.23.x`; test de regresión |
| **Acumulación de archivos en `uploads_quinta/`** | Alta | Bajo | Agregar limpieza automática post-procesamiento |
| **`.venv/` usado accidentalmente por IDE** | Alta | Medio | Eliminar `.venv/`; agregar `.python-version` con `venv` |
| **`_DUAL_TASKS` consume memoria en uso intensivo** | Media | Medio | Implementar TTL de limpieza |
| **`shutil.move` causa pérdida de datos** | Baja | Alto | Cambiar a `copy2` en `procesador_ofertas` |
| **Rutas >260 chars en `clasificador_quinta`** | Baja | Bajo | Aplicar `_get_win_path` consistentemente en todos los `fitz.open()` |

---

## 6. Recomendaciones Prioritizadas

### Prioridad 1 — Aplicar esta semana

1. **Eliminar `.venv/`** (DT-01) — 1 minuto de trabajo
   ```batch
   rmdir /s /q .venv
   ```

2. **Corregir bug de carpetas duplicadas** (DT-05) — 1 línea de código
   ```python
   # procesador_combinado.py, línea 227
   name_clean = re.sub(r'^\d{4,8}\s*[-–]\s*', '', persona_nombre).strip()
   ```

3. **Limpiar `uploads_quinta/` post-procesamiento** (DT-10) — 5 líneas de código

### Prioridad 2 — Antes del próximo despliegue

4. **Cambiar `shutil.move` a `shutil.copy2`** (DT-06) — proteger datos en `procesador_ofertas`

5. **Agregar TTL a `_DUAL_TASKS`** (DT-02/DT-07) — evitar crecimiento de memoria

6. **Corregir rutas hardcodeadas en scripts de prueba** (DT-04)

### Prioridad 3 — Mejoras a mediano plazo

7. **Centralizar detección de beneficios** en un módulo utilitario (DT-08)

8. **Agregar flag explícita para Google Vision** (DT-03)

9. **Implementar logging estructurado** (reemplazar `except: pass` silencioso)
   ```python
   import logging
   logger = logging.getLogger('pa_quinta')
   # En lugar de except: pass
   except Exception as e:
       logger.warning(f"Cache miss: {e}")
   ```

10. **Externalizar rangos Y de checkboxes** a `config.json` (DT-15)

### Prioridad 4 — Mejoras de largo plazo

11. **Persistir estado de tareas** en SQLite o JSON (DT-02) — para sobrevivir reinicios

12. **Pruebas formales** con PDFs reales (anonimizados) para regresión ante cambios

13. **Agregar validación de contenido a `es_carta_oferta`** (DT-11) para mayor cobertura

---

## Apéndice: Checklist de Transferencia de Conocimiento

Para un nuevo desarrollador que tome el mantenimiento del sistema:

- [ ] Leer `docs/ARQUITECTURA.md` para entender la estructura general
- [ ] Leer `docs/MANUAL_TECNICO.md` para entender cada módulo
- [ ] Ejecutar `INSTALAR.bat` en una PC limpia y verificar que funciona
- [ ] Revisar y ejecutar `clasificador_quinta.py` en modo standalone con un PDF de prueba
- [ ] Revisar `categoria_overrides.json` para entender los casos especiales activos
- [ ] Verificar el estado del caché `cache_ocr_dni.*` (tamaño, edad)
- [ ] Confirmar que `.venv/` ha sido eliminado (DT-01)
- [ ] Aplicar corrección de DT-05 (carpetas duplicadas)
- [ ] Revisar y actualizar `CHECKBOX_Y_STD` si el formulario DJ quinta cambió recientemente

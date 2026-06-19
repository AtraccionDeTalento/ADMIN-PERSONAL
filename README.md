# Sistema de Administración Personal — DJ Quinta Categoría
**People Analytics USIL** · Clasificador automático de declaraciones juradas

---

## 📋 Requisitos previos

- **Windows 7, 10, 11** (o superior)
- **Python 3.10+** (descargar de https://www.python.org/downloads/)
- Conexión a Internet (solo para la instalación inicial)

---

## 🚀 INSTALACIÓN RÁPIDA (para otras PCs)

### Paso 1: Instalar Python
1. Ve a https://www.python.org/downloads/
2. Descarga la versión más reciente para Windows
3. **IMPORTANTE:** Durante la instalación marca ✅ "Add Python to PATH"
4. Reinicia la computadora después de instalar

### Paso 2: Preparar el Sistema
1. Copia toda la carpeta `SISTEMA DE ADMIN PERSONAL` a tu computadora
2. Abre una terminal (cmd) y navega a esa carpeta
3. Ejecuta:
   ```bash
   INSTALAR.bat
   ```
4. **Espera a que termine** (tomará 2-5 minutos la primera vez)

### Paso 3: Iniciar
Tienes 3 opciones para iniciar:

#### Opción 1: INICIAR.vbs (Recomendada) ⭐
- Haz **doble clic** en `INICIAR.vbs`
- Se abrirá sin ventana de consola
- El navegador se abre automáticamente

#### Opción 2: launcher.py (Si INICIAR.vbs falla)
- Haz **doble clic** en `launcher.py`
- Mostrará diagnóstico automático
- Ideal para debuggear problemas

#### Opción 3: Terminal (Manual)
```bash
python launcher.py
```

---

## 🔍 DIAGNOSTICAR PROBLEMAS

### "INICIAR.vbs no abre nada"

Ejecuta primero el diagnóstico:
```bash
DIAGNOSTICO.bat
```

Esto verificará:
- ✓ Python instalado correctamente
- ✓ Entorno virtual (venv) funcional
- ✓ Dependencias instaladas
- ✓ Puerto 5010 disponible
- ✓ Tesseract OCR (opcional)

### Problemas comunes

#### ❌ "Python no encontrado"
**Solución:**
1. Desinstala Python completamente
2. Descarga nuevamente de https://www.python.org/downloads/
3. **Durante la instalación MARCA "Add Python to PATH"**
4. Reinicia la terminal
5. Ejecuta `INSTALAR.bat` de nuevo

#### ❌ "Entorno virtual corrupto"
**Solución:**
```bash
rmdir /s /q venv
INSTALAR.bat
```

#### ❌ "Puerto 5010 ya está en uso"
**Solución:**
- Cierra cualquier navegador con `http://localhost:5010` abierto
- O usa `INSTALAR.vbs` que limpia el puerto automáticamente

#### ❌ "No se puede leer documentos escaneados"
**Información:** Sin Tesseract OCR, solo funcionan PDFs con texto nativo.

**Para instalar Tesseract:**
1. Ve a: https://github.com/UB-Mannheim/tesseract/wiki
2. Descarga el instalador para Windows
3. Instala en la ubicación por defecto
4. Reinicia la aplicación

---

## 📂 Estructura de archivos

```
SISTEMA DE ADMIN PERSONAL/
├── INSTALAR.bat              ← Ejecuta primero (setup)
├── DIAGNOSTICO.bat           ← Si hay problemas
├── INICIAR.vbs               ← Iniciar (recomendado)
├── launcher.py               ← Iniciar alternativo
├── servidor_dj_quinta.py     ← Servidor Flask
├── clasificador_quinta.py    ← Motor de clasificación
├── procesador_combinado.py   ← Procesador adicional
├── requirements.txt          ← Dependencias Python
├── venv/                     ← Entorno virtual (se crea automáticamente)
├── templates/                ← HTML de la interfaz
│   └── quinta_categoria.html
├── uploads_quinta/           ← Carpeta de archivos subidos
├── FUNCIONALIDAD 2/          ← Datos de prueba
└── README.md                 ← Este archivo
```

---

## 🌐 Acceder a la aplicación

Después de iniciar, la aplicación estará en:
```
http://localhost:5010
```

Si el navegador no abre automáticamente, copia esa URL manualmente.

---

## 📝 Notas de Portabilidad

✅ **Lo que funciona en cualquier PC:**
- Todas las rutas usan rutas relativas (no hardcodeadas)
- El venv se crea localmente en cada PC
- Las dependencias se instalan en ese venv

⚠️ **Lo que necesita configuración local:**
- **Python**: Debe estar instalado en cada PC
- **Tesseract OCR**: Necesario para escaneos (opcional)

---

## 📞 Soporte

Si tienes problemas:

1. **Ejecuta DIAGNOSTICO.bat** para ver detalles
2. **Revisa los logs** en `logs_iniciar.txt` (si existe)
3. **Intenta en otra terminal** con permisos de Admin (clic derecho → Run as Administrator)

---

## 🔐 Seguridad

- El venv es **específico de cada PC** (no compartible entre computadoras)
- Los archivos subidos se guardan en `uploads_quinta/`
- No hay clave o contraseña (se ejecuta en localhost)

---

**Última actualización:** Mayo 2026  
**Versión:** 2.0 (Portable)

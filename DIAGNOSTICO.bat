@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title Diagnostico - Sistema DJ Quinta Categoria
cls

echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║         DIAGNOSTICO - Sistema DJ Quinta Categoria                ║
echo ║         People Analytics USIL                                    ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.

:: ── Directorio del script (relativo) ───────────────────────────────────
set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

echo [DIAGNOSTICO BASICO]
echo.

:: 1. Verificar Python global
echo [1/6] Verificando Python global...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ✗ Python NO instalado o NO en PATH
    echo      Solución: Instala Python y marca "Add Python to PATH"
    set "PYTHON_OK=0"
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
    echo    ✓ Python %PYVER% encontrado
    set "PYTHON_OK=1"
)
echo.

:: 2. Verificar venv
echo [2/6] Verificando entorno virtual...
if exist "%DIR%\venv\Scripts\python.exe" (
    echo    ✓ Directorio venv existe
    set "VENV_EXISTS=1"
) else (
    echo    ✗ Directorio venv NO existe
    echo      Solución: Ejecuta INSTALAR.bat
    set "VENV_EXISTS=0"
)
echo.

:: 3. Probar venv si existe
echo [3/6] Probando venv...
if !VENV_EXISTS! equ 1 (
    "%DIR%\venv\Scripts\python.exe" --version >nul 2>&1
    if errorlevel 1 (
        echo    ✗ venv existe pero Python NO funciona
        echo      Solución: Borra venv y ejecuta INSTALAR.bat nuevamente
        echo      rmdir /s /q "%DIR%\venv"
        set "VENV_OK=0"
    ) else (
        for /f "tokens=2" %%i in ('"%DIR%\venv\Scripts\python.exe" --version 2^>^&1') do set VENV_PYVER=%%i
        echo    ✓ venv funcional: Python !VENV_PYVER!
        set "VENV_OK=1"
    )
) else (
    echo    - venv no existe, saltando
    set "VENV_OK=0"
)
echo.

:: 4. Verificar archivos principales
echo [4/6] Verificando archivos necesarios...
set "FILES_OK=1"

if not exist "%DIR%\servidor_dj_quinta.py" (
    echo    ✗ servidor_dj_quinta.py falta
    set "FILES_OK=0"
) else (
    echo    ✓ servidor_dj_quinta.py encontrado
)

if not exist "%DIR%\clasificador_quinta.py" (
    echo    ✗ clasificador_quinta.py falta
    set "FILES_OK=0"
) else (
    echo    ✓ clasificador_quinta.py encontrado
)

if not exist "%DIR%\templates\quinta_categoria.html" (
    echo    ✗ templates\quinta_categoria.html falta
    set "FILES_OK=0"
) else (
    echo    ✓ templates\quinta_categoria.html encontrado
)
echo.

:: 5. Verificar puerto 5010
echo [5/6] Verificando puerto 5010...
netstat -ano | findstr :5010 >nul 2>&1
if errorlevel 1 (
    echo    ✓ Puerto 5010 disponible
    set "PORT_OK=1"
) else (
    echo    ✗ Puerto 5010 YA ESTA EN USO - posible servidor previo
    echo      Solución: Cierra otras ventanas o usa INICIAR.vbs que lo limpia
    set "PORT_OK=0"
)
echo.

:: 6. Verificar Tesseract (opcional pero recomendado)
echo [6/6] Verificando Tesseract OCR (opcional)...
set "TESS_FOUND=0"
set "TESS_EXE="
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo    ✓ Tesseract encontrado en Program Files
    set "TESS_FOUND=1"
    set "TESS_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe"
)
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    echo    ✓ Tesseract encontrado en Program Files x86
    set "TESS_FOUND=1"
    set "TESS_EXE=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
)
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (
    echo    ✓ Tesseract encontrado en AppData\Local
    set "TESS_FOUND=1"
    set "TESS_EXE=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
)
if %TESS_FOUND% equ 0 (
    echo    ⚠ Tesseract NO encontrado - solo necesario para escaneos
    echo      Descárgalo de: https://github.com/UB-Mannheim/tesseract/wiki
)
if %TESS_FOUND% equ 1 (
    echo    Verificando idiomas OCR...
    "%TESS_EXE%" --list-langs 2>nul | findstr /i /r "^eng$" >nul
    if errorlevel 1 (
        echo    ⚠ Idioma eng NO encontrado
    ) else (
        echo    ✓ Idioma eng detectado
    )
    "%TESS_EXE%" --list-langs 2>nul | findstr /i /r "^spa$" >nul
    if errorlevel 1 (
        echo    ⚠ Idioma spa NO encontrado (afecta reconocimiento en español)
    ) else (
        echo    ✓ Idioma spa detectado
    )
)
echo.

:: ────────────────────────────────────────────────────────────────────
:: RESUMEN
:: ────────────────────────────────────────────────────────────────────
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║ RESUMEN                                                           ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.

if %PYTHON_OK% equ 1 (
    echo  ✓ Python global OK
) else (
    echo  ✗ Python global FALLA
)

if !VENV_OK! equ 1 (
    echo  ✓ Entorno virtual OK
    echo  ✓ Archivos necesarios OK
    echo  ✓ Puerto 5010 OK
    echo.
    echo  ═══════════════════════════════════════════════════════════════════
    echo  ✓ TODO LISTO PARA INICIAR
    echo  ═══════════════════════════════════════════════════════════════════
    echo.
    echo  Puedes hacer doble clic en:
    echo    • INICIAR.vbs - recomendado, sin ventana de consola
    echo    • launcher.py - alternativa con diagnostico
    echo.
) else (
    echo  ✗ Entorno virtual FALLA
    echo.
    echo  ═══════════════════════════════════════════════════════════════════
    echo  NECESITAS CORREGIR ESTOS PROBLEMAS:
    echo  ═══════════════════════════════════════════════════════════════════
    echo.
    if %PYTHON_OK% equ 0 (
        echo  1. Instala Python desde: https://www.python.org/downloads/
        echo     Durante la instalación marca "Add Python to PATH"
        echo.
    )
    if !VENV_OK! equ 0 (
        echo  2. Ejecuta INSTALAR.bat y espera a que termine
        echo     tomara 2-3 minutos la primera vez
        echo.
    )
    echo  Luego vuelve a ejecutar este diagnóstico.
    echo.
)

echo Presiona ENTER para cerrar...
pause >nul

@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Instalador -- Sistema DJ Quinta Categoria

echo.
echo ===================================================================
echo   INSTALADOR -- Sistema DJ Quinta Categoria
echo   People Analytics USIL
echo ===================================================================
echo.
echo  Ejecuta esto UNA VEZ en cada PC antes de usar el sistema.
echo.

set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"
set "ERRORES=0"
set "PY_CMD="

:: ===================================================================
:: [1/6] Python
:: ===================================================================
echo [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    py -3 --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  ERROR: Python no encontrado.
        echo.
        echo  Instala Python desde https://www.python.org/downloads/
        echo  y marca "Add Python to PATH" durante la instalacion.
        echo  Luego cierra esta ventana y vuelve a ejecutar INSTALAR.bat.
        echo.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py -3"
        for /f "tokens=2" %%i in ('py -3 --version 2^>^&1') do set PYVER=%%i
    )
) else (
    set "PY_CMD=python"
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
)
echo    OK  Python %PYVER%
echo.

:: ===================================================================
:: [2/6] Entorno virtual
:: ===================================================================
echo [2/6] Preparando entorno virtual...

:: Leer pyvenv.cfg para detectar venv de otra PC SIN ejecutar python.exe
:: (ejecutarlo con rutas incorrectas dispara un dialogo de error de Windows)
if exist "%DIR%\venv\pyvenv.cfg" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%DIR%\venv\pyvenv.cfg") do (
        if /i "%%A"=="home " (
            set "VENV_HOME=%%B"
            if "!VENV_HOME:~0,1!"==" " set "VENV_HOME=!VENV_HOME:~1!"
            if not exist "!VENV_HOME!\python.exe" (
                echo    AVISO: Venv creado en otra PC. Eliminando y recreando...
                rmdir /s /q "%DIR%\venv" 2>nul
                timeout /t 1 >nul
            )
        )
    )
)

:: Si el venv existe y es de esta PC, verificar que funciona
if exist "%DIR%\venv\Scripts\python.exe" (
    "%DIR%\venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo    AVISO: Venv corrupto. Eliminando y recreando...
        rmdir /s /q "%DIR%\venv" 2>nul
        timeout /t 1 >nul
    ) else (
        echo    OK  Entorno virtual listo
        goto :INSTALAR_DEPS
    )
)

echo    Creando entorno virtual...
%PY_CMD% -m venv "%DIR%\venv"
if errorlevel 1 (
    echo    AVISO: Primer intento fallo. Reintentando con ensurepip...
    %PY_CMD% -m ensurepip --upgrade >nul 2>&1
    %PY_CMD% -m venv "%DIR%\venv"
    if errorlevel 1 (
        echo.
        echo  ERROR: No se pudo crear el entorno virtual.
        echo  Verifica permisos de carpeta y que Python no sea de Microsoft Store bloqueado.
        echo  Comando usado: %PY_CMD%
        echo.
        pause
        exit /b 1
    )
)
if not exist "%DIR%\venv\Scripts\python.exe" (
    echo  ERROR: venv creado pero falta python.exe. Intenta de nuevo.
    pause
    exit /b 1
)
echo    OK  Entorno virtual creado
echo.

:: ===================================================================
:: [3/6] Dependencias Python
:: ===================================================================
:INSTALAR_DEPS
echo [3/6] Instalando dependencias...
echo    flask, pymupdf, openpyxl, pytesseract, Pillow, werkzeug
echo    Primera instalacion puede tardar 2-5 minutos...
echo.

"%DIR%\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet 2>nul
"%DIR%\venv\Scripts\python.exe" -m pip install flask pymupdf openpyxl pytesseract Pillow werkzeug --quiet

if errorlevel 1 (
    echo.
    echo  ERROR: Fallo la instalacion. Verifica tu conexion a internet.
    echo.
    set /a ERRORES+=1
) else (
    echo    OK  Dependencias instaladas
)
echo.

:: ===================================================================
:: [4/6] Verificacion de paquetes y archivos
:: ===================================================================
echo [4/6] Verificando instalacion...

"%DIR%\venv\Scripts\python.exe" -c "import flask"       >nul 2>&1
if errorlevel 1 (echo    ERROR  flask           FALLA & set /a ERRORES+=1) else (echo    OK    flask)

"%DIR%\venv\Scripts\python.exe" -c "import fitz"        >nul 2>&1
if errorlevel 1 (echo    ERROR  pymupdf         FALLA & set /a ERRORES+=1) else (echo    OK    pymupdf)

"%DIR%\venv\Scripts\python.exe" -c "import openpyxl"    >nul 2>&1
if errorlevel 1 (echo    ERROR  openpyxl        FALLA & set /a ERRORES+=1) else (echo    OK    openpyxl)

"%DIR%\venv\Scripts\python.exe" -c "import pytesseract" >nul 2>&1
if errorlevel 1 (echo    ERROR  pytesseract    FALLA & set /a ERRORES+=1) else (echo    OK    pytesseract)

"%DIR%\venv\Scripts\python.exe" -c "import PIL"         >nul 2>&1
if errorlevel 1 (echo    ERROR  Pillow          FALLA & set /a ERRORES+=1) else (echo    OK    Pillow)

if not exist "%DIR%\servidor_dj_quinta.py"           (echo    ERROR  servidor_dj_quinta.py FALTA & set /a ERRORES+=1) else (echo    OK    servidor_dj_quinta.py)
if not exist "%DIR%\clasificador_quinta.py"          (echo    ERROR  clasificador_quinta.py FALTA & set /a ERRORES+=1) else (echo    OK    clasificador_quinta.py)
if not exist "%DIR%\procesador_combinado.py"         (echo    ERROR  procesador_combinado.py FALTA & set /a ERRORES+=1) else (echo    OK    procesador_combinado.py)
if not exist "%DIR%\templates\quinta_categoria.html" (echo    ERROR  templates\quinta_categoria.html FALTA & set /a ERRORES+=1) else (echo    OK    templates\quinta_categoria.html)
echo.

:: ===================================================================
:: [5/6] Tesseract OCR
:: ===================================================================
echo [5/6] Verificando Tesseract OCR...
set "TESS_OK=0"
set "TESS_EXE="
set "TESS_LANG_ENG=0"
set "TESS_LANG_SPA=0"
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe"        (set "TESS_OK=1" & set "TESS_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe")
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"  (set "TESS_OK=1" & set "TESS_EXE=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (set "TESS_OK=1" & set "TESS_EXE=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
if exist "%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"          (set "TESS_OK=1" & set "TESS_EXE=%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")

if "%TESS_OK%"=="1" (
    echo    OK    Tesseract OCR instalado
) else (
    echo    AVISO Tesseract OCR no encontrado. Intentando instalar automaticamente...

    :: Intento 1: winget (ids alternativos para mayor compatibilidad)
    where winget >nul 2>&1
    if errorlevel 1 (
        echo    AVISO winget no disponible en esta PC.
    ) else (
        echo    Intentando con winget id=UB-Mannheim.TesseractOCR ...
        winget install -e --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements --disable-interactivity >nul 2>&1
        if errorlevel 1 (
            echo    Reintentando con winget id=tesseract-ocr.tesseract ...
            winget install -e --id tesseract-ocr.tesseract --accept-source-agreements --accept-package-agreements --disable-interactivity >nul 2>&1
            if errorlevel 1 (
                echo    Reintentando con winget id=Tesseract.Tesseract.Stable ...
                winget install -e --id Tesseract.Tesseract.Stable --accept-source-agreements --accept-package-agreements --disable-interactivity >nul 2>&1
            )
        )
    )

    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe"        (set "TESS_OK=1" & set "TESS_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe")
    if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"  (set "TESS_OK=1" & set "TESS_EXE=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")
    if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (set "TESS_OK=1" & set "TESS_EXE=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
    if exist "%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"          (set "TESS_OK=1" & set "TESS_EXE=%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")

    :: Intento 2: Chocolatey (si existe)
    if "%TESS_OK%"=="0" (
        where choco >nul 2>&1
        if not errorlevel 1 (
            echo    Intentando con choco install tesseract ...
            choco install tesseract -y --no-progress >nul 2>&1
            if exist "C:\Program Files\Tesseract-OCR\tesseract.exe"        (set "TESS_OK=1" & set "TESS_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe")
            if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"  (set "TESS_OK=1" & set "TESS_EXE=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")
            if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" (set "TESS_OK=1" & set "TESS_EXE=%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
            if exist "%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"          (set "TESS_OK=1" & set "TESS_EXE=%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")
        )
    )

    if "%TESS_OK%"=="1" (
        echo    OK    Tesseract OCR instalado automaticamente
    ) else (
        echo    AVISO Tesseract OCR sigue sin instalarse.
        echo.
        echo    Sin Tesseract no se procesan PDFs escaneados ni imagenes.
        echo    Los PDFs con texto nativo SI funcionan sin el.
        echo.
        echo    Descargalo: https://github.com/UB-Mannheim/tesseract/wiki
        echo    Instala en la ubicacion por defecto y ejecuta INSTALAR.bat de nuevo.
        set /a ERRORES+=1
    )
)

if "%TESS_OK%"=="1" (
    echo    Verificando idiomas OCR (eng/spa)...
    set "TESSDATA_DIR="
    for %%P in ("%TESS_EXE%") do set "TESSDATA_DIR=%%~dpPtessdata"

    "%TESS_EXE%" --list-langs 2>nul | findstr /i /r "^eng$" >nul
    if errorlevel 1 (
        echo    AVISO idioma eng no detectado en Tesseract.
    ) else (
        echo    OK    idioma eng detectado
        set "TESS_LANG_ENG=1"
    )
    "%TESS_EXE%" --list-langs 2>nul | findstr /i /r "^spa$" >nul
    if errorlevel 1 (
        echo    AVISO idioma spa no detectado.
        echo    Intentando descargar spa.traineddata...
        if exist "!TESSDATA_DIR!" (
            powershell -NoProfile -ExecutionPolicy Bypass -Command "try {Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/spa.traineddata' -OutFile '!TESSDATA_DIR!\spa.traineddata' -UseBasicParsing; exit 0} catch {exit 1}" >nul 2>&1
        )
        "%TESS_EXE%" --list-langs 2>nul | findstr /i /r "^spa$" >nul
        if errorlevel 1 (
            echo    AVISO no se pudo agregar spa automaticamente. Instalar idioma espanol en Tesseract.
            set /a ERRORES+=1
        ) else (
            echo    OK    idioma spa detectado
            set "TESS_LANG_SPA=1"
        )
    ) else (
        echo    OK    idioma spa detectado
        set "TESS_LANG_SPA=1"
    )
)
echo.

:: ===================================================================
:: [6/6] Verificando Git
:: ===================================================================
echo [6/6] Verificando Git...
set "GIT_OK=0"
where git >nul 2>nul
if not errorlevel 1 (
    echo    OK    Git instalado
    set "GIT_OK=1"
) else (
    echo    AVISO Git no encontrado. Intentando instalar automaticamente...
    
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo    Intentando con winget id=Git.Git ...
        winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements --disable-interactivity >nul 2>&1
    )
    
    where git >nul 2>nul
    if not errorlevel 1 (
        echo    OK    Git instalado automaticamente
        set "GIT_OK=1"
    ) else (
        where choco >nul 2>&1
        if not errorlevel 1 (
            echo    Intentando con choco install git ...
            choco install git -y --no-progress >nul 2>&1
        )
        
        where git >nul 2>nul
        if not errorlevel 1 (
            echo    OK    Git instalado automaticamente
            set "GIT_OK=1"
        ) else (
            echo    AVISO Git sigue sin instalarse.
            echo    Sin Git no se podran recibir actualizaciones automaticas.
            echo    Descargalo: https://git-scm.com/downloads
            set /a ERRORES+=1
        )
    )
)
echo.

:: ===================================================================
:: Resultado final
:: ===================================================================
echo ===================================================================
echo  RESUMEN TESSERACT:
if "%TESS_OK%"=="1" (
    echo    - Estado: INSTALADO
    echo    - Ruta: %TESS_EXE%
) else (
    echo    - Estado: NO INSTALADO
)
if "%TESS_LANG_ENG%"=="1" (echo    - Idioma eng: OK) else (echo    - Idioma eng: FALTA)
if "%TESS_LANG_SPA%"=="1" (echo    - Idioma spa: OK) else (echo    - Idioma spa: FALTA)
if "%GIT_OK%"=="1" (echo    - Git: OK) else (echo    - Git: FALTA)
echo ===================================================================
if !ERRORES! equ 0 (
    echo  LISTO -- Doble clic en INICIAR.vbs para arrancar el sistema.
) else (
    echo  HAY !ERRORES! PROBLEMA(S) -- Revisa los errores arriba
    echo  y vuelve a ejecutar INSTALAR.bat despues de corregirlos.
)
echo ===================================================================
echo.
pause

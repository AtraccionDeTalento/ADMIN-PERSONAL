@echo off
title Actualizando Sistema DJ Quinta
echo ===================================================
echo   Buscando actualizaciones del sistema...
echo ===================================================

:: Comprobar si Git esta instalado
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Git no esta instalado en este equipo.
    echo Ejecutando INSTALAR.bat para configurar dependencias y Git...
    call "%~dp0INSTALAR.bat"
    
    where git >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] No se pudo instalar Git automaticamente.
        echo No se pueden buscar actualizaciones automaticamente.
        timeout /t 3 >nul
        exit /b 1
    )
)

:: Comprobar si es un repositorio Git
if not exist ".git" (
    echo [ADVERTENCIA] La carpeta no es un repositorio Git clonado.
    echo No se pueden buscar actualizaciones automaticamente.
    echo Por favor, usa "git clone" la primera vez en lugar de descargar el ZIP.
    timeout /t 4 >nul
    exit /b 1
)

echo Descargando ultimos cambios...
git pull origin main

echo.
echo Actualizacion finalizada. Iniciando el sistema...
timeout /t 2 >nul
exit /b 0

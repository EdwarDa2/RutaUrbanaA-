@echo off
setlocal
cd /d "%~dp0"
title RutaUrbana A* - Generador de Ejecutable (.EXE)

echo ========================================================
echo   RutaUrbana A* - Generador de Ejecutable Windows (.exe)
echo ========================================================
echo.
echo Este script creara un archivo .exe independiente en la carpeta 'dist'
echo que podras compartir y ejecutar en cualquier computadora con Windows
echo sin necesidad de instalar Python ni dependencias.
echo.

set PY_CMD=python
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if not errorlevel 1 (
        set PY_CMD=py
    )
)

echo 1. Verificando o instalando PyInstaller...
%PY_CMD% -m pip install pyinstaller

echo.
echo 2. Compilando RutaUrbanaAstar.exe (puede demorar unos momentos)...
%PY_CMD% -m PyInstaller --noconfirm --onedir --windowed ^
    --name "RutaUrbanaAstar" ^
    --add-data "datos;datos" ^
    --add-data "ui;ui" ^
    --add-data "analytics;analytics" ^
    app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la compilacion con PyInstaller.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   ¡Ejecutable generado con exito!
echo   Ubicacion: dist\RutaUrbanaAstar\RutaUrbanaAstar.exe
echo ========================================================
echo.
pause
endlocal


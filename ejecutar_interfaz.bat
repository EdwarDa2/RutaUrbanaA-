@echo off
setlocal
cd /d "%~dp0"
title RutaUrbana A* - Interfaz Grafica

echo ========================================================
echo        RutaUrbana A* - Planificador Multicriterio
echo ========================================================
echo Detectando entorno de Python...

:: Detectar comando python disponible
set PY_CMD=python
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] No se encontro Python en el sistema.
        echo Por favor instala Python 3.10 o superior desde https://www.python.org/
        pause
        exit /b 1
    ) else (
        set PY_CMD=py
    )
)

:: Verificar dependencias basicas
%PY_CMD% -c "import matplotlib, tkinter" >nul 2>&1
if errorlevel 1 (
    echo Instalando librerias necesarias (matplotlib, pytest)...
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Ocurrio un fallo al instalar las dependencias.
        pause
        exit /b 1
    )
)

echo Iniciando la aplicacion grafica...
%PY_CMD% app.py

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion se cerro inesperadamente.
    pause
)
endlocal

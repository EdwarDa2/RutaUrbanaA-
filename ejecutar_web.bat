@echo off
setlocal
cd /d "%~dp0"
title RutaUrbana A* - Web Dashboard

echo ========================================================
echo   RutaUrbana A* - Web Dashboard Moderno (Streamlit)
echo ========================================================
echo Detectando entorno de Python...

set PY_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] No se encontro Python en el sistema.
        pause
        exit /b 1
    )
    set PY_CMD=py
)

REM Desactivar solicitud de email de Streamlit en primer inicio
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>&1
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    echo [general]> "%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "">> "%USERPROFILE%\.streamlit\credentials.toml"
)

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_HEADLESS=false

REM Verificar librerias necesarias
%PY_CMD% -c "import streamlit, plotly" >nul 2>&1
if errorlevel 1 goto INSTALAR_DEPS
goto LIBERAR_PUERTO

:INSTALAR_DEPS
echo Instalando dependencias necesarias...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

:LIBERAR_PUERTO
REM Liberar puerto 8501 si un proceso previo colgado lo retiene
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr :8501 ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>&1
)

:INICIAR_APP
echo.
echo Iniciando Dashboard Web interactivo en tu navegador...
echo Si no abre automaticamente, ingresa a: http://localhost:8501
echo Para detener el servidor, cierra esta ventana o presiona Ctrl+C.
echo.

%PY_CMD% -m streamlit run web_app.py

if errorlevel 1 (
    echo.
    echo [ERROR] El servidor web se cerro con error.
    pause
)
endlocal

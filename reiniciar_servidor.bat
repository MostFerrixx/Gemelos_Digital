@echo off
REM =========================================================================
REM Script: reiniciar_servidor.bat
REM Descripcion: Reinicio FORZADO en un solo paso.
REM   1) Borra server.pid (puede estar obsoleto)
REM   2) Mata TODO proceso que escuche en el puerto 8000 (arbol completo /T)
REM   3) Arranca el servidor via start_server.bat
REM Uso: doble clic. Si pide permisos, ejecutar como administrador.
REM =========================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================================
echo  GEMELOS DIGITAL - Reinicio forzado del servidor (puerto 8000)
echo ========================================================================
echo.

REM 1) Limpiar PID file obsoleto
if exist "server.pid" (
    del "server.pid" >nul 2>&1
    echo [INFO] server.pid eliminado.
)

REM 2) Matar todo lo que escuche en el puerto 8000 (arbol completo)
set "FOUND_ANY=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000.*LISTENING"') do (
    set "FOUND_ANY=1"
    echo [INFO] Matando proceso en puerto 8000: PID %%a ...
    taskkill /PID %%a /F /T >nul 2>&1
)
if "!FOUND_ANY!"=="0" (
    echo [INFO] Puerto 8000 ya estaba libre.
) else (
    echo [OK] Puerto 8000 liberado.
)

REM 3) Verificar que quedo libre, con REINTENTOS (Windows tarda en soltar el
REM    socket tras el kill; verificar de inmediato da falso "sigue ocupado")
set "PORT_FREE=0"
for /l %%i in (1,1,5) do (
    if "!PORT_FREE!"=="0" (
        timeout /t 2 /nobreak >nul
        netstat -ano 2>nul | findstr ":8000.*LISTENING" >nul
        if !errorlevel! neq 0 (
            set "PORT_FREE=1"
        ) else (
            echo [INFO] Puerto aun ocupado, reintentando verificacion (%%i/5)...
        )
    )
)
if "!PORT_FREE!"=="0" (
    echo [ERROR] El puerto 8000 SIGUE ocupado tras 10s. Procesos:
    netstat -ano | findstr ":8000.*LISTENING"
    echo Identifica el proceso:  tasklist /FI "PID eq <pid_de_arriba>"
    pause
    exit /b 1
)

REM 4) Arrancar el servidor
echo [INFO] Arrancando servidor...
call start_server.bat
exit /b 0

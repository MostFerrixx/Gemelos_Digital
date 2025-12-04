@echo off
REM =========================================================================
REM Script: stop_server.bat
REM Descripcion: Detiene el servidor web en ejecucion
REM =========================================================================

setlocal enabledelayedexpansion

REM Configuracion
set "PID_FILE=server.pid"

echo ========================================================================
echo  GEMELOS DIGITAL - Detener Servidor Web
echo ========================================================================
echo.

REM Verificar si existe el archivo PID
if not exist "%PID_FILE%" (
    echo [INFO] No hay servidor ejecutandose
    echo El archivo PID no existe: %PID_FILE%
    echo.
    pause
    exit /b 0
)

REM Leer el PID del archivo
set /p SERVER_PID=<"%PID_FILE%"

REM Verificar si el proceso esta realmente ejecutandose
tasklist /FI "PID eq %SERVER_PID%" 2>nul | find "%SERVER_PID%" >nul
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] El proceso PID %SERVER_PID% no esta ejecutandose
    echo Limpiando archivo PID...
    del "%PID_FILE%" >nul 2>&1
    echo.
    pause
    exit /b 0
)

REM Terminar el proceso
echo [INFO] Deteniendo servidor (PID: %SERVER_PID%)...
taskkill /PID %SERVER_PID% /F >nul 2>&1

if %errorlevel% equ 0 (
    echo [EXITO] Servidor detenido exitosamente
    del "%PID_FILE%" >nul 2>&1
    echo.
    echo El servidor ha sido detenido correctamente.
) else (
    echo [ERROR] No se pudo detener el servidor
    echo Es posible que necesites permisos de administrador
    echo.
    pause
    exit /b 1
)

echo.
pause
exit /b 0

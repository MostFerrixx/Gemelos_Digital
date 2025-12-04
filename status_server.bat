@echo off
REM =========================================================================
REM Script: status_server.bat
REM Descripcion: Verifica el estado del servidor web
REM =========================================================================

setlocal enabledelayedexpansion

REM Configuracion
set "PID_FILE=server.pid"
set "SERVER_PORT=8000"
set "SERVER_URL=http://localhost:%SERVER_PORT%"

echo ========================================================================
echo  GEMELOS DIGITAL - Estado del Servidor Web
echo ========================================================================
echo.

REM Verificar si existe el archivo PID
if not exist "%PID_FILE%" (
    echo [ESTADO] DETENIDO
    echo.
    echo El servidor no esta ejecutandose.
    echo Para iniciarlo, ejecuta: start_server.bat
    echo.
    pause
    exit /b 0
)

REM Leer el PID del archivo
set /p SERVER_PID=<"%PID_FILE%"

REM Verificar si el proceso esta realmente ejecutandose
tasklist /FI "PID eq %SERVER_PID%" 2>nul | find "%SERVER_PID%" >nul
if %errorlevel% neq 0 (
    echo [ESTADO] ERROR - Proceso no encontrado
    echo.
    echo El archivo PID existe pero el proceso %SERVER_PID% no esta ejecutandose.
    echo Esto puede ocurrir si el servidor se cerro inesperadamente.
    echo.
    echo Ejecuta start_server.bat para iniciar el servidor.
    echo.
    pause
    exit /b 1
)

REM El servidor esta ejecutandose - mostrar informacion
echo [ESTADO] EJECUTANDOSE
echo.
echo   PID:         %SERVER_PID%
echo   URL:         %SERVER_URL%
echo   Config URL:  %SERVER_URL%/web_configurator/
echo.

REM Obtener informacion del proceso
for /f "tokens=*" %%i in ('wmic process where "ProcessId=%SERVER_PID%" get CreationDate /value 2^>nul ^| find "="') do set "%%i"
if defined CreationDate (
    set "START_TIME=!CreationDate:~0,4!-!CreationDate:~4,2!-!CreationDate:~6,2! !CreationDate:~8,2!:!CreationDate:~10,2!:!CreationDate:~12,2!"
    echo   Iniciado:    !START_TIME!
)

REM Ver uso de memoria
for /f "tokens=5" %%i in ('tasklist /FI "PID eq %SERVER_PID%" /NH 2^>nul') do (
    echo   Memoria:     %%i KB
)

echo.
echo ========================================================================
echo  El servidor esta funcionando correctamente
echo ========================================================================
echo.
echo  Para detenerlo:  stop_server.bat
echo  Para reiniciar:  restart_server.bat
echo  Ver logs:        type logs\server.log
echo.

pause
exit /b 0

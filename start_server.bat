@echo off
REM =========================================================================
REM Script: start_server.bat
REM Descripcion: Inicia el servidor web en segundo plano sin ventana terminal
REM =========================================================================

setlocal enabledelayedexpansion

REM Configuracion
set "SERVER_SCRIPT=web_prototype\server.py"
set "PID_FILE=server.pid"
set "LOG_DIR=logs"
set "SERVER_LOG=%LOG_DIR%\server.log"
set "ERROR_LOG=%LOG_DIR%\server_errors.log"
set "SERVER_PORT=8000"
set "SERVER_URL=http://localhost:%SERVER_PORT%"

echo ========================================================================
echo  GEMELOS DIGITAL - Iniciar Servidor Web
echo ========================================================================
echo.

REM Verificar si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH
    echo Por favor, instala Python desde https://www.python.org/
    pause
    exit /b 1
)

REM Verificar si el servidor ya esta ejecutandose
if exist "%PID_FILE%" (
    set /p EXISTING_PID=<"%PID_FILE%"
    tasklist /FI "PID eq !EXISTING_PID!" 2>nul | find "!EXISTING_PID!" >nul
    if !errorlevel! equ 0 (
        echo [ADVERTENCIA] El servidor ya esta ejecutandose (PID: !EXISTING_PID!)
        echo Para detenerlo, ejecuta: stop_server.bat
        echo.
        pause
        exit /b 0
    ) else (
        echo [INFO] Limpiando archivo PID antiguo...
        del "%PID_FILE%" >nul 2>&1
    )
)

REM Crear directorio de logs si no existe
if not exist "%LOG_DIR%" (
    echo [INFO] Creando directorio de logs...
    mkdir "%LOG_DIR%"
)

REM Iniciar el servidor en segundo plano usando pythonw.exe
echo [INFO] Iniciando servidor en segundo plano...
echo [INFO] Auto-reload: ACTIVADO (Reinicia al guardar cambios)
echo [INFO] Script: %SERVER_SCRIPT%
echo [INFO] Logs: %SERVER_LOG%
echo.

REM Usar pythonw.exe para ejecutar sin ventana de consola
start /B pythonw.exe "%SERVER_SCRIPT%" > "%SERVER_LOG%" 2> "%ERROR_LOG%"

REM Esperar un momento para que el proceso inicie
timeout /t 2 /nobreak >nul

REM Obtener el PID del proceso Python mas reciente
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq pythonw.exe" /NH 2^>nul ^| find "pythonw.exe"') do (
    set "SERVER_PID=%%i"
    goto :found_pid
)

:found_pid
if defined SERVER_PID (
    echo %SERVER_PID% > "%PID_FILE%"
    echo [EXITO] Servidor iniciado exitosamente!
    echo.
    echo   PID:        %SERVER_PID%
    echo   URL:        %SERVER_URL%
    echo   Logs:       %SERVER_LOG%
    echo   Errores:    %ERROR_LOG%
    echo.
    echo ========================================================================
    echo  El servidor esta ejecutandose en segundo plano
    echo ========================================================================
    echo.
    echo  Para detener el servidor: stop_server.bat
    echo  Para ver el estado:        status_server.bat
    echo  Para reiniciar:            restart_server.bat
    echo.
    
    REM Preguntar si desea abrir el navegador
    set /p OPEN_BROWSER="Desea abrir el navegador ahora? (S/N): "
    if /i "!OPEN_BROWSER!"=="S" (
        echo [INFO] Abriendo navegador...
        start "" "%SERVER_URL%/web_configurator/"
    )
) else (
    echo [ERROR] No se pudo obtener el PID del servidor
    echo Verifica los logs en: %ERROR_LOG%
    pause
    exit /b 1
)

echo.
pause
exit /b 0

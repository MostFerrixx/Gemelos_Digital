@echo off
setlocal EnableDelayedExpansion

REM Configuracion
set "SERVER_SCRIPT=web_prototype\server.py"
set "LOG_DIR=logs"
set "SERVER_LOG=%LOG_DIR%\server.log"
set "ERROR_LOG=%LOG_DIR%\server_errors.log"
set "PID_FILE=server.pid"
set "SERVER_URL=http://localhost:8000"

REM Titulo de la ventana
title Gemelos Digital - Iniciar Servidor Web

echo ========================================================================
echo  GEMELOS DIGITAL - Iniciar Servidor Web
echo ========================================================================
echo.

REM ============================================================
REM DETECCION ROBUSTA DE INSTANCIAS DUPLICADAS
REM ============================================================

set "SERVER_ALIVE=0"

REM Paso 1: Verificar si existe archivo PID
if exist "%PID_FILE%" (
    set /p EXISTING_PID=<"%PID_FILE%"
    
    REM Paso 2: Verificar si el PID corresponde a python.exe (validacion estricta)
    set "IS_PYTHON=0"
    for /f "tokens=1" %%a in ('tasklist /FI "PID eq !EXISTING_PID!" /FI "IMAGENAME eq python.exe" /NH 2^>nul ^| find "python.exe"') do (
        set "IS_PYTHON=1"
    )
    
    REM Paso 3: Verificar si el puerto 8000 esta en LISTENING (source of truth)
    set "PORT_LISTENING=0"
    netstat -ano 2>nul | findstr ":8000.*LISTENING" >nul
    if !errorlevel! equ 0 set "PORT_LISTENING=1"
    
    REM Paso 4: Logica de Auto-Healing
    if "!IS_PYTHON!"=="1" if "!PORT_LISTENING!"=="1" (
        REM Escenario B: Servidor VIVO (python.exe + puerto ocupado)
        set "SERVER_ALIVE=1"
    ) else (
        REM Escenario A: PID es basura (no es python.exe O puerto libre)
        echo [INFO] Limpiando archivo PID obsoleto...
        del "%PID_FILE%" >nul 2>&1
    )
)

REM Paso 5: Si no hay PID file, verificar puerto por si acaso
if "!SERVER_ALIVE!"=="0" (
    netstat -ano 2>nul | findstr ":8000.*LISTENING" >nul
    if !errorlevel! equ 0 (
        echo [ADVERTENCIA] El puerto 8000 ya esta en uso por otro proceso.
        echo Use stop_server.bat o cierre manualmente el proceso que ocupa el puerto.
        pause
        exit /b 1
    )
)

REM Paso 6: Mostrar menu SOLO si el servidor esta realmente vivo
if "!SERVER_ALIVE!"=="1" (
    echo [ADVERTENCIA] Ya hay un servidor corriendo con PID !EXISTING_PID!
    echo.
    echo Opciones:
    echo   1. Reiniciar (detener el actual e iniciar uno nuevo^)
    echo   2. Salir (dejar el servidor actual^)
    echo.
    set /p CHOICE="Seleccione opcion (1/2): "
    
    if "!CHOICE!"=="1" (
        echo [INFO] Deteniendo servidor existente...
        taskkill /F /PID !EXISTING_PID! >nul 2>&1
        timeout /t 2 /nobreak >nul
        del "%PID_FILE%" >nul 2>&1
        echo [INFO] Servidor detenido. Continuando con inicio...
    ) else if "!CHOICE!"=="2" (
        echo [INFO] Operacion cancelada. El servidor sigue corriendo.
        echo   URL: %SERVER_URL%
        echo   PID: !EXISTING_PID!
        pause
        exit /b 0
    ) else (
        echo [ERROR] Opcion invalida. Saliendo...
        pause
        exit /b 1
    )
)

REM ============================================================

REM Crear directorio de logs si no existe
if not exist "%LOG_DIR%" (
    echo [INFO] Creando directorio de logs...
    mkdir "%LOG_DIR%"
)

REM Limpiar logs de sesion anterior
if exist "%LOG_DIR%" (
    echo [INFO] Limpiando logs de sesion anterior...
    del /Q "%LOG_DIR%\*.log" >nul 2>&1
)

echo [INFO] Iniciando servidor en segundo plano (invisible)...
echo [INFO] Auto-reload: ACTIVADO
echo [INFO] Logs: %SERVER_LOG%
echo.

REM Ejecutar el lanzador Python (invisible)
REM start_hidden.py usa CREATE_NO_WINDOW y redirige logs
pythonw.exe start_hidden.py

REM Esperar a que el proceso inicie
echo [INFO] Esperando inicializacion (3s)...
timeout /t 3 /nobreak >nul

REM Capturar PID del proceso python.exe (hijo) mas reciente
set "SERVER_PID="
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /NH 2^>nul ^| find "python.exe"') do (
    set "SERVER_PID=%%i"
)

if defined SERVER_PID (
    echo %SERVER_PID% > "%PID_FILE%"
    echo [EXITO] Servidor iniciado en segundo plano
    echo   PID: %SERVER_PID%
    echo   URL: %SERVER_URL%
    
    REM Validar que los logs tengan contenido
    for %%A in ("%SERVER_LOG%") do if %%~zA==0 (
        echo [ADVERTENCIA] El log esta vacio. Verifique %ERROR_LOG% si falla.
    )
) else (
    echo [ERROR] No se pudo capturar el PID. El servidor pudo haber fallado al iniciar.
    echo Revise %ERROR_LOG% para mas detalles.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo  El servidor esta ejecutandose en segundo plano
echo ========================================================================
echo.
echo  Para detener el servidor: stop_server.bat
echo  Para ver el estado:        status_server.bat
echo  Para reiniciar:            restart_server.bat
echo.

REM Preguntar si abrir el navegador
set /p OPEN_BROWSER="Desea abrir el navegador ahora? (S/N): "
if /i "%OPEN_BROWSER%"=="S" (
    start %SERVER_URL%
)

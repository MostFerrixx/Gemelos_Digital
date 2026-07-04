@echo off
REM Script de conveniencia para Gemelo Digital (Windows)
REM NOTA: las GUI de escritorio (Pygame/PyQt6/Tkinter) fueron deprecadas y
REM archivadas en _legacy\gui_escritorio\. La GUI vigente es la web.

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="sim" goto sim
if "%1"=="web" goto web
if "%1"=="test" goto test
if "%1"=="gate" goto gate
if "%1"=="clean" goto clean
goto unknown

:help
echo === GEMELO DIGITAL - COMANDOS DISPONIBLES ===
echo.
echo   .\run sim    - Generar replay (.jsonl) + reportes (headless)
echo   .\run web    - Iniciar la GUI web (http://localhost:8000)
echo   .\run test   - Suite pytest de red de seguridad (rapida, ^<10 s)
echo   .\run gate   - Gate de regresion byte-identico (~30 s)
echo   .\run clean  - Limpiar archivos temporales
echo.
echo NOTA: En PowerShell usa .\run (con punto y barra)
echo.
goto end

:test
python -m pytest -q
goto end

:gate
python scripts\regression_gate.py
goto end

:sim
echo Generando archivo de replay...
python entry_points\run_generate_replay.py
goto end

:web
echo Iniciando servidor web en http://localhost:8000 ...
call start_server.bat
goto end

:clean
echo Limpiando archivos temporales...
if exist __pycache__ rmdir /s /q __pycache__
if exist src\__pycache__ rmdir /s /q src\__pycache__
for /r %%i in (*.pyc) do del /q "%%i"
echo Limpieza completada
goto end

:unknown
echo Comando desconocido: %1
echo Usa 'run help' para ver comandos disponibles
goto end

:end

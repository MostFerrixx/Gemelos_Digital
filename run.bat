@echo off
REM Script de conveniencia para Gemelo Digital (Windows)
REM Alternativa a Makefile para sistemas Windows

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="sim" goto sim
if "%1"=="sim-visual" goto sim-visual
if "%1"=="replay" goto replay
if "%1"=="config" goto config
if "%1"=="test" goto test
if "%1"=="clean" goto clean
goto unknown

:help
echo === GEMELO DIGITAL - COMANDOS DISPONIBLES ===
echo.
echo   .\run sim          - Ejecutar simulacion headless (sin UI)
echo   .\run sim-visual   - Ejecutar simulacion con interfaz grafica
echo   .\run replay ^<archivo.jsonl^> - Ver replay de simulacion
echo   .\run config       - Abrir configurador de simulacion
echo   .\run test         - Ejecutar test rapido (3 ordenes)
echo   .\run clean        - Limpiar archivos temporales
echo.
echo Ejemplos:
echo   .\run sim
echo   .\run replay output\simulation_20250115_120000\replay_events_20250115_120000.jsonl
echo.
echo NOTA: En PowerShell usa .\run (con punto y barra)
echo.
goto end

:sim
echo Ejecutando simulacion headless...
python entry_points\run_live_simulation.py --headless
goto end

:sim-visual
echo Ejecutando simulacion con interfaz grafica...
python entry_points\run_live_simulation.py
goto end

:replay
if "%2"=="" (
    echo Error: Debes especificar el archivo .jsonl
    echo Ejemplo: run replay output\simulation_*\replay_events_*.jsonl
    goto end
)
echo Ejecutando replay viewer...
python entry_points\run_replay_viewer.py %2
goto end

:config
echo Abriendo configurador...
python configurator.py
goto end

:test
echo Ejecutando test rapido (3 ordenes)...
python test_quick_jsonl.py
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


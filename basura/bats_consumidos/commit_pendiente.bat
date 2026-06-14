@echo off
REM =========================================================================
REM Script: commit_pendiente.bat  (un solo uso; borrar despues)
REM Commitea TODO el trabajo pendiente de la sesion:
REM   toggles motor avanzado + mini-fix reservas pallet + telemetria +
REM   scripts de servidor + docs de calibracion (investigacion + impacto)
REM =========================================================================
setlocal
cd /d "%~dp0"

echo ========================================================================
echo  GEMELOS DIGITAL - Commit del trabajo pendiente
echo ========================================================================
echo.

REM Limpiar lock zombi si existe (pasa con FUSE/sesiones cortadas)
if exist ".git\index.lock" (
    echo [INFO] Limpiando index.lock zombi...
    move ".git\index.lock" ".git\index.lock.bak" >nul 2>&1
)

echo [INFO] Agregando cambios...
git add -A

echo [INFO] Creando commit...
git commit -m "feat: toggles motor avanzado + mini-fix reservas pallet + telemetria outbound + scripts servidor + docs calibracion tiempos"

echo.
echo [INFO] Ultimos 3 commits:
git log --oneline -3
echo.
echo Si arriba aparece el commit nuevo, todo OK. Puedes borrar este .bat.
pause

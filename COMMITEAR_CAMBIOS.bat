@echo off
cd /d "D:\Documentos\Martin\Gemelos Digital"

echo.
echo ============================================================
echo   PASO 1: Limpiar el candado de Git (index.lock)
echo ============================================================
if exist ".git\index.lock" (
    del ".git\index.lock"
    echo   [OK] Candado eliminado.
) else (
    echo   [OK] No habia candado, todo bien.
)

echo.
echo ============================================================
echo   PASO 2: Ignorar archivos temporales de sincronizacion
echo ============================================================
git rm -r --cached --ignore-unmatch ".fuse_hidden*" >nul 2>&1
echo   [OK] Limpieza de archivos temporales lista.

echo.
echo ============================================================
echo   PASO 3: Agregar los cambios del proyecto
echo ============================================================
git add docs\
git add web_prototype\
git add src\
git add config.json
git add run_migration.py
git add visualizer.py
git add server_manager.py
git add COMMITEAR_CAMBIOS.bat
echo   [OK] Cambios registrados.

echo.
echo ============================================================
echo   PASO 4: Hacer el commit
echo ============================================================
git commit -m "chore: limpieza docs + fixes (F2.d, save_config, REG-06, MIG-03, WEB-05, E2E)"

echo.
echo ============================================================
echo   LISTO. Presiona cualquier tecla para cerrar.
echo ============================================================
pause

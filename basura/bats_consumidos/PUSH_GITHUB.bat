@echo off
cd /d "D:\Documentos\Martin\Gemelos Digital"

echo ============================================================
echo  PUSH_GITHUB.bat -- Repara rama y sube a GitHub
echo ============================================================
echo.

echo [1/5] Limpiando locks huerfanos...
del /q ".git\index.lock" 2>nul
del /q ".git\HEAD.lock" 2>nul
del /q ".git\logs\HEAD.lock" 2>nul
for /r ".git" %%f in (*.lock) do del /q "%%f" 2>nul
echo      Hecho.

echo.
echo [2/5] Eliminando tag corrupto...
del /q ".git\refs\tags\_locktest_tmp.lock.z5.3" 2>nul
echo      Hecho (o ya no existia).

echo.
echo [3/5] Reparando puntero de rama...
git update-ref refs/heads/feature/allocation-layer-v12.1 9af045527fc194eaa4cce222218c3a229c4296a5
if %errorlevel%==0 (
    echo      [OK] Rama apuntando a 9af04552.
) else (
    echo      [ERROR] update-ref fallo. Abortando.
    pause
    exit /b 1
)

echo.
echo [4/5] Log de verificacion:
git --no-pager log --oneline -5
echo.

echo [5/5] Push a GitHub...
git push -u origin feature/allocation-layer-v12.1
if %errorlevel%==0 (
    echo.
    echo [OK] Push exitoso. Rama disponible en GitHub.
) else (
    echo.
    echo [ERROR] Push fallo. Revisa credenciales o conexion.
)

echo.
pause

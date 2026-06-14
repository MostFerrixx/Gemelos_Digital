@echo off
cd /d "D:\Documentos\Martin\Gemelos Digital"

echo ============================================================
echo  REPARAR_GIT.bat -- Cerebellum Git Recovery
echo ============================================================
echo.

echo [1/4] Eliminando tag corrupto...
del /q ".git\refs\tags\_locktest_tmp.lock.z5.3" 2>nul
echo      Hecho (o ya no existia).

echo.
echo [2/4] Apuntando la rama al commit correcto...
git update-ref refs/heads/feature/allocation-layer-v12.1 9af045527fc194eaa4cce222218c3a229c4296a5
if %errorlevel%==0 (
    echo      [OK] Rama reparada.
) else (
    echo      [WARN] update-ref fallo. Intentando con archivo directo...
    echo 9af045527fc194eaa4cce222218c3a229c4296a5 > ".git\refs\heads\feature\allocation-layer-v12.1"
    echo      Archivo escrito manualmente.
)

echo.
echo [3/4] Verificando log...
git log --oneline -5
echo.

echo [4/4] Verificando tag corrupto eliminado...
git tag -l
echo.

echo ============================================================
echo  Si ves el commit "chore: limpieza docs + fixes..." arriba,
echo  el repo esta sano. Puedes borrar REPARAR_GIT.bat.
echo ============================================================
echo.
pause

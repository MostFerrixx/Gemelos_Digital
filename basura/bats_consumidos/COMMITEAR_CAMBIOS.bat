@echo off
cd /d "D:\Documentos\Martin\Gemelos Digital"

echo Limpiando locks huerfanos de Git...
del /q ".git\index.lock" 2>nul
del /q ".git\HEAD.lock" 2>nul
del /q ".git\logs\HEAD.lock" 2>nul
del /q ".git\refs\heads\*.lock" 2>nul
for /r ".git" %%f in (*.lock) do del /q "%%f" 2>nul
echo Locks eliminados.

echo.
echo Haciendo el commit...
git commit -m "chore: limpieza docs + fixes F2.d save_config REG-06 MIG-03 WEB-05 E2E"

echo.
echo Ultimos 3 commits:
git log --oneline -3

echo.
pause

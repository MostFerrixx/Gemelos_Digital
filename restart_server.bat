@echo off
REM =========================================================================
REM Script: restart_server.bat
REM Descripcion: Reinicia el servidor web (detiene y vuelve a iniciar)
REM =========================================================================

echo ========================================================================
echo  GEMELOS DIGITAL - Reiniciar Servidor Web
echo ========================================================================
echo.

echo [INFO] Deteniendo servidor...
call stop_server.bat

echo.
echo [INFO] Esperando 2 segundos...
timeout /t 2 /nobreak >nul

echo.
echo [INFO] Iniciando servidor...
call start_server.bat

exit /b 0

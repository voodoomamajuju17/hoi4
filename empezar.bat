@echo off
REM Doble click aca para instalar el mod. Ver EMPEZAR.md si algo falla.
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py empezar.py %*
    goto fin
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python empezar.py %*
    goto fin
)

echo.
echo   No encontre Python en esta computadora.
echo.
echo   QUE HACER: instalalo desde https://www.python.org/downloads/
echo   IMPORTANTE: durante la instalacion marca la casilla
echo   "Add Python to PATH", si no, esto no va a funcionar.
echo.

:fin
echo.
pause

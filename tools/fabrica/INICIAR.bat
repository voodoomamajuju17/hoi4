@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo NO SE ENCONTRO PYTHON. Instala Python 3 desde https://www.python.org/downloads/
  echo Durante la instalacion activa "Add Python to PATH".
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creando entorno del programa...
  %PY% -m venv .venv
  if errorlevel 1 (pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (echo Error instalando dependencias. & pause & exit /b 1)
.venv\Scripts\python.exe fabrica_hoi4.py
if errorlevel 1 pause

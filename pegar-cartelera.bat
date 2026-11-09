@echo off
REM Abre la ventana para pegar la cartelera copiada de la pagina de un cine (Cine Colombia,
REM cineclubes...) y guardarla en scrapers\manual.csv
cd /d "%~dp0"
call :buscar_python
if not defined PY (
  echo Python no esta instalado. Ejecuta primero instalar-scrapers.bat
  pause
  exit /b 1
)
set PYTHONIOENCODING=utf-8
%PY% scrapers\pegar_cartelera.py
if errorlevel 1 pause
exit /b

:buscar_python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b

@echo off
REM Actualiza la cartelera y la sube a GitHub. Registro en logs\actualizar.txt
cd /d "%~dp0"
if not exist logs mkdir logs
set PYTHONIOENCODING=utf-8
call :principal %* > logs\actualizar.txt 2>&1
type logs\actualizar.txt
timeout /t 15
exit /b

:principal
echo === %date% %time% ===
call :buscar_python
if not defined PY (
  echo ERROR: Python no esta instalado. Ejecuta primero instalar-scrapers.bat
  exit /b 1
)
cd scrapers
%PY% -u run.py %*
cd ..
if not exist app\www\data\funciones.json (
  echo ERROR: no se genero la cartelera.
  exit /b 1
)
git add app/www/data/funciones.json
git commit -m "Cartelera %date%"
git pull --no-rebase --no-edit
git push
echo === FIN codigo %errorlevel% ===
exit /b

:buscar_python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b

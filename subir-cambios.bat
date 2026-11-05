@echo off
REM Sube a GitHub todos los cambios del proyecto. Deja el registro en logs\subir.txt
cd /d "%~dp0"
if not exist logs mkdir logs
call :principal > logs\subir.txt 2>&1
type logs\subir.txt
timeout /t 15
exit /b

:principal
echo === %date% %time% ===
call :buscar_python
if not defined PY (
  echo ERROR: Python no esta instalado. Ejecuta primero instalar-scrapers.bat
  exit /b 1
)
set PYTHONIOENCODING=utf-8
%PY% -u scrapers\sincronizar.py "BogoCine: actualizacion del proyecto"
echo === FIN codigo %errorlevel% ===
exit /b

:buscar_python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b

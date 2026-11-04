@echo off
REM Instala lo necesario para los scrapers (una sola vez). Registro en logs\instalar.txt
cd /d "%~dp0"
if not exist logs mkdir logs
call :principal > logs\instalar.txt 2>&1
type logs\instalar.txt
timeout /t 15
exit /b

:principal
echo === %date% %time% ===
call :buscar_python
if defined PY goto :instalar
echo Python no esta instalado. Descargando Python 3.12 desde python.org...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile \"$env:TEMP\python-3.12.10-amd64.exe\""
if not exist "%TEMP%\python-3.12.10-amd64.exe" (
  echo ERROR: no se pudo descargar el instalador de Python.
  exit /b 1
)
echo Instalando Python para este usuario...
"%TEMP%\python-3.12.10-amd64.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=0 Include_test=0
echo Instalador termino con codigo %errorlevel%
call :buscar_python
if defined PY goto :instalar
echo ERROR: no se encontro Python despues de instalarlo.
exit /b 1
:instalar
echo Usando: %PY%
%PY% --version
%PY% -m pip install --upgrade pip
%PY% -m pip install -r scrapers\requirements.txt
%PY% -m playwright install chromium
echo === FIN codigo %errorlevel% ===
exit /b

:buscar_python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b

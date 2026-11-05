@echo off
REM Abre BogoCine en el navegador del PC (http://localhost:8000). Cierra esta ventana para apagarla.
cd /d "%~dp0app\www"
call :buscar_python
if not defined PY (
  echo Python no esta instalado. Ejecuta primero instalar-scrapers.bat
  pause
  exit /b 1
)
echo.
echo  BogoCine esta corriendo en http://localhost:8000
echo  Para verla como celular: en el navegador presiona F12 y luego Ctrl+Shift+M
echo  Cierra esta ventana para apagarla.
echo.
start "" http://localhost:8000
%PY% -m http.server 8000 --bind 127.0.0.1
exit /b

:buscar_python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b

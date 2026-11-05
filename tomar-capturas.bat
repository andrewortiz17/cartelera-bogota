@echo off
REM Toma las 6 capturas de pantalla para Google Play (quedan en play-store\capturas).
cd /d "%~dp0"
if not exist logs mkdir logs
call :buscar_python
if not defined PY (
  echo Python no esta instalado. Ejecuta primero instalar-scrapers.bat
  pause
  exit /b 1
)
echo Tomando capturas... (tarda menos de un minuto)
call :principal > logs\capturas.txt 2>&1
type logs\capturas.txt
start "" "%~dp0play-store\capturas"
pause
exit /b

:principal
echo === %date% %time% ===
set PYTHONIOENCODING=utf-8
%PY% -u play-store\tomar_capturas.py
echo === FIN codigo %errorlevel% ===
exit /b

:buscar_python
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b

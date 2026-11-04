@echo off
REM Instala lo necesario para los scrapers (una sola vez). Registro en logs\instalar.txt
cd /d "%~dp0"
if not exist logs mkdir logs
(
  echo === %date% %time% ===
  python --version
  python -m pip install -r scrapers\requirements.txt
  python -m playwright install chromium
  echo === FIN codigo %errorlevel% ===
) > logs\instalar.txt 2>&1
type logs\instalar.txt
timeout /t 15

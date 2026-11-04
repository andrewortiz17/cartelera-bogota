@echo off
REM Instala lo necesario para los scrapers (una sola vez)
cd /d "%~dp0scrapers"
python -m pip install -r requirements.txt
python -m playwright install chromium
pause

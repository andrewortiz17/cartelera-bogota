@echo off
REM Actualiza la cartelera y la sube a GitHub
cd /d "%~dp0scrapers"
python run.py %*
if errorlevel 1 goto fin
cd /d "%~dp0"
git add app/www/data/funciones.json
git commit -m "Cartelera %date%"
git push
:fin
pause

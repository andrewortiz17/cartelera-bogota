@echo off
REM Actualiza la cartelera y la sube a GitHub. Registro en logs\actualizar.txt
cd /d "%~dp0"
if not exist logs mkdir logs
set PYTHONIOENCODING=utf-8
(
  echo === %date% %time% ===
  cd scrapers
  python run.py %*
  cd ..
  git add app/www/data/funciones.json
  git commit -m "Cartelera %date%"
  git pull --no-rebase --no-edit
  git push
  echo === FIN codigo %errorlevel% ===
) > logs\actualizar.txt 2>&1
type logs\actualizar.txt
timeout /t 15

@echo off
REM Sube a GitHub todos los cambios del proyecto. Deja el registro en logs\subir.txt
cd /d "%~dp0"
if not exist logs mkdir logs
(
  echo === %date% %time% ===
  git add -A
  git commit -m "BogoCine: actualizacion del proyecto"
  git pull --no-rebase --no-edit
  git push
  echo === FIN codigo %errorlevel% ===
) > logs\subir.txt 2>&1
type logs\subir.txt
timeout /t 15

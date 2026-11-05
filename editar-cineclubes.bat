@echo off
REM Abre en Excel la hoja de funciones escritas a mano (cineclubes y salas sin web)
REM y la lista de ids de las salas. Guarda la hoja como CSV al terminar.
cd /d "%~dp0scrapers"
start "" "salas-ids.csv"
start "" "manual.csv"
exit /b

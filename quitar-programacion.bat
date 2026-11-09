@echo off
REM Quita las actualizaciones automaticas programadas por programar-actualizacion.bat
schtasks /Delete /F /TN "QueDan - cartelera manana"
schtasks /Delete /F /TN "QueDan - cartelera tarde"
pause

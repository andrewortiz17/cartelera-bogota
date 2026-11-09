@echo off
REM Programa en Windows la actualizacion de Procinal y Royal Films todos los dias a las 7:00 a. m.
REM y a la 1:00 p. m. (esas dos webs no responden desde los servidores de GitHub).
REM Solo corre si el PC esta prendido. Para quitarla: quitar-programacion.bat
cd /d "%~dp0"
schtasks /Create /F /TN "QueDan - cartelera manana" /SC DAILY /ST 07:00 /TR "\"%~dp0actualizar-cartelera.bat\" procinal royal_films"
schtasks /Create /F /TN "QueDan - cartelera tarde" /SC DAILY /ST 13:00 /TR "\"%~dp0actualizar-cartelera.bat\" procinal royal_films"
echo.
echo Listo. Puedes verlas en el Programador de tareas de Windows (buscan "QueDan").
pause

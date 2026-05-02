@echo off
echo Parando servidores do WealthMap Analytics PRO...

:: Encerra os processos associados aos titulos das janelas
taskkill /FI "WindowTitle eq WealthMap Backend*" /T /F
taskkill /FI "WindowTitle eq WealthMap Frontend*" /T /F

echo.
echo Servidores parados com sucesso!
pause

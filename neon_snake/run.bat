@echo off
echo Iniciando Neon Snake...
echo.

echo [1/2] Iniciando backend Go (porta 8080)...
start "Neon Snake API" cmd /k "cd /d "%~dp0backend" && go run ./cmd/api/main.go"

timeout /t 2 /nobreak >nul

echo [2/2] Abrindo jogo...
start "" "%~dp0frontend\index.html"

echo.
echo Neon Snake iniciado!
echo   API:  http://localhost:8080
echo   Jogo: frontend\index.html

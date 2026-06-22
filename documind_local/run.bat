@echo off
echo Iniciando DocuMind Local...
echo.

echo [1/2] Iniciando backend Go + Python (porta 8080)...
start "DocuMind API" cmd /k "cd /d "%~dp0backend" && go run ./cmd/api/main.go"

timeout /t 3 /nobreak >nul

echo [2/2] Abrindo interface web...
start "" "http://localhost:8080"

echo.
echo DocuMind iniciado!
echo   Interface: http://localhost:8080
echo.
echo Para parar: feche a janela "DocuMind API"

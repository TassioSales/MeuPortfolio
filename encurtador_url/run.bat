@echo off
echo Iniciando Encurtador de URL...
echo.

echo [1/2] Iniciando backend Go (porta 8080)...
start "Encurtador API" cmd /k "cd /d "%~dp0backend" && go run ./cmd/api/main.go"

timeout /t 2 /nobreak >nul

echo [2/2] Iniciando frontend Next.js (porta 3000)...
start "Encurtador Frontend" cmd /k "cd /d "%~dp0frontend" && npm install && npm run dev"

echo.
echo Servicos iniciados!
echo   Backend:  http://localhost:8080
echo   Frontend: http://localhost:3000
echo.
timeout /t 5 /nobreak >nul
start "" "http://localhost:3000"

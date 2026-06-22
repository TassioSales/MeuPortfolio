@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   Encurtador de URL - Rastreamento e Analytics
echo ============================================
echo.

where go >nul 2>&1
if errorlevel 1 ( echo [ERRO] Go nao encontrado no PATH. & pause & exit /b 1 )
where npm >nul 2>&1
if errorlevel 1 ( echo [ERRO] npm nao encontrado no PATH. & pause & exit /b 1 )

echo [1/2] Iniciando backend Go (porta 8080)...
start "Encurtador - API" /d "%~dp0backend" cmd /k "go run ./cmd/api/main.go"

timeout /t 3 /nobreak >nul

echo [2/2] Iniciando frontend Next.js (porta 3000)...
start "Encurtador - Frontend" /d "%~dp0frontend" cmd /k "npm install && npm run dev"

echo.
echo Servicos iniciados!
echo   Backend:  http://localhost:8080
echo   Frontend: http://localhost:3000
echo.
timeout /t 6 /nobreak >nul
start "" "http://localhost:3000"

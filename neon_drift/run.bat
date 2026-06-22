@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   Neon Drift - Jogo de Corrida
echo ============================================
echo.

where go >nul 2>&1
if errorlevel 1 ( echo [ERRO] Go nao encontrado no PATH. & pause & exit /b 1 )

echo [1/2] Iniciando backend Go (porta 8080)...
start "Neon Drift - API" /d "%~dp0backend" cmd /k "go run ./cmd/api/main.go"

timeout /t 3 /nobreak >nul

echo [2/2] Abrindo jogo no navegador...
start "" "%~dp0frontend\index.html"

echo.
echo Neon Drift iniciado!
echo   API:  http://localhost:8080
echo   Jogo: frontend\index.html

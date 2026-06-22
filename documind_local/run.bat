@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   DocuMind Local - Assistente de Documentos
echo ============================================
echo.

where go >nul 2>&1
if errorlevel 1 ( echo [ERRO] Go nao encontrado no PATH. & pause & exit /b 1 )

echo Iniciando servidor Go (porta 8080)...
start "DocuMind - API" /d "%~dp0backend" cmd /k "go run ./cmd/api/main.go"

timeout /t 4 /nobreak >nul
start "" "http://localhost:8080"

echo.
echo DocuMind iniciado!
echo   Interface: http://localhost:8080
echo.
echo Para parar: feche a janela "DocuMind - API"

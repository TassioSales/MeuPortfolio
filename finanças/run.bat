@echo off
chcp 65001 >nul 2>&1
title Finanças - Dashboard de Investimentos

echo ==========================================
echo    Finanças - Dashboard de Investimentos
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado no PATH.
    pause
    exit /b 1
)

python -c "import waitress" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependências...
    pip install -r requirements.txt
)

echo.
echo [INFO] Iniciando aplicação (Porta 8080)...
echo [INFO] Pressione CTRL+C para encerrar.
echo.

python run_app.py
pause

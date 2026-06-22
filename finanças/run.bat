@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Financas - Dashboard de Investimentos

echo ============================================
echo   Financas - Dashboard de Investimentos
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  pause
  exit /b 1
)

python -c "import waitress" >nul 2>&1
if errorlevel 1 (
  echo [INFO] Instalando dependencias...
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
  )
)

echo [INFO] Iniciando aplicacao (Porta 8080)...
echo [INFO] Pressione CTRL+C para encerrar.
echo.
python run_app.py
pause

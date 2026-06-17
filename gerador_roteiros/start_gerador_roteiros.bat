@echo off
chcp 65001 >nul 2>&1
title Gerador de Roteiros de Viagem com IA

echo ==========================================
echo    Gerador de Roteiros de Viagem com IA
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias...
    pip install -r requirements.txt
)

echo.
echo [INFO] Iniciando aplicacao Streamlit...
echo [INFO] Pressione CTRL+C para encerrar.
echo.

streamlit run app.py
pause

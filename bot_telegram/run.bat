@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Bot Telegram - Assistente de Produtividade

echo ============================================
echo   Bot Telegram - Assistente de Produtividade
echo ============================================
echo.

REM Verifica .env
if not exist ".env" (
  echo [ERRO] Arquivo .env nao encontrado.
  echo Copie .env.example para .env e configure TELEGRAM_TOKEN.
  pause
  exit /b 1
)

REM Cria venv se nao existir
if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Criando ambiente virtual...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERRO] Falha ao criar venv. Verifique se Python esta instalado.
    pause
    exit /b 1
  )
  echo [OK] Ambiente virtual criado.
  echo.
)

REM Ativa venv e instala dependencias
echo [INFO] Instalando/verificando dependencias...
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias.
  pause
  exit /b 1
)

echo.
echo [OK] Tudo pronto. Iniciando o bot...
echo [INFO] Pressione Ctrl+C para parar.
echo.

python -m bot.main

pause

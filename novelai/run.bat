@echo off
title NovelAI
color 0A

set "BACK=C:\Users\tassi\OneDrive\Documentos\MeuPortfolio\novelai\backend"
set "FRONT=C:\Users\tassi\OneDrive\Documentos\MeuPortfolio\novelai\frontend"

echo.
echo  === NovelAI ===
echo.

echo [1] Preparando backend...
cd /d "%BACK%"

if not exist "venv\" (
    echo Criando venv...
    python -m venv venv
)

echo [2] Instalando dependencias...
"%BACK%\venv\Scripts\pip.exe" install -r requirements.txt -q --disable-pip-version-check

echo [3] Iniciando backend...
start "NovelAI Backend" "%BACK%\venv\Scripts\python.exe" main.py

timeout /t 3 /nobreak >nul

echo [4] Iniciando frontend...
start "NovelAI Frontend" cmd /k "cd /d C:\Users\tassi\OneDrive\Documentos\MeuPortfolio\novelai\frontend && npm run dev"

timeout /t 5 /nobreak >nul
start "" http://localhost:8000/docs

echo.
echo  Backend: http://localhost:8000
echo  Docs:    http://localhost:8000/docs
echo  Front:   http://localhost:5173
echo.
echo  LEMBRE: Docker Desktop deve estar rodando.
echo  Para subir banco: abra outro CMD e rode:
echo  cd novelai ^&^& docker-compose up -d db redis
echo.
pause

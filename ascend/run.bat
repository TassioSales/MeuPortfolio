@echo off
title Trilha - AI Career Coach

echo.
echo ========================================
echo   ASCEND - AI Career Coach
echo ========================================
echo.

set "ROOT=%~dp0"

:: Mata processos anteriores
echo [0/4] Encerrando processos anteriores...
taskkill /f /fi "WINDOWTITLE eq Trilha-Backend*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Trilha-Frontend*" > nul 2>&1
taskkill /f /im uvicorn.exe > nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /f /pid %%p > nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do taskkill /f /pid %%p > nul 2>&1
timeout /t 2 /nobreak > nul
echo [OK] Portas 8000 e 3000 liberadas.

:: Verifica Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale em https://python.org
    pause
    exit /b 1
)
echo [OK] Python: OK

:: Verifica Node.js
node --version > nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado. Instale em https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js: OK

:: Backend - cria venv
echo.
echo [1/4] Configurando backend...
cd /d "%ROOT%backend"

if not exist ".venv" (
    echo       Criando ambiente virtual Python...
    python -m venv .venv
)

call "%ROOT%backend\.venv\Scripts\activate.bat"

pip show fastapi > nul 2>&1
if errorlevel 1 (
    echo       Instalando dependencias Python...
    pip install -r requirements.txt
) else (
    echo       Dependencias Python OK.
)

:: Frontend - npm install
echo.
echo [2/4] Configurando frontend...
cd /d "%ROOT%frontend"

if not exist "node_modules" (
    echo       Instalando dependencias Node.js...
    npm install
) else (
    echo       Dependencias Node.js OK.
)

:: Volta para raiz
cd /d "%ROOT%"

:: Inicia backend em janela separada usando o bat auxiliar
echo.
echo [3/4] Iniciando backend na porta 8000...
start "Trilha-Backend" "%ROOT%start_backend.bat"

timeout /t 4 /nobreak > nul

:: Inicia frontend em janela separada
echo [4/4] Iniciando frontend na porta 3000...
start "Trilha-Frontend" "%ROOT%start_frontend.bat"

timeout /t 8 /nobreak > nul

echo.
echo  Backend:   http://localhost:8000
echo  Frontend:  http://localhost:3000
echo  Docs API:  http://localhost:8000/docs
echo.

start "" "http://localhost:3000"

echo Pressione qualquer tecla para encerrar os servidores...
pause > nul

echo Encerrando...
taskkill /f /fi "WINDOWTITLE eq Trilha-Backend*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Trilha-Frontend*" > nul 2>&1
echo Pronto!
timeout /t 2 > nul

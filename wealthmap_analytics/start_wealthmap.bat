@echo off
echo ==================================================
echo      INICIANDO WEALTHMAP ANALYTICS PRO
echo ==================================================
echo.

:: Inicia o Backend Python FastAPI em uma nova janela
echo [1/2] Iniciando Backend FastAPI na porta 8000...
start "WealthMap Backend" cmd /k "cd /d ""%~dp0backend"" && ""C:\Users\tassi\AppData\Local\Programs\Python\Python313\python.exe"" -m pip install --user -r requirements.txt && ""C:\Users\tassi\AppData\Local\Programs\Python\Python313\python.exe"" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Aguarda 2 segundos para dar tempo ao backend
timeout /t 2 /nobreak > nul

:: Inicia o Frontend Next.js em uma nova janela
echo [2/2] Iniciando Frontend Next.js na porta 3000...
start "WealthMap Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo Servidores iniciados! 
echo O navegador abrira automaticamente em 5 segundos...
timeout /t 5 /nobreak > nul
start http://localhost:3000

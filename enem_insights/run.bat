@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   ENEM Insights - Analise de Dados do ENEM
echo ============================================
echo.

where docker >nul 2>&1
if not errorlevel 1 (
  echo Usando Docker Compose...
  docker-compose up --build %*
  goto :eof
)

echo [AVISO] Docker nao encontrado. Executando com Python direto...
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo [1/3] Criando ambiente virtual...
  python -m venv .venv
  if errorlevel 1 ( echo [ERRO] Falha ao criar venv. & pause & exit /b 1 )
)

echo [2/3] Ativando ambiente virtual e instalando dependencias...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if errorlevel 1 ( echo [ERRO] Falha ao instalar dependencias. & pause & exit /b 1 )

echo [3/3] Iniciando aplicacao (porta 8501)...
streamlit run "🏠_Home.py" --server.port=8501 --browser.gatherUsageStats=false %*

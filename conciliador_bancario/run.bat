@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo   Conciliacao Bancaria
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  echo Instale o Python 3.11 ou superior e marque "Add to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo [1/3] Criando ambiente virtual...
  python -m venv .venv
  if errorlevel 1 ( echo [ERRO] Falha ao criar o ambiente virtual. ^& pause ^& exit /b 1 )
)

echo [2/3] Ativando ambiente e instalando dependencias...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if errorlevel 1 ( echo [ERRO] Falha ao instalar dependencias. ^& pause ^& exit /b 1 )

if /i "%~1"=="testes" (
  echo [3/3] Rodando os testes...
  python -m pytest tests -q
  pause
  exit /b %errorlevel%
)

if /i "%~1"=="avaliar" (
  echo [3/3] Medindo precisao e cobertura contra o gabarito...
  python avaliar.py
  pause
  exit /b %errorlevel%
)

echo [3/3] Iniciando a interface na porta 8504...
echo Sem arquivos seus? A aba "Dados de exemplo" gera um par para testar.
echo.
streamlit run app.py --server.port=8504 --browser.gatherUsageStats=false %*

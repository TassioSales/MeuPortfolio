@echo off
echo Iniciando ENEM Insights...
echo.

where docker >nul 2>nul
if errorlevel 1 goto :sem_docker

echo Usando Docker Compose...
docker-compose up --build %*
goto :eof

:sem_docker
echo Docker nao encontrado. Rodando com Python direto...
pip install -r requirements.txt
streamlit run "🏠_Home.py" --server.port=8501 --browser.gatherUsageStats=false

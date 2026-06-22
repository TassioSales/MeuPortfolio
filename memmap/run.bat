@echo off
echo Iniciando MemMap - Second Brain com Grafo de Conhecimento
echo ==========================================================
echo.
echo Servicos:
echo   NLP Service  -^> http://localhost:8001
echo   Go API       -^> http://localhost:8080
echo   Frontend     -^> http://localhost:3000
echo.
echo Iniciando com Docker Compose...

docker-compose up --build %*

@echo off
echo ==========================================
echo      Gerando Dados de Exemplo
echo ==========================================

if not exist venv (
    echo Erro: Ambiente virtual nao encontrado. Execute 'install.bat' primeiro.
    pause
    exit /b
)

call venv\Scripts\activate

echo Executando script de populacao...
python examples.py

echo.
pause

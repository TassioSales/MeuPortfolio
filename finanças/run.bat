@echo off
echo ==========================================
echo      Iniciando Servidor de Desenvolvimento
echo ==========================================

if not exist venv (
    echo Erro: Ambiente virtual nao encontrado. Execute 'install.bat' primeiro.
    pause
    exit /b
)

call venv\Scripts\activate

echo Aplicando migracoes do banco de dados...
python manage.py migrate

echo.
echo Servidor rodando em: http://127.0.0.1:8000
echo Pressione CTRL+C para parar.
echo.

python manage.py runserver

pause

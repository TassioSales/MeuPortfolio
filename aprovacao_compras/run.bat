@echo off
echo.
echo ==========================================
echo   CompraFlow - Aprovacao de Pedidos
echo ==========================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [!] Ambiente virtual nao encontrado. Criando...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo [1] Rodando migrations...
python manage.py migrate --run-syncdb

echo [2] Descobrindo IP local...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "169.254"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo ==========================================
echo   Acesso local:  http://127.0.0.1:8000
echo   Acesso na rede: http://%LOCAL_IP%:8000
echo ==========================================
echo.
echo   Login: admin / admin123  (superuser)
echo          lucas / lucas123  (aprovador)
echo          ana   / ana123    (comprador)
echo.
echo   Pressione Ctrl+C para parar.
echo.
python manage.py runserver 0.0.0.0:8000

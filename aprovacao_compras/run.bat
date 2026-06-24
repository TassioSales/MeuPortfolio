@echo off
chcp 65001 >nul
echo.
echo  ==========================================
echo    CompraBio - Aprovacao de Pedidos
echo    Bio Mundo
echo  ==========================================
echo.

cd /d "%~dp0"

:: Cria o ambiente virtual se nao existir
if not exist ".venv\Scripts\python.exe" (
    echo  [!] Ambiente virtual nao encontrado. Criando...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

:: Aplica migrations pendentes silenciosamente
echo  [1] Verificando banco de dados...
python manage.py migrate --run-syncdb >nul 2>&1

:: Abre o navegador apos 2 segundos (tempo do Django subir)
echo  [2] Iniciando servidor...
start "" /B cmd /C "timeout /t 2 >nul && start http://comprabio.local:8000"

echo.
echo  ==========================================
echo   Acesso:  http://comprabio.local:8000
echo  ==========================================
echo.
echo   Usuarios:
echo     admin          / admin123   (administrador)
echo     lucas.castilho / lucas123   (aprovador)
echo     junior.lima    / junior123  (comprador)
echo.
echo   Pressione Ctrl+C para encerrar.
echo.

python manage.py runserver 0.0.0.0:8000

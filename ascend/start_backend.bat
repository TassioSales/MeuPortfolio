@echo off
title Trilha-Backend
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo Sincronizando dependencias...
pip install -r requirements.txt --quiet
echo Criando usuario demo (se necessario)...
python seed.py
echo Iniciando servidor...
uvicorn main:app --reload --port 8000
pause

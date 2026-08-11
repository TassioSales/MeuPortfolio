@echo off
REM Atalho para instalar dependencias e transcrever.
REM Uso: dê dois cliques ou rode  run.bat
cd /d "%~dp0"

echo == Instalando dependencias (so na primeira vez) ==
python -m pip install -r requirements.txt

echo.
echo == Transcrevendo audios em dados\audios ==
python src\transcrever.py -m small

echo.
echo == Gerando relatorio de analise ==
python src\analisar.py

echo.
echo Pronto! Veja dados\saidas\transcricoes.txt e relatorio_analise.txt
pause

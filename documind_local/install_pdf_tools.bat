@echo off
setlocal

cd /d "%~dp0backend"

echo Criando ambiente Python em backend\.venv...
py -m venv .venv

echo Instalando bibliotecas de PDF...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Bibliotecas instaladas.
echo OCR com pytesseract tambem precisa do Tesseract instalado no Windows.
pause

endlocal

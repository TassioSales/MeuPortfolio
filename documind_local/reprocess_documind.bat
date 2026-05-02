@echo off
setlocal

cd /d "%~dp0backend"

echo Reprocessando documentos ja enviados...
go run ./cmd/reprocess
pause

endlocal

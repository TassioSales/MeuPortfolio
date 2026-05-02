@echo off
setlocal

cd /d "%~dp0"

echo Starting DocuMind Local at http://localhost:8093
start "DocuMind Local" cmd /k "cd /d ""%~dp0backend"" && go run ./cmd/server"
timeout /t 2 /nobreak >nul
start "" "http://localhost:8093/?v=20260502-upload-fix"

endlocal

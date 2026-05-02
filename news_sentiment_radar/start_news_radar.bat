@echo off
setlocal

cd /d "%~dp0"

echo Starting News Sentiment Radar at http://localhost:8092
start "News Sentiment Radar" cmd /k "cd /d ""%~dp0backend"" && go run ./cmd/server"
timeout /t 2 /nobreak >nul
start "" "http://localhost:8092"

endlocal

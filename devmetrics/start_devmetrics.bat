@echo off
echo Starting DevMetrics...

echo Starting Go backend...
start "DevMetrics Backend" cmd /k "cd /d %~dp0backend && go run ./cmd/api/main.go"

timeout /t 2 /nobreak >nul

echo Starting Next.js frontend...
start "DevMetrics Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo DevMetrics is starting!
echo Backend: http://localhost:8080
echo Frontend: http://localhost:3000

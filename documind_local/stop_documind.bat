@echo off
setlocal

echo Stopping DocuMind Local on port 8093...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8093" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F >nul 2>&1
)

echo Done.
pause

endlocal

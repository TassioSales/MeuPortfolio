@echo off
setlocal

echo Stopping News Sentiment Radar on port 8092...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8092" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F >nul 2>&1
)

echo Done.
pause

endlocal

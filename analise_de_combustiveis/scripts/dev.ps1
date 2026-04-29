$ErrorActionPreference = "Stop"

Write-Host "1/3 Running sample pipeline" -ForegroundColor Cyan
Push-Location "data-pipeline-python"
python -m fuel_analytics.cli run --sample
Pop-Location

Write-Host "2/3 Starting Go API" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend-go; go run ./cmd/api"

Write-Host "3/3 Starting Next frontend" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend-next; npm run dev"

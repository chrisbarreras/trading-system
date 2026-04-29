# Start Trading System Persistently
# This script starts both the server and scanner in minimized background windows

Write-Host "Starting Autonomous Trading System..." -ForegroundColor Green

# Navigate to trading system directory
Set-Location "$env:USERPROFILE\trading-system"

# Start trading system server in background
Write-Host "Starting trading system server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn app.main:app --host 0.0.0.0 --port 8080" -WindowStyle Minimized

# Wait for server to start
Write-Host "Waiting for server to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Start scanner in background
Write-Host "Starting automated scanner..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python run_scanner.py --schedule --strategy rsi" -WindowStyle Minimized

Write-Host "`nTrading system started successfully!" -ForegroundColor Green
Write-Host "Both processes are running in the background (minimized)" -ForegroundColor White
Write-Host "`nTo view:" -ForegroundColor White
Write-Host "  - Check taskbar for minimized PowerShell windows" -ForegroundColor Gray
Write-Host "  - Run 'python check_trades.py' to see trade history" -ForegroundColor Gray
Write-Host "  - Visit http://localhost:8080/docs for API docs`n" -ForegroundColor Gray

@echo off
REM Start both trading system and scanner with TOP 100 stocks
echo ========================================
echo Starting Autonomous Trading System
echo with TOP 100 Stock Scanning
echo ========================================
echo.

cd /d "%~dp0"

REM Check if stock list exists
if not exist "stock_symbols_top100.txt" (
    echo Error: stock_symbols_top100.txt not found!
    echo.
    echo Downloading stock lists now...
    python download_stock_list.py
    echo.
)

REM Start trading system in new window
echo Starting trading system server...
start "Trading System Server" cmd /k python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

REM Wait a few seconds for server to start
timeout /t 5 /nobreak

REM Start scanner with top 100 stock list in new window
echo Starting automated scanner with 100 stocks...
start "Trading Scanner - 100 Stocks" cmd /k python run_scanner.py --schedule --strategy rsi --symbols-file stock_symbols_top100.txt

echo.
echo ========================================
echo Both systems are now running!
echo ========================================
echo.
echo - Trading System Server: Check the first window
echo - Scanner (100 stocks): Check the second window
echo.
echo Note: Scanning 100 stocks takes ~2-3 minutes per scan
echo.
echo To stop: Close both windows or press Ctrl+C in each
echo.
pause

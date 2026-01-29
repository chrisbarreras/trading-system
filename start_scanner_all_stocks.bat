@echo off
REM Start scanner with TOP 500 liquid stocks
echo Starting Scanner with TOP 500 Stocks...
echo.
echo This will scan 500 of the most liquid stocks every 15 minutes.
echo Press Ctrl+C to stop.
echo.
cd /d "%~dp0"

REM Check if stock list exists
if not exist "stock_symbols_top500.txt" (
    echo Error: stock_symbols_top500.txt not found!
    echo.
    echo Please run this first to download stock lists:
    echo   python download_stock_list.py
    echo.
    pause
    exit /b 1
)

python run_scanner.py --schedule --strategy rsi --symbols-file stock_symbols_top500.txt

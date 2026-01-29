@echo off
REM Weekly Stock List Update Script
REM This script updates the stock list files
REM Can be run manually or via Windows Task Scheduler

echo ========================================
echo Stock List Update
echo ========================================
echo.

cd /d "%~dp0"

echo Updating stock lists...
python download_stock_list.py

echo.
echo ========================================
echo Update Complete
echo ========================================
echo.
echo Stock lists updated:
echo - stock_symbols_all.txt
echo - stock_symbols_top500.txt
echo - stock_symbols_top100.txt
echo.

REM Uncomment the line below if running via Task Scheduler
REM (prevents window from closing immediately)
REM pause

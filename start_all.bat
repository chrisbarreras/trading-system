@echo off
REM Start both the trading system and scanner
echo ========================================
echo Starting Autonomous Trading System
echo ========================================
echo.

cd /d "%~dp0"

REM Start trading system in new window
echo Starting trading system server...
start "Trading System Server" cmd /k python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

REM Wait a few seconds for server to start
timeout /t 5 /nobreak

REM Start scanner in new window
echo Starting automated scanner...
start "Trading Scanner" cmd /k python run_scanner.py --schedule --strategy rsi

echo.
echo ========================================
echo Both systems are now running!
echo ========================================
echo.
echo - Trading System Server: Check the first window
echo - Scanner: Check the second window
echo.
echo To stop: Close both windows or press Ctrl+C in each
echo.
pause

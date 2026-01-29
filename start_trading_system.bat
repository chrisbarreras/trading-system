@echo off
REM Start the trading system server
echo Starting Trading System Server...
cd /d "%~dp0"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

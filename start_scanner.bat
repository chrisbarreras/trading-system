@echo off
REM Start the automated scanner with scheduling (aggressive RSI strategy)
echo Starting Automated Scanner...
cd /d "%~dp0"
python run_scanner.py --schedule --strategy rsi

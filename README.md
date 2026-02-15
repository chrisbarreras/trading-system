# Autonomous Stock Trading System

A complete automated stock trading system with built-in market scanner, technical analysis strategies, and paper/live trading support via Alpaca API.

## 🎯 What This System Does

- **Scans stocks** automatically using technical analysis (RSI, MACD, Bollinger Bands, etc.)
- **Generates trade signals** based on configurable strategies
- **Executes trades** automatically via Alpaca API
- **Manages risk** with position limits and safety controls
- **Logs everything** to SQLite database for analysis
- **Runs autonomously** 24/7 with scheduling support

No TradingView premium required - uses free Yahoo Finance data!

---

## 📦 Quick Start

### 1. Install Dependencies

```powershell
# Install core dependencies
pip install -r requirements.txt

# Install scanner dependencies
pip install -r scanner_requirements.txt
```

### 2. Configure API Keys

Edit `.env` file:

```env
# Get paper trading keys from: https://app.alpaca.markets/paper/dashboard/overview
ALPACA_API_KEY=your_paper_api_key_here
ALPACA_SECRET_KEY=your_paper_secret_key_here
```

### 3. Download Stock Lists (Optional but Recommended)

```powershell
# Downloads ~400 curated liquid stocks
python download_stock_list.py
```

### 4. Start Trading

**Option A: Double-click to start everything**
```
start_all.bat
```

**Option B: Manual start**
```powershell
# Terminal 1: Trading system
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

# Terminal 2: Scanner
python run_scanner.py --schedule --strategy rsi
```

### 5. Monitor Your Trades

```powershell
# View recent trades
python check_trades.py

# Reset database for testing
python reset_database.py
```

---

## 🎮 System Configuration

### Current Settings (Aggressive Paper Trading Mode)

Your system is pre-configured for aggressive paper trading testing:

| Setting | Value | What It Means |
|---------|-------|---------------|
| **Strategy** | RSI | Trades on oversold/overbought signals |
| **Max Positions** | 10 | Can hold up to 10 stocks at once |
| **Position Size** | 15% | Each trade is 15% of portfolio |
| **Daily Trade Limit** | 50 | Max 50 trades per day |
| **Max Position Value** | $15,000 | No single position over $15k |
| **Scan Frequency** | Every 15 min | Scans market 4 times per hour |
| **Stock List Updates** | Weekly | Auto-updates stock lists every 7 days |
| **Order Cleanup** | Auto (1hr) | Cancels stuck orders older than 1 hour |

**To Change Settings:** Edit `.env` file

---

## 📊 Available Strategies

| Strategy | Description | Signal Frequency | Risk Level |
|----------|-------------|------------------|------------|
| **rsi** | RSI mean reversion (oversold/overbought) | Moderate-High | Medium |
| **macd** | MACD crossover signals | Low-Moderate | Medium |
| **ma_cross** | Moving average crossover (50/200 day) | Very Low | Low |
| **bb** | Bollinger Bands mean reversion | Moderate-High | High |
| **combo** | RSI + MACD confirmation (conservative) | Low | Low |

**Current:** RSI (aggressive testing)
**To Change:** Edit `start_scanner.bat` or `start_all.bat`

---

## 🔧 Common Customizations

### Change Strategy

Edit `start_scanner.bat`:
```batch
python run_scanner.py --schedule --strategy combo
```

Options: `rsi`, `macd`, `ma_cross`, `bb`, `combo`

### Change Risk Limits

Edit `.env`:
```env
MAX_POSITIONS=5           # Reduce positions
POSITION_SIZE_PCT=0.10    # Smaller position sizes (10%)
MAX_DAILY_TRADES=20       # Fewer trades per day
```

### Change Scan Frequency

Edit `run_scanner.py` line 106:
```python
schedule.every(30).minutes.do(job)  # Every 30 minutes
schedule.every().hour.do(job)       # Every hour
```

### Change Stock List

**Use default 10 stocks:**
```powershell
python run_scanner.py --schedule --strategy rsi
```

**Use custom symbols:**
```powershell
python run_scanner.py --schedule --symbols AAPL MSFT GOOGL TSLA NVDA
```

**Scan hundreds of stocks:**
```powershell
# First, download stock lists
python download_stock_list.py

# Then use the list
python run_scanner.py --schedule --symbols-file stock_symbols_top500.txt
```

### Adjust Market Hours

Edit `run_scanner.py` line 85 for your timezone:
```python
# Pacific Time (6:30 AM - 1:00 PM)
return 6 <= hour < 13

# Eastern Time (9:30 AM - 4:00 PM)
return 9 <= hour < 16

# Central Time (8:30 AM - 3:00 PM)
return 8 <= hour < 15
```

---

## 🚀 Running Options

### Run with Visible Windows (Recommended for Testing)

```powershell
start_all.bat
```

Two windows open:
- Window 1: Trading system server (receives signals)
- Window 2: Scanner (generates signals)

### Run in Background

```powershell
.\start_trading_persistent.ps1
```

Runs minimized in background. Check taskbar for windows.

### Run with Full Stock Scanning

```powershell
# Scans ~400 stocks instead of 10
start_all_with_full_scan.bat
```

Requires: `python download_stock_list.py` first

### Dry Run (No Actual Trades)

```powershell
# Test without executing trades
python run_scanner.py --dry-run --strategy rsi

# Test with specific symbols
python run_scanner.py --dry-run --symbols AAPL MSFT NVDA
```

---

## 📈 Monitoring & Analysis

### View Recent Trades

```powershell
python check_trades.py
```

Shows:
- Trade details (symbol, side, quantity, price)
- Status (filled, pending, rejected)
- Strategy used
- Timestamps

### Check Alpaca Dashboard

Visit: https://app.alpaca.markets/paper/dashboard/overview

See:
- Current positions
- Account value
- Trade history
- Buying power

### Clear Database

```powershell
python reset_database.py
```

Options:
1. Delete all trades
2. Delete only rejected trades
3. Delete only filled trades
4. Delete only pending trades

---

## 🔄 Automation Setup

### Windows Task Scheduler (Starts on Login)

1. Press `Win + R`, type `taskschd.msc`, press Enter
2. Click "Create Task"
3. **General Tab:**
   - Name: "Automated Trading System"
   - Check: "Run whether user is logged on or not"
4. **Triggers Tab:**
   - New → "At log on"
5. **Actions Tab:**
   - New → Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "c:\Users\chris\trading-system\start_trading_persistent.ps1"`
6. **Conditions Tab:**
   - Uncheck: "Start only if on AC power"
7. Click OK

System now starts automatically when you log in.

### Google Cloud (24/7 Remote Server)

Run the system on a Google Cloud VM for ~$7/month. See **[DEPLOY_GCP.md](DEPLOY_GCP.md)** for full instructions.

### Windows Service (Always Running)

For 24/7 operation, use NSSM (Non-Sucking Service Manager):

1. Download NSSM: https://nssm.cc/download
2. Extract to `C:\nssm`
3. Open PowerShell as Administrator:

```powershell
cd C:\nssm\win64

# Install trading system service
.\nssm.exe install TradingSystemServer "C:\Users\chris\AppData\Local\Programs\Python\Python313\python.exe"
.\nssm.exe set TradingSystemServer AppDirectory "c:\Users\chris\trading-system"
.\nssm.exe set TradingSystemServer AppParameters "-m uvicorn app.main:app --host 0.0.0.0 --port 8080"

# Install scanner service
.\nssm.exe install TradingScanner "C:\Users\chris\AppData\Local\Programs\Python\Python313\python.exe"
.\nssm.exe set TradingScanner AppDirectory "c:\Users\chris\trading-system"
.\nssm.exe set TradingScanner AppParameters "run_scanner.py --schedule --strategy rsi"
.\nssm.exe set TradingScanner DependOnService TradingSystemServer

# Start services
.\nssm.exe start TradingSystemServer
.\nssm.exe start TradingScanner
```

Services now run even when you're logged out.

---

## 🛠️ Advanced Features

### Scan 400+ Stocks

Download curated stock lists:

```powershell
python download_stock_list.py
```

Creates three files:
- `stock_symbols_all.txt` - All symbols (~400)
- `stock_symbols_top500.txt` - Same (already filtered)
- `stock_symbols_top100.txt` - Top 100 subset

Use them:
```powershell
# Fast - 100 stocks (~2 min per scan)
python run_scanner.py --schedule --symbols-file stock_symbols_top100.txt

# Comprehensive - 400 stocks (~8 min per scan)
python run_scanner.py --schedule --symbols-file stock_symbols_top500.txt
```

#### Automatic Stock List Updates

The system automatically checks and updates stock lists when using `--symbols-file`:

**Configure in `.env`:**
```env
# Update stock lists every 7 days (default)
STOCK_LIST_UPDATE_DAYS=7

# Enable/disable automatic updates
AUTO_UPDATE_STOCK_LIST=true
```

**How it works:**
- Scanner checks file age on startup
- If older than `STOCK_LIST_UPDATE_DAYS`, automatically downloads fresh list
- Runs in foreground during scanner startup
- If missing, downloads on first run

**Manual update options:**

```powershell
# Update now (manual)
python download_stock_list.py

# Or use the batch file
update_stock_list.bat
```

**Schedule with Windows Task Scheduler:**

1. Open Task Scheduler (`Win + R` → `taskschd.msc`)
2. Create Basic Task
3. Name: "Update Stock Lists"
4. Trigger: Weekly (Sunday at 2:00 AM recommended)
5. Action: Start a program
   - Program: `C:\Users\chris\trading-system\update_stock_list.bat`
6. Finish

This ensures fresh stock data even when scanner isn't running.

### Manual Trade Triggering

Test the webhook endpoint:

**PowerShell:**
```powershell
$body = @{
    ticker = "AAPL"
    action = "buy"
    strategy = "momentum"
    price = 150.00
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8080/webhook/tradingview -Method POST -ContentType "application/json" -Body $body
```

**Bash/curl:**
```bash
curl -X POST http://localhost:8080/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","action":"buy","strategy":"momentum","price":150.00}'
```

### Create Custom Strategies

1. Edit `scanner/strategies.py`
2. Add your strategy class:

```python
class MyCustomStrategy(TechnicalStrategy):
    name = "my_custom"

    def analyze(self, df, symbol):
        # Your analysis logic here
        # df has columns: open, high, low, close, volume

        # Calculate indicators
        df['rsi'] = ta.rsi(df['close'], length=14)

        # Determine action
        if df['rsi'].iloc[-1] < 25:
            action = "buy"
            signals = ["RSI extremely oversold"]
        elif df['rsi'].iloc[-1] > 75:
            action = "sell"
            signals = ["RSI extremely overbought"]
        else:
            action = None
            signals = []

        return {
            'symbol': symbol,
            'action': action,
            'signals': signals,
            'price': df['close'].iloc[-1],
            'rsi': df['rsi'].iloc[-1]
        }
```

3. Use it:
```powershell
python run_scanner.py --strategy my_custom --dry-run
```

### API Endpoints

Visit http://localhost:8080/docs when system is running

**Available endpoints:**
- `GET /` - System info
- `GET /health` - Health check
- `GET /status` - Account status
- `GET /trades` - Recent trades
- `POST /webhook/tradingview` - Webhook for trade signals

---

## ⚠️ Troubleshooting

### Orders showing "Filled Qty: 0.00" on Alpaca

**Cause:** Pending orders stuck in "accepted" status, tying up buying power
**Why it happens:** Orders placed when market is closed don't fill until market opens
**Solution:** System now automatically cancels orders older than 1 hour

**Automatic Prevention (Enabled by default):**
```env
# In .env file
AUTO_CLEANUP_ORDERS=true               # Enables auto-cleanup
AUTO_CANCEL_ORDER_AGE_HOURS=1          # Cancel after 1 hour
```

The scanner automatically cleans up stuck orders on startup. No manual intervention needed.

**Manual cleanup if needed:**
```powershell
python cancel_all_orders.py
```

### "No signals found"
**Cause:** Market conditions don't meet strategy criteria
**Solution:** Normal behavior. Try:
- Different strategy (e.g., `rsi` instead of `combo`)
- More symbols
- Wait for market volatility

### "Unauthorized" error
**Cause:** Invalid Alpaca API keys
**Solution:**
1. Get correct keys from https://app.alpaca.markets/paper/dashboard/overview
2. Update `.env` file
3. Restart trading system

### "Market is closed"
**Cause:** Trading outside 9:30 AM - 4:00 PM ET
**Solution:** Paper trading works 24/7, but market data may be stale

### Scanner not finding stocks
**Cause:** Stock list file missing
**Solution:**
```powershell
python download_stock_list.py
```

### Too many/few trades
**Too many trades:**
- Switch to `combo` strategy (more conservative)
- Reduce `MAX_DAILY_TRADES` in `.env`
- Increase scan interval (30 min instead of 15)

**Too few trades:**
- Switch to `rsi` strategy (more signals)
- Scan more symbols (use stock list files)
- Decrease scan interval (every 5-10 minutes)

### Yahoo Finance rate limiting
**Cause:** Scanning too many stocks too frequently
**Solution:**
- Limit to 500 stocks per scan
- Keep scan frequency at 15+ minutes
- If blocked, wait 1 hour

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `.env` | Configuration (API keys, limits) |
| `start_all.bat` | Start everything (easy) |
| `start_trading_persistent.ps1` | Run in background |
| `check_trades.py` | View trade history |
| `reset_database.py` | Clear trades |
| `download_stock_list.py` | Get stock symbols |
| `run_scanner.py` | Scanner CLI |
| `app/main.py` | Trading system server |
| `scanner/strategies.py` | Trading strategies |

---

## 🎓 Understanding How It Works

### Trade Execution Flow

1. **Scanner runs** every 15 minutes (configurable)
2. **Fetches data** from Yahoo Finance for each symbol
3. **Analyzes with strategy** (RSI, MACD, etc.)
4. **Generates signals** (buy/sell/hold)
5. **Posts to webhook** if signal found
6. **Trading system validates** signal and checks risk limits
7. **Executes order** via Alpaca API
8. **Records to database** for tracking
9. **Repeats** on schedule

### Decision Logic

**When does it trade?**
- ALL symbols are checked each scan
- ANY symbol meeting criteria generates a signal
- Multiple symbols can trigger simultaneously
- Risk limits prevent overtrading:
  - Max 10 positions at once
  - Max $15k per position
  - Max 50 trades per day
  - 15% of portfolio per trade

**What if multiple signals appear?**
- System tries to execute ALL qualifying trades
- Subject to risk limits above
- If at max positions, skips new buys
- Can always sell existing positions

---

## 🔐 Security & Best Practices

### Testing Protocol

1. ✅ **Start with paper trading** (you're here)
2. ✅ **Run for 2-4 weeks** minimum
3. ✅ **Review all trades** daily
4. ✅ **Test different market conditions**
5. ✅ **Verify strategy performance**
6. ⚠️ **Only then consider live trading**

### Safety Reminders

- ✅ Paper trading = fake money (safe to test)
- ⚠️ Never commit `.env` files (contains API keys)
- ⚠️ Start with small position sizes in live trading
- ⚠️ Always have stop-loss strategy
- ⚠️ Monitor daily for unexpected behavior

### Going Live (When Ready)

1. Copy `.env.paper` to `.env.live`
2. Add LIVE Alpaca API keys (from live trading section)
3. Reduce risk limits:
   ```env
   MAX_POSITIONS=3
   POSITION_SIZE_PCT=0.05  # 5% instead of 15%
   MAX_POSITION_SIZE_USD=5000
   ```
4. Start conservatively:
   ```powershell
   # Use combo strategy (most conservative)
   python run_scanner.py --schedule --strategy combo --symbols AAPL MSFT GOOGL
   ```
5. Fund Alpaca account (start small, e.g., $1000)
6. Monitor closely for first week

---

## 📞 Support & Resources

**System is working when:**
- ✅ Server starts without errors
- ✅ Scanner shows symbols being checked
- ✅ `python check_trades.py` shows trades
- ✅ Alpaca dashboard shows positions

**If something breaks:**
1. Check server logs (Terminal 1)
2. Check scanner logs (Terminal 2)
3. Verify API keys in `.env`
4. Test with dry run: `python run_scanner.py --dry-run`
5. Try manual webhook test (see Advanced Features)

**External Documentation:**
- Alpaca API: https://alpaca.markets/docs/
- Yahoo Finance (yfinance): https://github.com/ranaroussi/yfinance
- pandas-ta indicators: https://github.com/twopirllc/pandas-ta

---

## ⚖️ Disclaimer

**IMPORTANT:** This software is for educational purposes only.

- Trading stocks involves significant risk
- You may lose money (potentially all of it)
- Past performance does not guarantee future results
- Always test thoroughly in paper mode first
- Never invest more than you can afford to lose
- The authors are not responsible for any financial losses
- Not financial advice - do your own research

**You are responsible for:**
- Your own trading decisions
- Understanding the strategies used
- Monitoring the system
- Setting appropriate risk limits
- Complying with financial regulations

---

## 🎉 You're Ready!

Your trading system is configured and ready to use. To start:

```powershell
# Easy way
start_all.bat

# Then monitor
python check_trades.py
```

Happy trading! 🚀 (but responsibly)

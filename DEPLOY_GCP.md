# Deploying to Google Cloud (Compute Engine)

Run your trading system 24/7 on a Google Cloud VM for ~$7/month.

---

## Prerequisites

- A Google Cloud account with billing enabled
- The `gcloud` CLI installed locally ([install guide](https://cloud.google.com/sdk/docs/install))
- Your project code pushed to a Git repository

---

## 1. Create the VM

```bash
gcloud compute instances create trading-system \
  --zone=us-east1-b \
  --machine-type=e2-micro \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --tags=trading
```

**Why these choices:**
- `us-east1-b` — Low latency to US stock exchanges and Alpaca's servers
- `e2-micro` — ~$7/month, plenty for this workload (qualifies for GCP free tier)
- `ubuntu-2204-lts` — Stable, well-supported Linux distribution
- `20GB` disk — Room for database growth and logs

> **Note:** If you run more than ~5 accounts simultaneously, consider upgrading to `e2-small` (2GB RAM, ~$14/month).

## 2. SSH into the VM

```bash
gcloud compute ssh trading-system --zone=us-east1-b
```

## 3. Install Dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git

git clone <your-repo-url> ~/trading-system
cd ~/trading-system

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r scanner_requirements.txt
```

## 4. Configure Environment

```bash
nano ~/trading-system/.env
```

Paste your configuration. At minimum:

```env
TRADING_MODE=paper
ALPACA_API_KEY=your_paper_api_key_here
ALPACA_SECRET_KEY=your_paper_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
DATABASE_URL=sqlite:///./trading_paper.db
```

For additional accounts, add key pairs using any names you choose:

```env
ALPACA_DAY1_KEY=your_second_paper_api_key
ALPACA_DAY1_SECRET=your_second_paper_secret_key
ALPACA_SWING2_KEY=your_third_paper_api_key
ALPACA_SWING2_SECRET=your_third_paper_secret_key
```

## 5. Configure Accounts

```bash
nano ~/trading-system/accounts.yaml
```

Each account entry maps one Alpaca paper account to one strategy. The `accounts.yaml`
file ships with a single swing RSI account pre-configured. Add or uncomment entries
to enable more accounts:

```yaml
symbols_file: stock_symbols_top500.txt

accounts:
  - id: swing_rsi_1
    name: "Swing RSI"
    type: swing          # daily bars, scans once at 09:35 ET
    alpaca_api_key: ${ALPACA_API_KEY}
    alpaca_secret_key: ${ALPACA_SECRET_KEY}
    strategy: rsi
    strategy_params:
      period: 14
      oversold: 30
      overbought: 70
    risk:
      position_size_pct: 0.10
      max_positions: 5
      max_position_size_usd: 10000.0

  - id: day_rsi_1
    name: "Day Trading RSI"
    type: day            # 15m bars, scans every 15 min; closes all at 15:55 ET
    alpaca_api_key: ${ALPACA_DAY1_KEY}
    alpaca_secret_key: ${ALPACA_DAY1_SECRET}
    strategy: rsi
    strategy_params:
      period: 9
      oversold: 20
      overbought: 80
    risk:
      position_size_pct: 0.08
      max_positions: 3
      max_position_size_usd: 5000.0
```

**Account types:**
- `swing` — scans daily bars once per trading day at 09:35 ET
- `day` — scans 15-minute bars every 15 minutes during market hours; all positions closed at 15:55 ET

**Supported strategies:** `rsi`, `macd`, `ma_cross`, `bb`, `combo`

## 6. Download Stock Lists

```bash
source ~/trading-system/venv/bin/activate
cd ~/trading-system
python download_stock_list.py
```

## 7. Test Manually

Before setting up the service, verify everything works:

```bash
cd ~/trading-system
source venv/bin/activate

# Validate config loads cleanly
python -c "from trading.config_loader import load_accounts_config; c = load_accounts_config(); print(f'Loaded {len(c.accounts)} account(s)')"

# Start the system (Ctrl+C to stop)
python run_trading.py
```

In a second SSH session, verify the API responds:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/status
```

If both run without errors, you're ready to set up the persistent service.

---

## 8. Set Up systemd Service

systemd keeps the process running 24/7, restarts it on failure, and starts it automatically after VM reboots. The trading system now runs as a **single service** that manages both the API server and all configured accounts.

### Create the service

```bash
sudo tee /etc/systemd/system/trading-system.service > /dev/null << 'EOF'
[Unit]
Description=Trading System (Multi-Account Orchestrator + API Server)
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/trading-system
Environment=PATH=/home/YOUR_USERNAME/trading-system/venv/bin:/usr/bin
ExecStart=/home/YOUR_USERNAME/trading-system/venv/bin/python run_trading.py
Restart=always
RestartSec=30
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF
```

**Replace `YOUR_USERNAME`** with your actual VM username (run `whoami` to check).

### Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-system
sudo systemctl start trading-system
```

### Verify it's running

```bash
sudo systemctl status trading-system
```

Should show `active (running)`.

### Migrating from the old two-service setup

If you previously ran `trading-server` and `trading-scanner`, disable them first:

```bash
sudo systemctl stop trading-scanner trading-server
sudo systemctl disable trading-scanner trading-server
sudo systemctl daemon-reload
sudo systemctl enable trading-system
sudo systemctl start trading-system
```

---

## 9. Viewing Logs

```bash
# Live logs
sudo journalctl -u trading-system -f

# Last 100 lines
sudo journalctl -u trading-system -n 100

# Logs from today only
sudo journalctl -u trading-system --since today
```

---

## 10. Common Operations

### Restart (e.g., after config changes)

```bash
sudo systemctl restart trading-system
```

### Stop everything

```bash
sudo systemctl stop trading-system
```

### Deploy code updates

```bash
cd ~/trading-system
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart trading-system
```

### Add or modify accounts

Edit `accounts.yaml` and restart:

```bash
nano ~/trading-system/accounts.yaml
sudo systemctl restart trading-system
```

### Check system status (all accounts)

```bash
curl http://localhost:8080/status
```

### Run a backtest

```bash
cd ~/trading-system
source venv/bin/activate

# Backtest a configured account against historical data
python run_backtest.py --account swing_rsi_1 --start 2024-01-01 --end 2024-12-31

# With custom capital and CSV output
python run_backtest.py --account swing_rsi_1 --start 2023-01-01 --end 2024-01-01 \
  --capital 50000 --output results.csv
```

### Cancel all orders (emergency)

```bash
cd ~/trading-system
source venv/bin/activate
python cancel_all_orders.py
```

### Check trades

```bash
cd ~/trading-system
source venv/bin/activate
python check_trades.py
```

---

## 11. Firewall Rules

By default the VM is not accessible from the internet. If you need external access to the API (e.g., for monitoring):

```bash
gcloud compute firewall-rules create allow-trading-api \
  --allow=tcp:8080 \
  --target-tags=trading \
  --source-ranges=YOUR_IP/32 \
  --description="Allow trading API access from my IP"
```

Replace `YOUR_IP` with your home IP address. **Never use `0.0.0.0/0`** — that exposes the API to the entire internet.

---

## 12. Static IP (Optional)

If you need a fixed IP for external access:

```bash
gcloud compute addresses create trading-ip --region=us-east1

gcloud compute instances delete-access-config trading-system \
  --zone=us-east1-b --access-config-name="External NAT"

gcloud compute instances add-access-config trading-system \
  --zone=us-east1-b \
  --address=$(gcloud compute addresses describe trading-ip --region=us-east1 --format='value(address)')
```

---

## 13. Monitoring and Alerts

### Set up an uptime check (free)

1. Go to **Cloud Monitoring** in the GCP Console
2. Navigate to **Uptime checks** > **Create Uptime Check**
3. Protocol: HTTP, Port: 8080, Path: `/health`
4. Check frequency: 5 minutes
5. Add a notification channel (email) for alerts

### VM monitoring

GCP automatically tracks CPU, memory, and disk usage. View in **Compute Engine** > **VM instances** > click your instance > **Monitoring** tab.

---

## 14. Database Backups

Schedule automatic disk snapshots to protect your trade history:

```bash
gcloud compute resource-policies create snapshot-schedule trading-backup \
  --region=us-east1 \
  --max-retention-days=14 \
  --daily-schedule \
  --start-time=04:00

gcloud compute disks add-resource-policies trading-system \
  --resource-policies=trading-backup \
  --zone=us-east1-b
```

This takes a daily snapshot at 4:00 AM UTC and keeps 14 days of history.

---

## Cost Summary

| Resource | Monthly Cost |
|----------|-------------|
| e2-micro VM | ~$7 (free tier eligible) |
| 20GB disk | ~$1 |
| Snapshots (14 days) | ~$0.50 |
| Static IP (if used) | ~$3 (free while attached to running VM) |
| **Total** | **~$8-11/month** |

---

## Troubleshooting

### Service won't start

```bash
sudo journalctl -u trading-system -n 50 --no-pager
```

Common causes:
- Wrong username in the service file — run `whoami` and update
- Missing venv — re-run the install steps
- Environment variable referenced in `accounts.yaml` not set in `.env` — check the error message for the variable name
- Bad `.env` file — check for typos in API keys

### Config validation errors

```bash
cd ~/trading-system
source venv/bin/activate
python -c "from trading.config_loader import load_accounts_config; load_accounts_config()"
```

This will print a clear error if any `${ENV_VAR}` references in `accounts.yaml` are unresolved.

### VM runs out of memory

The e2-micro has 1GB RAM. Running many accounts scanning 500 symbols each can be demanding. Consider upgrading:

```bash
# Stop VM first
gcloud compute instances stop trading-system --zone=us-east1-b

# Resize
gcloud compute instances set-machine-type trading-system \
  --zone=us-east1-b --machine-type=e2-small

# Restart
gcloud compute instances start trading-system --zone=us-east1-b
```

`e2-small` (2GB RAM) costs ~$14/month.

### Can't SSH into VM

```bash
gcloud compute instances add-metadata trading-system \
  --zone=us-east1-b \
  --metadata=enable-oslogin=TRUE
```

### Database locked errors

SQLite can have issues with concurrent writes. If you see these frequently, the system handles retries automatically. For persistent issues, consider reducing the number of accounts or scan frequency.

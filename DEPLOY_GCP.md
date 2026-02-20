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

Paste your configuration (API keys, trading mode, limits, etc.). At minimum:

```env
TRADING_MODE=paper
ALPACA_API_KEY=your_paper_api_key_here
ALPACA_SECRET_KEY=your_paper_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
DATABASE_URL=sqlite:///./trading_paper.db
MAX_POSITIONS=10
POSITION_SIZE_PCT=0.15
MAX_DAILY_TRADES=50
MAX_POSITION_SIZE_USD=15000
AUTO_CLEANUP_ORDERS=true
AUTO_CANCEL_ORDER_AGE_HOURS=1
```

## 5. Download Stock Lists (Optional)

```bash
source ~/trading-system/venv/bin/activate
cd ~/trading-system
python download_stock_list.py
```

## 6. Test Manually

Before setting up services, verify everything works:

```bash
cd ~/trading-system
source venv/bin/activate

# Terminal 1: Start the trading server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

# (In a second SSH session)
# Terminal 2: Run a dry-run scan
python run_scanner.py --dry-run --strategy rsi
```

If both run without errors, you're ready to set up persistent services.

---

## 7. Set Up systemd Services

systemd keeps your processes running 24/7, restarts them on failure, and starts them automatically after VM reboots.

### Create the trading server service

```bash
sudo tee /etc/systemd/system/trading-server.service > /dev/null << 'EOF'
[Unit]
Description=Trading System FastAPI Server
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/trading-system
Environment=PATH=/home/YOUR_USERNAME/trading-system/venv/bin:/usr/bin
ExecStart=/home/YOUR_USERNAME/trading-system/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Create the scanner service

```bash
sudo tee /etc/systemd/system/trading-scanner.service > /dev/null << 'EOF'
[Unit]
Description=Trading System Market Scanner
After=trading-server.service
Requires=trading-server.service

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/trading-system
Environment=PATH=/home/YOUR_USERNAME/trading-system/venv/bin:/usr/bin
ExecStart=/home/YOUR_USERNAME/trading-system/venv/bin/python run_scanner.py --schedule --strategy rsi --symbols-file stock_symbols_top500.txt
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
```

**Replace `YOUR_USERNAME`** with your actual VM username (run `whoami` to check).

### Enable and start both services

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-server trading-scanner
sudo systemctl start trading-server trading-scanner
```

### Verify they're running

```bash
sudo systemctl status trading-server
sudo systemctl status trading-scanner
```

Both should show `active (running)`.

---

## 8. Viewing Logs

```bash
# Trading server logs (live)
sudo journalctl -u trading-server -f

# Scanner logs (live)
sudo journalctl -u trading-scanner -f

# Last 100 lines of scanner logs
sudo journalctl -u trading-scanner -n 100

# Logs from today only
sudo journalctl -u trading-server --since today
```

---

## 9. Common Operations

### Restart services (e.g., after config changes)

```bash
sudo systemctl restart trading-server trading-scanner
```

### Stop everything

```bash
sudo systemctl stop trading-scanner trading-server
```

### Deploy code updates

```bash
cd ~/trading-system
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart trading-server trading-scanner
```

### Check trades

```bash
cd ~/trading-system
source venv/bin/activate
python check_trades.py
```

### Cancel all orders (emergency)

```bash
cd ~/trading-system
source venv/bin/activate
python cancel_all_orders.py
```

---

## 10. Firewall Rules

By default the VM is not accessible from the internet. If you need external access to the API (e.g., for monitoring):

```bash
gcloud compute firewall-rules create allow-trading-api \
  --allow=tcp:8080 \
  --target-tags=trading \
  --source-ranges=YOUR_IP/32 \
  --description="Allow trading API access from my IP"
```

Replace `YOUR_IP` with your home IP address. **Never use `0.0.0.0/0`** — that exposes the API to the entire internet.

If you don't need external access, skip this step. The scanner and server communicate over localhost.

---

## 11. Static IP (Optional)

If you need a fixed IP for external webhook integrations:

```bash
gcloud compute addresses create trading-ip --region=us-east1

gcloud compute instances delete-access-config trading-system \
  --zone=us-east1-b --access-config-name="External NAT"

gcloud compute instances add-access-config trading-system \
  --zone=us-east1-b \
  --address=$(gcloud compute addresses describe trading-ip --region=us-east1 --format='value(address)')
```

---

## 12. Monitoring and Alerts

### Set up an uptime check (free)

1. Go to **Cloud Monitoring** in the GCP Console
2. Navigate to **Uptime checks** > **Create Uptime Check**
3. Protocol: HTTP, Port: 8080, Path: `/health`
4. Check frequency: 5 minutes
5. Add a notification channel (email) for alerts

### VM monitoring

GCP automatically tracks CPU, memory, and disk usage. View in **Compute Engine** > **VM instances** > click your instance > **Monitoring** tab.

---

## 13. Database Backups

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

### Services won't start

```bash
# Check for errors in logs
sudo journalctl -u trading-server -n 50 --no-pager
sudo journalctl -u trading-scanner -n 50 --no-pager
```

Common causes:
- Wrong username in service files — run `whoami` and update
- Missing venv — re-run the install steps
- Bad `.env` file — check for typos in API keys

### VM runs out of memory

The e2-micro has 1GB RAM. If you scan 400+ stocks, consider upgrading:

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
# Reset SSH keys
gcloud compute instances add-metadata trading-system \
  --zone=us-east1-b \
  --metadata=enable-oslogin=TRUE
```

### Database locked errors

SQLite can have issues with concurrent writes. If you see these frequently, the system handles retries automatically. For persistent issues, consider reducing scan frequency.

"""Cleanup all stuck orders immediately (non-interactive)."""
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load .env
load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL")

headers = {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": SECRET_KEY
}

print("=" * 80)
print("Cleaning Up All Pending Orders")
print("=" * 80)
print()

# Get all orders
response = requests.get(f"{BASE_URL}/v2/orders", headers=headers)

if response.status_code != 200:
    print(f"Error fetching orders: {response.status_code} - {response.text}")
    exit(1)

orders = response.json()

if not orders:
    print("No open orders to cancel")
    exit(0)

print(f"Found {len(orders)} open order(s)\n")

# Cancel each order
cancelled = 0
failed = 0

for order in orders:
    order_id = order['id']
    symbol = order['symbol']
    side = order['side'].upper()
    qty = order['qty']

    print(f"Cancelling: {side} {qty} {symbol}")

    # Cancel order
    cancel_response = requests.delete(
        f"{BASE_URL}/v2/orders/{order_id}",
        headers=headers
    )

    if cancel_response.status_code in [200, 204]:
        print(f"  ✅ Cancelled")
        cancelled += 1
    else:
        print(f"  ❌ Failed: {cancel_response.status_code}")
        failed += 1

print()
print("=" * 80)
print(f"Summary:")
print(f"  Cancelled: {cancelled}")
print(f"  Failed: {failed}")
print("=" * 80)
print()

# Show updated account status
print("Updated Account Status:")
print("-" * 80)
account_response = requests.get(f"{BASE_URL}/v2/account", headers=headers)
if account_response.status_code == 200:
    account = account_response.json()
    print(f"Portfolio Value: ${float(account['portfolio_value']):,.2f}")
    print(f"Buying Power: ${float(account['buying_power']):,.2f}")
    print(f"Cash: ${float(account['cash']):,.2f}")
    print()
    print("✅ Ready to trade!")
else:
    print(f"Error fetching account: {account_response.status_code}")

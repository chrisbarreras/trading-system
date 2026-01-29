"""
Quick script to view trades from the database.
"""
import sqlite3
from pathlib import Path

db_path = Path("trading_paper.db")

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    print("Run the trading system first to create it.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get recent trades
cursor.execute("""
    SELECT
        id,
        symbol,
        side,
        quantity,
        price,
        status,
        strategy_name,
        order_id,
        created_at,
        filled_at,
        error_message
    FROM trades
    ORDER BY created_at DESC
    LIMIT 10
""")

trades = cursor.fetchall()

if not trades:
    print("📊 No trades found in database yet.")
    print("This is normal if you haven't executed any trades.")
else:
    print("\n" + "="*80)
    print("📊 Recent Trades")
    print("="*80 + "\n")

    for trade in trades:
        trade_id, symbol, side, quantity, price, status, strategy_name, order_id, created_at, filled_at, error_message = trade
        print(f"ID: {trade_id}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side.upper()}")
        print(f"Quantity: {quantity}")
        print(f"Price: ${price:.2f}" if price else "Price: PENDING")
        print(f"Status: {status}")
        print(f"Strategy: {strategy_name}")
        print(f"Order ID: {order_id}")
        print(f"Created: {created_at}")
        if filled_at:
            print(f"Filled: {filled_at}")
        if error_message:
            print(f"Error: {error_message}")
        print("-" * 80)

# Get trade count
cursor.execute("SELECT COUNT(*) FROM trades")
count = cursor.fetchone()[0]
print(f"\nTotal trades in database: {count}\n")

conn.close()

"""
Clear rejected trades from the database.
"""
import sqlite3
from pathlib import Path

db_path = Path("trading_paper.db")

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count rejected trades
cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'REJECTED'")
rejected_count = cursor.fetchone()[0]

print(f"\nFound {rejected_count} rejected trades")

if rejected_count > 0:
    response = input("Delete all rejected trades? (yes/no): ")
    if response.lower() == 'yes':
        cursor.execute("DELETE FROM trades WHERE status = 'REJECTED'")
        conn.commit()
        print(f"✅ Deleted {rejected_count} rejected trades\n")
    else:
        print("❌ Cancelled\n")
else:
    print("No rejected trades to delete\n")

conn.close()

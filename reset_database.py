"""
Reset or clear trades from the database.
Useful for testing and starting fresh.
"""
import sqlite3
from pathlib import Path
import sys

db_path = Path("trading_paper.db")

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    print("The database will be created when you run the trading system.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get trade counts
cursor.execute("SELECT COUNT(*) FROM trades")
total_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'REJECTED'")
rejected_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'FILLED'")
filled_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'PENDING'")
pending_count = cursor.fetchone()[0]

print("\n" + "="*80)
print("📊 Database Status")
print("="*80)
print(f"Total trades: {total_count}")
print(f"  - Filled: {filled_count}")
print(f"  - Rejected: {rejected_count}")
print(f"  - Pending: {pending_count}")
print("="*80 + "\n")

if total_count == 0:
    print("Database is already empty.\n")
    conn.close()
    exit(0)

print("What would you like to do?\n")
print("1. Delete ALL trades (complete reset)")
print("2. Delete only REJECTED trades")
print("3. Delete only FILLED trades")
print("4. Delete only PENDING trades")
print("5. Cancel (do nothing)")

choice = input("\nEnter your choice (1-5): ").strip()

if choice == "1":
    confirm = input(f"\n⚠️  Delete ALL {total_count} trades? Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        cursor.execute("DELETE FROM trades")
        conn.commit()
        print(f"✅ Deleted all {total_count} trades\n")
    else:
        print("❌ Cancelled\n")

elif choice == "2":
    if rejected_count > 0:
        confirm = input(f"\nDelete {rejected_count} rejected trades? Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            cursor.execute("DELETE FROM trades WHERE status = 'REJECTED'")
            conn.commit()
            print(f"✅ Deleted {rejected_count} rejected trades\n")
        else:
            print("❌ Cancelled\n")
    else:
        print("No rejected trades to delete.\n")

elif choice == "3":
    if filled_count > 0:
        confirm = input(f"\nDelete {filled_count} filled trades? Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            cursor.execute("DELETE FROM trades WHERE status = 'FILLED'")
            conn.commit()
            print(f"✅ Deleted {filled_count} filled trades\n")
        else:
            print("❌ Cancelled\n")
    else:
        print("No filled trades to delete.\n")

elif choice == "4":
    if pending_count > 0:
        confirm = input(f"\nDelete {pending_count} pending trades? Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            cursor.execute("DELETE FROM trades WHERE status = 'PENDING'")
            conn.commit()
            print(f"✅ Deleted {pending_count} pending trades\n")
        else:
            print("❌ Cancelled\n")
    else:
        print("No pending trades to delete.\n")

elif choice == "5":
    print("❌ Cancelled\n")

else:
    print("Invalid choice. Cancelled.\n")

conn.close()

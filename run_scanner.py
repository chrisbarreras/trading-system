"""
Run the market scanner manually or on a schedule.

Usage:
    # Scan once (dry run - no trades)
    python run_scanner.py --dry-run

    # Scan once and execute trades
    python run_scanner.py

    # Run on schedule (every hour during market hours)
    python run_scanner.py --schedule

    # Use different strategy
    python run_scanner.py --strategy combo

    # Custom symbols
    python run_scanner.py --symbols AAPL MSFT GOOGL
"""
import argparse
import time
import schedule
import os
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
from scanner.scanner import create_scanner


# Configuration
DEFAULT_SYMBOLS = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Google
    "TSLA",   # Tesla
    "NVDA",   # NVIDIA
    "AMD",    # AMD
    "SPY",    # S&P 500 ETF
    "QQQ",    # NASDAQ ETF
    "DIA",    # Dow Jones ETF
    "IWM",    # Russell 2000 ETF
]


def check_and_update_stock_list():
    """
    Check if stock list needs updating and update if necessary.
    Returns True if update was performed, False otherwise.
    """
    try:
        # Load settings from .env
        from dotenv import load_dotenv
        load_dotenv()

        # Check if auto-update is enabled
        auto_update = os.getenv("AUTO_UPDATE_STOCK_LIST", "true").lower() == "true"
        if not auto_update:
            return False

        # Get update interval (default 7 days)
        update_days = int(os.getenv("STOCK_LIST_UPDATE_DAYS", "7"))

        # Check if stock list file exists
        stock_list_file = Path("stock_symbols_top500.txt")
        if not stock_list_file.exists():
            print(f"\n📥 Stock list file not found. Downloading for the first time...")
            return update_stock_list()

        # Check file age
        file_modified_time = datetime.fromtimestamp(stock_list_file.stat().st_mtime)
        file_age = datetime.now() - file_modified_time

        if file_age > timedelta(days=update_days):
            print(f"\n🔄 Stock list is {file_age.days} days old (update threshold: {update_days} days)")
            print(f"Updating stock list...")
            return update_stock_list()

        return False

    except Exception as e:
        print(f"\n⚠️  Error checking stock list age: {e}")
        print("Continuing with existing list...")
        return False


def update_stock_list():
    """
    Run the download_stock_list.py script to update stock lists.
    Returns True if successful, False otherwise.
    """
    try:
        print(f"Running: python download_stock_list.py")

        # Run the download script
        result = subprocess.run(
            ["python", "download_stock_list.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            print(f"✅ Stock list updated successfully!")
            print(f"{result.stdout}")
            return True
        else:
            print(f"⚠️  Stock list update failed:")
            print(f"{result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⚠️  Stock list update timed out (took longer than 5 minutes)")
        return False
    except Exception as e:
        print(f"⚠️  Error updating stock list: {e}")
        return False


def cleanup_stale_orders():
    """
    Cancel any pending orders that are older than configured threshold.
    This prevents orders from tying up buying power indefinitely.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Check if auto-cleanup is enabled
        auto_cleanup = os.getenv("AUTO_CLEANUP_ORDERS", "true").lower() == "true"
        if not auto_cleanup:
            return

        # Get configuration
        max_age_hours = int(os.getenv("AUTO_CANCEL_ORDER_AGE_HOURS", "1"))
        API_KEY = os.getenv("ALPACA_API_KEY")
        SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
        BASE_URL = os.getenv("ALPACA_BASE_URL")

        if not all([API_KEY, SECRET_KEY, BASE_URL]):
            print("⚠️  Alpaca credentials not configured - skipping order cleanup")
            return

        headers = {
            "APCA-API-KEY-ID": API_KEY,
            "APCA-API-SECRET-KEY": SECRET_KEY
        }

        # Get all open orders
        response = requests.get(f"{BASE_URL}/v2/orders", headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"⚠️  Could not fetch orders for cleanup: {response.status_code}")
            return

        orders = response.json()

        if not orders:
            return  # No orders to clean up

        # Check each order's age
        now = datetime.utcnow()
        cancelled_count = 0

        for order in orders:
            try:
                # Parse order creation time
                created_at = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                age = now - created_at.replace(tzinfo=None)

                # Cancel if older than configured threshold
                if age > timedelta(hours=max_age_hours):
                    order_id = order['id']
                    symbol = order['symbol']
                    side = order['side'].upper()

                    cancel_response = requests.delete(
                        f"{BASE_URL}/v2/orders/{order_id}",
                        headers=headers,
                        timeout=10
                    )

                    if cancel_response.status_code in [200, 204]:
                        print(f"🗑️  Cancelled stale order: {side} {symbol} (age: {age.total_seconds()/3600:.1f}h)")
                        cancelled_count += 1

            except Exception as e:
                continue  # Skip problematic orders

        if cancelled_count > 0:
            print(f"✅ Cleaned up {cancelled_count} stale order(s)")
            print()

    except Exception as e:
        print(f"⚠️  Error during order cleanup: {e}")
        # Don't fail the whole process if cleanup fails


def run_scan(symbols, strategy, dry_run=False):
    """Run a single market scan."""
    try:
        # Create scanner with Yahoo Finance data
        scanner = create_scanner(
            symbols=symbols,
            strategy_name=strategy,
            data_source="yahoo"
        )

        # Scan and execute
        executed = scanner.scan_and_execute(dry_run=dry_run)

        if executed:
            print(f"\n✅ Executed {len(executed)} trade(s)")
        else:
            print(f"\n📊 Scan complete - no trades executed")

        print(f"\n{'='*80}\n")

    except Exception as e:
        print(f"\n❌ Scanner error: {e}\n")


def is_market_hours():
    """
    Check if current time is during market hours (9:30 AM - 4:00 PM ET).
    For simplicity, this checks your local time. Adjust as needed.
    """
    now = datetime.now()

    # Skip weekends
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Check time (simplified - doesn't account for timezone)
    hour = now.hour

    # Approximate market hours (adjust for your timezone)
    # US market: 9:30 AM - 4:00 PM ET
    # If you're in EST/EDT: 9-16
    # If you're in PST/PDT: 6-13
    # Adjust these values for your timezone
    return 9 <= hour < 16


def scheduled_scan(symbols, strategy, dry_run=False):
    """Run scheduled scans during market hours."""
    print(f"\n{'='*80}")
    print("📅 Scheduled Scanner Started")
    print(f"Strategy: {strategy}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Dry Run: {dry_run}")
    print(f"Schedule: Every hour during market hours")
    print(f"{'='*80}\n")

    def job():
        if is_market_hours():
            print(f"\n⏰ Scheduled scan triggered at {datetime.now().strftime('%H:%M:%S')}")
            run_scan(symbols, strategy, dry_run)
        else:
            print(f"⏸️  Market closed - skipping scan at {datetime.now().strftime('%H:%M:%S')}")

    # Schedule scans every 15 minutes (aggressive mode)
    schedule.every(15).minutes.do(job)

    # Run immediately on start
    job()

    # Keep running
    print("Press Ctrl+C to stop...\n")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\n📊 Scanner stopped by user.\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Market scanner for automated trading signals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan once (dry run)
  python run_scanner.py --dry-run

  # Scan once and execute
  python run_scanner.py

  # Run on schedule
  python run_scanner.py --schedule

  # Use combo strategy
  python run_scanner.py --strategy combo --dry-run

  # Custom symbols
  python run_scanner.py --symbols AAPL MSFT NVDA --strategy rsi

Strategies:
  rsi      - RSI mean reversion (oversold/overbought)
  macd     - MACD crossover signals
  ma_cross - Moving average crossover (Golden/Death cross)
  bb       - Bollinger Bands mean reversion
  combo    - Combination strategy (RSI + MACD confirmation)
        """
    )

    parser.add_argument(
        '--symbols',
        nargs='+',
        default=None,
        help='Symbols to scan (space-separated, e.g., AAPL MSFT GOOGL)'
    )

    parser.add_argument(
        '--symbols-file',
        type=str,
        help='File containing symbols (one per line, e.g., stock_symbols_top500.txt)'
    )

    parser.add_argument(
        '--strategy',
        choices=['rsi', 'macd', 'ma_cross', 'bb', 'combo'],
        default='rsi',
        help='Trading strategy to use (default: rsi)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show signals but do not execute trades'
    )

    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Run on schedule (every hour during market hours)'
    )

    args = parser.parse_args()

    # Determine symbols to use
    symbols = DEFAULT_SYMBOLS  # Default

    if args.symbols_file:
        # Load from file
        try:
            from pathlib import Path
            filepath = Path(args.symbols_file)
            if not filepath.exists():
                print(f"❌ Error: File not found: {args.symbols_file}")
                print("\nCreate it first by running: python download_stock_list.py")
                return

            with open(filepath, 'r') as f:
                symbols = [line.strip() for line in f if line.strip()]

            print(f"✅ Loaded {len(symbols)} symbols from {args.symbols_file}")

        except Exception as e:
            print(f"❌ Error loading symbols file: {e}")
            return

    elif args.symbols:
        # Use command-line symbols
        symbols = args.symbols

    # Print banner
    print("\n" + "="*80)
    print("🤖 Automated Trading Scanner")
    print("   Powered by Yahoo Finance + Python")
    print("="*80)

    # Clean up any stale orders from previous runs
    cleanup_stale_orders()

    # Check and update stock list if needed
    if args.symbols_file:
        check_and_update_stock_list()

    # Run scanner
    if args.schedule:
        scheduled_scan(symbols, args.strategy, args.dry_run)
    else:
        run_scan(symbols, args.strategy, args.dry_run)


if __name__ == "__main__":
    main()

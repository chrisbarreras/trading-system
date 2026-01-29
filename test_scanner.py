"""
Test the scanner components without executing trades.
"""
from scanner.data_source import YahooFinanceSource
from scanner.strategies import RSIStrategy, MACDStrategy, ComboStrategy
from scanner.scanner import MarketScanner


def test_data_source():
    """Test Yahoo Finance data fetching."""
    print("\n" + "="*80)
    print("Testing Yahoo Finance Data Source")
    print("="*80 + "\n")

    yf = YahooFinanceSource()

    # Test getting bars
    print("Fetching AAPL data...")
    df = yf.get_bars("AAPL", period="1mo", interval="1d")
    print(f"✅ Retrieved {len(df)} bars")
    print(f"   Latest close: ${df['close'].iloc[-1]:.2f}")
    print(f"   Columns: {list(df.columns)}\n")

    # Test current price
    print("Getting current price...")
    price = yf.get_current_price("AAPL")
    print(f"✅ Current price: ${price:.2f}\n")


def test_strategies():
    """Test technical analysis strategies."""
    print("\n" + "="*80)
    print("Testing Technical Strategies")
    print("="*80 + "\n")

    yf = YahooFinanceSource()
    df = yf.get_bars("AAPL", period="3mo", interval="1d")

    strategies = [
        RSIStrategy(),
        MACDStrategy(),
        ComboStrategy()
    ]

    for strategy in strategies:
        print(f"\n{strategy.name}:")
        print("-" * 40)
        result = strategy.analyze(df, "AAPL")

        print(f"Symbol: {result['symbol']}")
        print(f"Price: ${result['price']:.2f}")

        if 'rsi' in result:
            print(f"RSI: {result['rsi']:.1f}")
        if 'macd' in result:
            print(f"MACD: {result['macd']:.2f}")

        if result['action']:
            print(f"Action: {result['action'].upper()} ✅")
            for sig in result['signals']:
                print(f"  - {sig}")
        else:
            print("Action: HOLD")

        print()


def test_scanner():
    """Test full scanner (dry run)."""
    print("\n" + "="*80)
    print("Testing Full Scanner (Dry Run)")
    print("="*80 + "\n")

    from scanner.scanner import create_scanner

    scanner = create_scanner(
        symbols=["AAPL", "MSFT", "NVDA"],
        strategy_name="rsi",
        data_source="yahoo"
    )

    # Dry run - don't execute trades
    scanner.scan_and_execute(dry_run=True)


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🧪 Scanner Component Tests")
    print("="*80)

    try:
        test_data_source()
        test_strategies()
        test_scanner()

        print("\n" + "="*80)
        print("✅ All tests passed!")
        print("="*80 + "\n")

        print("Next steps:")
        print("1. Start your trading system: python -m uvicorn app.main:app --reload --port 8080")
        print("2. Run scanner in dry-run mode: python run_scanner.py --dry-run")
        print("3. When ready, run for real: python run_scanner.py\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

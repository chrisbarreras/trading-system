"""
Standalone backtesting CLI.

Loads strategy configuration from accounts.yaml, fetches historical data
from Alpaca, and simulates the strategy walk-forward to produce performance metrics.

Usage:
    # Backtest a single account
    python run_backtest.py --account bt_swing_rsi --start 2024-01-01 --end 2024-12-31

    # Compare all backtest_accounts side by side
    python run_backtest.py --compare --start 2024-01-01 --end 2024-12-31

    # With custom capital and CSV trade output
    python run_backtest.py --account bt_swing_rsi --start 2023-01-01 --end 2024-01-01 \\
        --capital 50000 --output trades.csv
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from trading.config_loader import load_accounts_config, AccountConfig
from trading.account_runner import _STRATEGY_MAP
from backtest.engine import BacktestEngine
from backtest.report import print_report, write_csv


def _setup_logging(debug: bool) -> None:
    """Configure structlog for the backtest CLI."""
    import structlog

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def _run_account(
    account_config: AccountConfig,
    symbols: list,
    start: datetime,
    end: datetime,
    capital: float,
) -> dict:
    """Run a single backtest and return the result dict."""
    cls = _STRATEGY_MAP[account_config.strategy_name]
    strategy = cls(**account_config.strategy_params)
    interval = "15m" if account_config.type == "day" else "1d"

    engine = BacktestEngine(
        strategy=strategy,
        symbols=symbols,
        start=start,
        end=end,
        interval=interval,
        initial_capital=capital,
        risk=account_config.risk,
        alpaca_api_key=account_config.alpaca_api_key,
        alpaca_secret_key=account_config.alpaca_secret_key,
        account_type=account_config.type,
    )
    return engine.run()


def _print_comparison(results: list) -> None:
    """Print a side-by-side comparison table of multiple backtest results."""
    print("\n" + "=" * 90)
    print("  STRATEGY COMPARISON")
    print("=" * 90)
    fmt = "  {:<28} {:>7} {:>8} {:>8} {:>8} {:>9} {:>8}"
    print(fmt.format("Strategy", "Trades", "Win %", "P&L %", "PF", "MaxDD %", "Sharpe"))
    print("  " + "-" * 86)

    for name, result in results:
        m = result["metrics"]
        if m.get("total_trades", 0) == 0:
            print(f"  {name:<28} {'no trades':>7}")
            continue
        print(fmt.format(
            name[:28],
            m["total_trades"],
            f"{m['win_rate_pct']}%",
            f"{m['total_pnl_pct']}%",
            str(m["profit_factor"]),
            f"{m['max_drawdown_pct']}%",
            str(m["sharpe_ratio"]),
        ))

    print("=" * 90 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Backtest trading strategies against historical Alpaca data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test with a handful of symbols
  python run_backtest.py --account bt_swing_rsi --start 2024-01-01 --end 2024-12-31 \\
      --symbols AAPL MSFT NVDA GOOGL TSLA

  # Full run — single strategy against all 500 symbols
  python run_backtest.py --account bt_swing_rsi --start 2024-01-01 --end 2024-12-31

  # Compare all strategies (uses --symbols for a quick sanity check)
  python run_backtest.py --compare --start 2024-01-01 --end 2024-12-31 \\
      --symbols AAPL MSFT NVDA GOOGL TSLA

  # Custom capital, save trades to CSV
  python run_backtest.py --account bt_swing_macd --start 2023-01-01 --end 2024-01-01 \\
      --capital 50000 --output macd_trades.csv
        """,
    )
    parser.add_argument(
        "--account",
        default=None,
        help="Account ID from accounts.yaml backtest_accounts section (e.g. bt_swing_rsi)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run all backtest_accounts and show a side-by-side comparison",
    )
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end",   required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--capital",
        type=float,
        default=100_000.0,
        help="Starting capital in USD (default: 100000)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        metavar="TICKER",
        help="Space-separated list of symbols to test (e.g. --symbols AAPL MSFT NVDA). "
             "Overrides --symbols-file.",
    )
    parser.add_argument(
        "--symbols-file",
        default=None,
        help="Override symbols file path",
    )
    parser.add_argument(
        "--config",
        default="accounts.yaml",
        help="Path to accounts config file (default: accounts.yaml)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="CSV file for trade-by-trade output (single account only)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (shows every signal and skip reason)",
    )
    args = parser.parse_args()

    _setup_logging(args.debug)

    if not args.account and not args.compare:
        parser.error("Specify --account <id> or --compare.")

    # Parse dates
    try:
        start = datetime.strptime(args.start, "%Y-%m-%d")
        end   = datetime.strptime(args.end,   "%Y-%m-%d")
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        return
    if start >= end:
        print("Error: --start must be before --end.")
        return

    # Load config
    system_config = load_accounts_config(args.config)

    # Load symbols — CLI list takes priority, then file
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
        print(f"Using {len(symbols)} symbol(s) from command line: {', '.join(symbols)}")
    else:
        symbols_file = args.symbols_file or system_config.symbols_file
        symbols_path = Path(symbols_file)
        if not symbols_path.exists():
            print(f"Error: symbols file not found: {symbols_file}")
            return
        with open(symbols_path) as f:
            symbols = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(symbols)} symbols from {symbols_file}")

    # -----------------------------------------------------------------------
    # Compare mode: run all backtest_accounts
    # -----------------------------------------------------------------------
    if args.compare:
        accounts = system_config.backtest_accounts
        if not accounts:
            print("No backtest_accounts found in accounts.yaml.")
            return

        print(f"\nComparing {len(accounts)} strategies  |  {args.start} → {args.end}  |  capital ${args.capital:,.0f}\n")

        comparison = []
        for acc in accounts:
            print(f"  Running {acc.name}...", end=" ", flush=True)
            try:
                result = _run_account(acc, symbols, start, end, args.capital)
                trades = len(result.get("trades", []))
                print(f"done ({trades} trades)")
                comparison.append((acc.name, result))
            except Exception as e:
                print(f"FAILED: {e}")
                comparison.append((acc.name, {"metrics": {"total_trades": 0}}))

        _print_comparison(comparison)
        return

    # -----------------------------------------------------------------------
    # Single account mode
    # -----------------------------------------------------------------------
    # Search both accounts and backtest_accounts sections
    all_accounts = system_config.accounts + system_config.backtest_accounts
    account_config = next((a for a in all_accounts if a.id == args.account), None)
    if account_config is None:
        ids = [a.id for a in all_accounts]
        print(f"Error: account '{args.account}' not found in {args.config}.")
        print(f"Available: {ids}")
        return

    print(f"\nBacktesting {account_config.name}")
    print(f"  Strategy:  {account_config.strategy_name} {account_config.strategy_params}")
    print(f"  Type:      {account_config.type}")
    print(f"  Period:    {args.start} to {args.end}")
    print(f"  Capital:   ${args.capital:,.2f}")
    print(f"  Symbols:   {len(symbols)}\n")

    result = _run_account(account_config, symbols, start, end, args.capital)
    print_report(result["metrics"], result["trades"], result.get("signal_stats"))

    if args.output:
        write_csv(result["trades"], args.output)


if __name__ == "__main__":
    main()

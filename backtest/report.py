"""
Backtest report formatting — console table and optional CSV output.
"""
import csv
from typing import List, Optional


def print_report(metrics: dict, trades: List[dict], signal_stats: Optional[dict] = None) -> None:
    """Print a formatted backtest report to stdout."""
    print("\n" + "=" * 60)
    print("  BACKTEST RESULTS")
    print("=" * 60)

    if metrics.get("total_trades", 0) == 0:
        print(f"  {metrics.get('message', 'No trades.')}")
        print("=" * 60)
        if signal_stats:
            _print_signal_stats(signal_stats)
        return

    rows = [
        ("Total trades",        str(metrics["total_trades"])),
        ("Winning trades",      f"{metrics['winning_trades']} ({metrics['win_rate_pct']}%)"),
        ("Losing trades",       str(metrics["losing_trades"])),
        ("",                    ""),
        ("Total P&L",           f"${metrics['total_pnl_usd']:,.2f}  ({metrics['total_pnl_pct']}%)"),
        ("Final capital",       f"${metrics['final_capital_usd']:,.2f}"),
        ("",                    ""),
        ("Gross profit",        f"${metrics['gross_profit_usd']:,.2f}"),
        ("Gross loss",          f"${metrics['gross_loss_usd']:,.2f}"),
        ("Profit factor",       str(metrics["profit_factor"])),
        ("Avg win",             f"${metrics['avg_win_usd']:,.2f}"),
        ("Avg loss",            f"${metrics['avg_loss_usd']:,.2f}"),
        ("",                    ""),
        ("Max drawdown",        f"{metrics['max_drawdown_pct']}%"),
        ("Sharpe ratio",        str(metrics["sharpe_ratio"])),
    ]

    for label, value in rows:
        if label == "":
            print()
        else:
            print(f"  {label:<20} {value}")

    if signal_stats:
        print()
        _print_signal_stats(signal_stats)

    print("\n" + "=" * 60)
    print(f"  TRADES ({len(trades)} total — showing last 10)")
    print("=" * 60)
    print(f"  {'Symbol':<6} {'Entry':>8} {'Exit':>8} {'Qty':>5} {'P&L':>9} {'%':>7}  Reason")
    print("  " + "-" * 56)
    for t in trades[-10:]:
        print(
            f"  {t['symbol']:<6} "
            f"${t['entry_price']:>7.2f} "
            f"${t['exit_price']:>7.2f} "
            f"{t['quantity']:>5} "
            f"${t['pnl_usd']:>8.2f} "
            f"{t['pnl_pct']:>6.1f}%  "
            f"{t['exit_reason']}"
        )
    print("=" * 60 + "\n")


def _print_signal_stats(s: dict) -> None:
    """Print signal frequency breakdown."""
    print("  " + "-" * 40)
    print("  Signal Statistics")
    print("  " + "-" * 40)

    scanned = s["symbols_scanned"]
    buy_total = s["buy_signals"]
    buy_exec = s["buy_executed"]
    skipped_max = s["buy_skipped_max_pos"]
    skipped_hold = s["buy_skipped_holding"]
    skipped_cap = s["buy_skipped_capital"]
    sell_total = s["sell_signals"]
    sell_exec = s["sell_executed"]
    sell_skip = s["sell_skipped_not_holding"]
    eob = s["eob_closes"]

    pct_with_signal = f"({buy_exec / scanned * 100:.1f}% of symbols)" if scanned else ""
    exec_pct = f"({buy_exec / buy_total * 100:.0f}% of signals)" if buy_total else ""

    print(f"  {'Symbols scanned:':<28} {scanned:>5}")
    print(f"  {'Buy signals fired:':<28} {buy_total:>5}  {pct_with_signal}")
    print(f"  {'Buy signals executed:':<28} {buy_exec:>5}  {exec_pct}")
    if skipped_max or skipped_hold or skipped_cap:
        skipped_total = skipped_max + skipped_hold + skipped_cap
        print(
            f"  {'Buy signals skipped:':<28} {skipped_total:>5}"
            f"  — max positions: {skipped_max}, already holding: {skipped_hold}, capital: {skipped_cap}"
        )
    print(f"  {'Sell signals fired:':<28} {sell_total:>5}")
    print(f"  {'Sell signals executed:':<28} {sell_exec:>5}")
    if sell_skip:
        print(f"  {'Sell skipped (not holding):':<28} {sell_skip:>5}")
    if eob:
        print(f"  {'Closed at end-of-backtest:':<28} {eob:>5}")


def write_csv(trades: List[dict], path: str) -> None:
    """Write trade-by-trade results to a CSV file."""
    if not trades:
        return
    fieldnames = list(trades[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)
    print(f"Trade details written to {path}")

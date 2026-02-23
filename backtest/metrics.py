"""
Backtest performance metrics.
"""
import math
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class ClosedTrade:
    symbol: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    quantity: int
    pnl: float          # dollar P&L
    pnl_pct: float      # percentage P&L relative to entry cost
    exit_reason: str    # "sell_signal" | "eod_close" | "end_of_backtest"


def calculate_metrics(trades: List[ClosedTrade], initial_capital: float) -> dict:
    """
    Calculate performance metrics from a list of closed trades.

    Args:
        trades: List of completed trades.
        initial_capital: Starting capital in USD.

    Returns:
        Dict with performance metrics.
    """
    if not trades:
        return {
            "total_trades": 0,
            "message": "No trades executed during backtest period.",
        }

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]

    total_pnl = sum(t.pnl for t in trades)
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))

    win_rate = len(wins) / len(trades) * 100
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
    avg_win = (gross_profit / len(wins)) if wins else 0.0
    avg_loss = (gross_loss / len(losses)) if losses else 0.0

    max_drawdown = _calculate_max_drawdown(trades, initial_capital)
    sharpe = _calculate_sharpe(trades, initial_capital)

    return {
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "total_pnl_usd": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / initial_capital * 100, 2),
        "final_capital_usd": round(initial_capital + total_pnl, 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win_usd": round(avg_win, 2),
        "avg_loss_usd": round(avg_loss, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
    }


def _calculate_max_drawdown(trades: List[ClosedTrade], initial_capital: float) -> float:
    """Calculate maximum peak-to-trough drawdown as a percentage."""
    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0

    for trade in sorted(trades, key=lambda t: t.exit_time):
        equity += trade.pnl
        if equity > peak:
            peak = equity
        drawdown = (peak - equity) / peak * 100
        if drawdown > max_dd:
            max_dd = drawdown

    return max_dd


def _calculate_sharpe(
    trades: List[ClosedTrade],
    initial_capital: float,
    risk_free_rate: float = 0.05,
) -> float:
    """
    Calculate annualized Sharpe ratio from trade P&L.

    Uses per-trade returns. Annualizes by assuming 252 trading days/year.
    """
    if len(trades) < 2:
        return 0.0

    returns = [t.pnl / initial_capital for t in trades]
    n = len(returns)
    mean_return = sum(returns) / n
    variance = sum((r - mean_return) ** 2 for r in returns) / (n - 1)
    std_return = math.sqrt(variance) if variance > 0 else 0.0

    if std_return == 0:
        return 0.0

    daily_rf = risk_free_rate / 252
    sharpe = (mean_return - daily_rf) / std_return * math.sqrt(252)
    return sharpe

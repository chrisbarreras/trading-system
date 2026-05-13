"""
Position-level exit rules: stop-loss, take-profit, max-hold-days.

These are evaluated independently of the entry strategy's analyze() output.
Whatever opened a position, these rules decide whether to close it.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExitConfig:
    """
    All fields are optional — None disables that rule.

    stop_loss_pct:    exit if price falls this fraction below entry (0.08 = -8%)
    take_profit_pct:  exit if price rises this fraction above entry (0.15 = +15%)
    max_hold_days:    exit after this many calendar days since entry
    """
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_hold_days: Optional[int] = None

    def is_active(self) -> bool:
        return any(
            v is not None
            for v in (self.stop_loss_pct, self.take_profit_pct, self.max_hold_days)
        )


def evaluate_exit(
    entry_price: float,
    current_price: float,
    entry_time: Optional[datetime],
    now: datetime,
    config: ExitConfig,
) -> Optional[str]:
    """
    Return a human-readable exit reason if any rule fires, else None.

    Rule precedence: stop_loss > take_profit > max_hold_days.
    Stop-loss wins on the rare bar where price gaps through both bands.

    If entry_time is None the max_hold_days rule is skipped silently
    (the broker didn't surface an entry timestamp for this position).
    """
    if entry_price <= 0:
        return None

    pct_change = (current_price - entry_price) / entry_price

    if config.stop_loss_pct is not None and pct_change <= -config.stop_loss_pct:
        return (
            f"stop_loss: {pct_change * 100:.1f}% <= -{config.stop_loss_pct * 100:.1f}%"
        )

    if config.take_profit_pct is not None and pct_change >= config.take_profit_pct:
        return (
            f"take_profit: {pct_change * 100:.1f}% >= {config.take_profit_pct * 100:.1f}%"
        )

    if config.max_hold_days is not None and entry_time is not None:
        held_days = (now - entry_time).days
        if held_days >= config.max_hold_days:
            return f"max_hold_days: {held_days} >= {config.max_hold_days}"

    return None

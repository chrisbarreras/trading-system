"""
BacktestEngine: walk-forward simulation of a trading strategy on historical data.
No lookahead bias — at bar N, only bars [0..N] are visible to the strategy.

Processes all symbols' bars in chronological order (time-ordered simulation)
so portfolio constraints (max_positions, capital) are enforced in real time.
"""
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import structlog

from scanner.data_source import AlpacaDataSource
from scanner.strategies import TechnicalStrategy
from trading.config_loader import RiskConfig
from backtest.metrics import ClosedTrade, calculate_metrics

logger = structlog.get_logger()
ET = ZoneInfo("America/New_York")


@dataclass
class OpenPosition:
    symbol: str
    entry_price: float
    entry_time: datetime
    quantity: int


@dataclass
class SignalStats:
    """Tracks signal frequency and execution reasons for backtest transparency."""
    symbols_scanned: int = 0
    buy_signals: int = 0
    buy_executed: int = 0
    buy_skipped_max_pos: int = 0
    buy_skipped_holding: int = 0
    buy_skipped_capital: int = 0
    sell_signals: int = 0
    sell_executed: int = 0
    sell_skipped_not_holding: int = 0
    eob_closes: int = 0

    def to_dict(self) -> dict:
        return {
            "symbols_scanned": self.symbols_scanned,
            "buy_signals": self.buy_signals,
            "buy_executed": self.buy_executed,
            "buy_skipped_max_pos": self.buy_skipped_max_pos,
            "buy_skipped_holding": self.buy_skipped_holding,
            "buy_skipped_capital": self.buy_skipped_capital,
            "sell_signals": self.sell_signals,
            "sell_executed": self.sell_executed,
            "sell_skipped_not_holding": self.sell_skipped_not_holding,
            "eob_closes": self.eob_closes,
        }


class BacktestEngine:
    """
    Simulates a strategy against historical Alpaca data.

    Fetches all symbol data upfront, then replays bars in chronological order
    across all symbols simultaneously. This correctly enforces portfolio
    constraints (max_positions, capital) in real time rather than per-symbol.
    """

    def __init__(
        self,
        strategy: TechnicalStrategy,
        symbols: List[str],
        start: datetime,
        end: datetime,
        interval: str,
        initial_capital: float,
        risk: RiskConfig,
        alpaca_api_key: str,
        alpaca_secret_key: str,
        account_type: str = "swing",  # "swing" | "day"
        warmup_bars: int = 252,
    ):
        self.strategy = strategy
        self.symbols = symbols
        self.start = start
        self.end = end
        self.interval = interval
        self.initial_capital = initial_capital
        self.risk = risk
        self.account_type = account_type
        self.warmup_bars = warmup_bars

        self.data_source = AlpacaDataSource(
            api_key=alpaca_api_key,
            secret_key=alpaca_secret_key,
        )

    def run(self) -> dict:
        """
        Run the backtest and return metrics.

        Phase 1: Fetch historical data for all symbols (with indicator warmup).
        Phase 2: Build a time-sorted event list of all bars in the trading period.
        Phase 3: Walk forward through events, enforcing portfolio constraints
                 (max_positions, capital) in real time across all symbols.

        Returns:
            Dict with performance metrics, trade list, and signal statistics.
        """
        logger.info(
            "backtest_starting",
            strategy=self.strategy.name,
            symbols=len(self.symbols),
            start=self.start.date().isoformat(),
            end=self.end.date().isoformat(),
            interval=self.interval,
            capital=self.initial_capital,
        )

        # -------------------------------------------------------------------
        # Phase 1: Fetch data for all symbols
        # Fetch extra history before start so indicators (e.g. 200-day SMA)
        # can warm up. 2× calendar days ≈ 1.4× trading days, covering the
        # longest standard lookback (200 bars).
        # -------------------------------------------------------------------
        all_data: Dict[str, object] = {}  # symbol -> reset-indexed DataFrame
        fetch_start = self.start - timedelta(days=self.warmup_bars * 2)

        for symbol in self.symbols:
            try:
                df = self.data_source.get_bars(
                    symbol,
                    interval=self.interval,
                    start=fetch_start,
                    end=self.end,
                )
                if df is None or len(df) < 3:
                    continue
                all_data[symbol] = df.reset_index()
                time.sleep(0.2)  # be polite to the API
            except Exception as e:
                logger.error("backtest_data_fetch_failed", symbol=symbol, error=str(e))

        logger.info("backtest_data_fetched", symbols_loaded=len(all_data))

        # -------------------------------------------------------------------
        # Phase 2: Build time-sorted event list
        # Only include bars on or after self.start (warmup bars are excluded
        # from trading but are still in each symbol's DataFrame for indicator
        # computation via the growing window slice df.iloc[:i+1]).
        # -------------------------------------------------------------------
        events: List[Tuple[datetime, str, int]] = []
        for symbol, df in all_data.items():
            for i in range(len(df)):
                bar_time = self._bar_time(df.iloc[i])
                if bar_time >= self.start:
                    events.append((bar_time, symbol, i))

        events.sort(key=lambda e: e[0])
        logger.info("backtest_events_built", event_count=len(events))

        # -------------------------------------------------------------------
        # Phase 3: Walk forward in time across all symbols simultaneously
        # -------------------------------------------------------------------
        closed_trades: List[ClosedTrade] = []
        open_positions: Dict[str, OpenPosition] = {}
        capital = self.initial_capital
        stats = SignalStats(symbols_scanned=len(all_data))

        for bar_time, symbol, i in events:
            df = all_data[symbol]
            # Window grows as we advance: bars [0..i] visible, no lookahead.
            window = df.iloc[:i + 1].copy()

            try:
                result = self.strategy.analyze(window, symbol)
            except Exception as e:
                logger.debug(
                    "strategy_analyze_error",
                    symbol=symbol,
                    bar=i,
                    error=str(e),
                )
                continue

            action = result.get("action")
            price = float(result.get("price", window.iloc[-1].get("close", 0)))
            if price <= 0:
                continue

            # EOD close for day trading (simulate 15:55 ET bar)
            if self.account_type == "day" and symbol in open_positions:
                if self._is_eod_bar(bar_time):
                    pos = open_positions.pop(symbol)
                    trade = self._close_position(pos, price, bar_time, "eod_close")
                    closed_trades.append(trade)
                    capital += trade.pnl + pos.entry_price * pos.quantity
                    logger.info(
                        "backtest_eod_close",
                        symbol=symbol,
                        date=bar_time.date().isoformat(),
                        exit_price=price,
                        entry_price=pos.entry_price,
                        quantity=pos.quantity,
                        pnl=trade.pnl,
                        pnl_pct=trade.pnl_pct,
                    )
                    continue

            if action == "buy":
                stats.buy_signals += 1
                if symbol in open_positions:
                    stats.buy_skipped_holding += 1
                    logger.debug(
                        "backtest_buy_skipped_already_holding",
                        symbol=symbol,
                        date=bar_time.date().isoformat(),
                        reason=result.get("signals"),
                    )
                elif len(open_positions) >= self.risk.max_positions:
                    stats.buy_skipped_max_pos += 1
                    logger.debug(
                        "backtest_buy_skipped_max_positions",
                        symbol=symbol,
                        date=bar_time.date().isoformat(),
                        open_positions=len(open_positions),
                        reason=result.get("signals"),
                    )
                else:
                    quantity = self._calc_quantity(price, capital)
                    if quantity <= 0:
                        stats.buy_skipped_capital += 1
                        logger.debug(
                            "backtest_buy_skipped_insufficient_capital",
                            symbol=symbol,
                            date=bar_time.date().isoformat(),
                            price=price,
                            capital=round(capital, 2),
                        )
                    else:
                        cost = quantity * price
                        if cost > capital:
                            stats.buy_skipped_capital += 1
                        else:
                            open_positions[symbol] = OpenPosition(
                                symbol=symbol,
                                entry_price=price,
                                entry_time=bar_time,
                                quantity=quantity,
                            )
                            capital -= cost
                            stats.buy_executed += 1
                            logger.info(
                                "backtest_buy",
                                symbol=symbol,
                                date=bar_time.date().isoformat(),
                                price=price,
                                quantity=quantity,
                                cost=round(cost, 2),
                                capital_remaining=round(capital, 2),
                                open_positions=len(open_positions),
                                reason=result.get("signals"),
                            )

            elif action == "sell":
                stats.sell_signals += 1
                if symbol in open_positions:
                    pos = open_positions.pop(symbol)
                    trade = self._close_position(pos, price, bar_time, "sell_signal")
                    closed_trades.append(trade)
                    capital += trade.pnl + pos.entry_price * pos.quantity
                    stats.sell_executed += 1
                    logger.info(
                        "backtest_sell",
                        symbol=symbol,
                        date=bar_time.date().isoformat(),
                        exit_price=price,
                        entry_price=pos.entry_price,
                        quantity=pos.quantity,
                        pnl=trade.pnl,
                        pnl_pct=trade.pnl_pct,
                        reason=result.get("signals"),
                    )
                else:
                    stats.sell_skipped_not_holding += 1
                    logger.debug(
                        "backtest_sell_skipped_not_holding",
                        symbol=symbol,
                        date=bar_time.date().isoformat(),
                        reason=result.get("signals"),
                    )

        # Close any positions still open at end of backtest at last known price.
        for symbol, pos in list(open_positions.items()):
            df = all_data[symbol]
            last_bar = df.iloc[-1]
            last_price = float(last_bar.get("close", pos.entry_price))
            last_time = self._bar_time(last_bar)
            trade = self._close_position(pos, last_price, last_time, "end_of_backtest")
            closed_trades.append(trade)
            capital += trade.pnl + pos.entry_price * pos.quantity
            stats.eob_closes += 1
            logger.info(
                "backtest_position_closed_eob",
                symbol=symbol,
                exit_price=last_price,
                entry_price=pos.entry_price,
                entry_date=pos.entry_time.date().isoformat() if pos.entry_time else None,
                pnl=trade.pnl,
                pnl_pct=trade.pnl_pct,
            )

        metrics = calculate_metrics(closed_trades, self.initial_capital)
        return {
            "metrics": metrics,
            "trades": [self._trade_to_dict(t) for t in closed_trades],
            "signal_stats": stats.to_dict(),
        }

    def _calc_quantity(self, price: float, capital: float) -> int:
        """Calculate share quantity using risk config."""
        target_usd = min(
            capital * self.risk.position_size_pct,
            self.risk.max_position_size_usd,
            capital * (1 - self.risk.buying_power_reserve_pct),
        )
        quantity = int(target_usd / price)
        cost = quantity * price
        if cost < self.risk.min_trade_size_usd:
            return 0
        return max(1, quantity)

    def _close_position(
        self,
        pos: OpenPosition,
        exit_price: float,
        exit_time: datetime,
        reason: str,
    ) -> ClosedTrade:
        pnl = (exit_price - pos.entry_price) * pos.quantity
        pnl_pct = (exit_price / pos.entry_price - 1) * 100
        return ClosedTrade(
            symbol=pos.symbol,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            quantity=pos.quantity,
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            exit_reason=reason,
        )

    def _bar_time(self, bar) -> datetime:
        """Extract bar timestamp as a timezone-naive UTC datetime."""
        try:
            ts = bar.get("timestamp") or bar.name
            if hasattr(ts, "to_pydatetime"):
                dt = ts.to_pydatetime()
            else:
                dt = datetime.fromisoformat(str(ts))
            # Strip tzinfo so all trade timestamps are consistently naive
            return dt.replace(tzinfo=None)
        except Exception:
            return self.end

    def _is_eod_bar(self, bar_time: datetime) -> bool:
        """True if bar is at or after 15:55 ET."""
        try:
            from datetime import timezone
            # bar_time is naive UTC after _bar_time() strips tzinfo; re-attach UTC before converting
            et = bar_time.replace(tzinfo=timezone.utc).astimezone(ET)
            return et.hour == 15 and et.minute >= 55
        except Exception:
            return False

    @staticmethod
    def _trade_to_dict(t: ClosedTrade) -> dict:
        return {
            "symbol": t.symbol,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
            "quantity": t.quantity,
            "pnl_usd": t.pnl,
            "pnl_pct": t.pnl_pct,
            "exit_reason": t.exit_reason,
        }

"""
AccountRunner: manages one Alpaca paper account.
Scans the symbol universe, generates signals, and executes trades directly.
"""
from datetime import datetime
from typing import List, Optional
import structlog

from app.core.broker import AlpacaBroker
from scanner.data_source import YahooFinanceSource, AlpacaDataSource
from scanner.strategies import (
    TechnicalStrategy,
    RSIStrategy,
    MACDStrategy,
    MovingAverageCrossStrategy,
    BollingerBandsStrategy,
    ComboStrategy,
)
from trading.config_loader import AccountConfig
from trading.direct_executor import DirectExecutor

logger = structlog.get_logger()

# Scan parameters by account type
_SWING_PARAMS = {"period": "3mo", "interval": "1d"}
_DAY_PARAMS = {"period": "5d", "interval": "15m"}

_STRATEGY_MAP = {
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "ma_cross": MovingAverageCrossStrategy,
    "bb": BollingerBandsStrategy,
    "combo": ComboStrategy,
}


class AccountRunner:
    """
    Manages scanning and trade execution for a single Alpaca paper account.
    """

    def __init__(self, config: AccountConfig, symbols: List[str]):
        self.config = config
        self.symbols = symbols
        self.log = logger.bind(account=config.id, strategy=config.strategy_name)

        self.broker = AlpacaBroker(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            paper=True,
        )
        self.executor = DirectExecutor(
            broker=self.broker,
            risk=config.risk,
            account_id=config.id,
        )
        self.scanner_strategy = self._build_scanner_strategy()

        # Data source: Yahoo for swing (daily bars), Alpaca for day (intraday bars)
        if config.type == "day":
            self.data_source = AlpacaDataSource(
                api_key=config.alpaca_api_key,
                secret_key=config.alpaca_secret_key,
            )
        else:
            self.data_source = YahooFinanceSource()

        self._scan_params = _DAY_PARAMS if config.type == "day" else _SWING_PARAMS
        self.last_scan: Optional[datetime] = None
        self.scan_count: int = 0

    def run_scan_cycle(self) -> None:
        """
        Scan all symbols and execute any signals found.
        Fetches current positions once to avoid redundant API calls.
        """
        self.log.info("scan_cycle_starting", symbol_count=len(self.symbols))

        try:
            positions = self.broker.get_positions()
            account_info = self.broker.get_account()
        except Exception as e:
            self.log.error("failed_to_fetch_account_state", error=str(e))
            return

        held_symbols = {p["symbol"] for p in positions}
        account_info["open_positions"] = len(held_symbols)
        open_count = len(held_symbols)

        bought, sold, skipped = 0, 0, 0

        for symbol in self.symbols:
            try:
                df = self.data_source.get_bars(
                    symbol,
                    period=self._scan_params["period"],
                    interval=self._scan_params["interval"],
                )
                if df is None or len(df) < 3:
                    skipped += 1
                    continue

                result = self.scanner_strategy.analyze(df, symbol)
                action = result.get("action")

                if action is not None:
                    self.log.info(
                        "signal_detected",
                        symbol=symbol,
                        action=action,
                        price=result.get("price"),
                        reason=result.get("signals"),
                    )

                if action == "buy":
                    if symbol in held_symbols:
                        self.log.debug("buy_skipped_already_holding", symbol=symbol)
                        continue
                    if open_count >= self.config.risk.max_positions:
                        self.log.debug(
                            "buy_skipped_max_positions",
                            symbol=symbol,
                            open_positions=open_count,
                        )
                        continue
                    order = self.executor.execute_buy(
                        symbol=symbol,
                        signal_price=result["price"],
                        account_info=dict(account_info),  # pass copy; open_count may change
                    )
                    if order:
                        held_symbols.add(symbol)
                        open_count += 1
                        account_info["open_positions"] = open_count
                        bought += 1

                elif action == "sell":
                    if symbol not in held_symbols:
                        self.log.debug("sell_skipped_not_holding", symbol=symbol)
                        continue
                    order = self.executor.execute_sell(symbol=symbol)
                    if order:
                        held_symbols.discard(symbol)
                        open_count -= 1
                        account_info["open_positions"] = open_count
                        sold += 1

            except Exception as e:
                self.log.error("symbol_scan_failed", symbol=symbol, error=str(e))
                skipped += 1

        self.last_scan = datetime.utcnow()
        self.scan_count += 1
        self.log.info(
            "scan_cycle_complete",
            bought=bought,
            sold=sold,
            skipped=skipped,
            open_positions=open_count,
        )

    def close_all_positions(self) -> None:
        """
        Close every open position. Used for EOD day-trading close.
        """
        self.log.info("closing_all_positions_eod")
        try:
            positions = self.broker.get_positions()
        except Exception as e:
            self.log.error("failed_to_fetch_positions_for_eod_close", error=str(e))
            return

        for pos in positions:
            self.executor.execute_sell(pos["symbol"])

    def get_status(self) -> dict:
        """Return a status snapshot for the admin API."""
        try:
            account = self.broker.get_account()
            positions = self.broker.get_positions()
        except Exception as e:
            return {
                "id": self.config.id,
                "name": self.config.name,
                "error": str(e),
            }

        return {
            "id": self.config.id,
            "name": self.config.name,
            "type": self.config.type,
            "strategy": self.config.strategy_name,
            "buying_power": account.get("buying_power"),
            "portfolio_value": account.get("portfolio_value"),
            "open_positions": len(positions),
            "positions": [p["symbol"] for p in positions],
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "scan_count": self.scan_count,
        }

    def _build_scanner_strategy(self) -> TechnicalStrategy:
        cls = _STRATEGY_MAP.get(self.config.strategy_name)
        if cls is None:
            raise ValueError(
                f"Unknown strategy '{self.config.strategy_name}' for account '{self.config.id}'. "
                f"Valid options: {list(_STRATEGY_MAP.keys())}"
            )
        return cls(**self.config.strategy_params)

"""
Synchronous trade executor for scanner-driven signals.
Executes directly via AlpacaBroker — no HTTP hop, no database writes.
"""
from typing import Optional
import structlog

from app.core.broker import AlpacaBroker, BrokerError
from app.strategies.momentum import MomentumStrategy
from trading.config_loader import RiskConfig

logger = structlog.get_logger()


class DirectExecutor:
    """
    Sizes and submits orders for one account.
    Reuses MomentumStrategy's adaptive position sizing logic.
    """

    def __init__(self, broker: AlpacaBroker, risk: RiskConfig, account_id: str = ""):
        self.broker = broker
        self.risk = risk
        self.account_id = account_id
        self.log = logger.bind(account=account_id)

        # Build strategy config dict that MomentumStrategy expects
        self._strategy_config = {
            "position_size_pct": risk.position_size_pct,
            "max_positions": risk.max_positions,
            "max_position_size_usd": risk.max_position_size_usd,
            "min_buying_power": risk.min_buying_power,
            "min_trade_size_usd": risk.min_trade_size_usd,
            "buying_power_reserve_pct": risk.buying_power_reserve_pct,
            "position_sizing_mode": "adaptive",
        }
        self._sizing_strategy = MomentumStrategy(self._strategy_config)

    def execute_buy(self, symbol: str, signal_price: float, account_info: dict) -> Optional[dict]:
        """
        Size and submit a buy order.

        Args:
            symbol: Stock ticker.
            signal_price: Price from the scanner signal (used for initial sizing).
            account_info: Dict from broker.get_account() with open_positions count added.

        Returns:
            Order result dict, or None if rejected.
        """
        signal = {"ticker": symbol, "action": "buy", "price": signal_price}

        quantity = self._sizing_strategy.calculate_position_size(signal, account_info)
        if quantity <= 0:
            self.log.warning("position_size_zero_rejected", symbol=symbol)
            return None

        # Fetch live price and re-cap at max_position_size_usd
        current_price = self.broker.get_current_price(symbol)
        if current_price and current_price > 0:
            actual_cost = quantity * current_price
            if actual_cost > self.risk.max_position_size_usd:
                quantity = int(self.risk.max_position_size_usd / current_price)
                self.log.info(
                    "quantity_adjusted_for_live_price",
                    symbol=symbol,
                    signal_price=signal_price,
                    live_price=current_price,
                    adjusted_quantity=quantity,
                )

        if quantity <= 0:
            self.log.warning("quantity_zero_after_price_check", symbol=symbol)
            return None

        try:
            result = self.broker.submit_order(symbol=symbol, side="buy", quantity=quantity)
            self.log.info(
                "buy_order_submitted",
                symbol=symbol,
                quantity=quantity,
                order_id=result.get("order_id"),
            )
            return result
        except BrokerError as e:
            self.log.error("buy_order_failed", symbol=symbol, error=str(e))
            return None

    def execute_sell(self, symbol: str) -> Optional[dict]:
        """
        Close an existing position entirely.
        Caller must verify the position exists before calling.

        Args:
            symbol: Stock ticker.

        Returns:
            Order result dict, or None on failure.
        """
        try:
            result = self.broker.close_position(symbol)
            self.log.info("position_closed", symbol=symbol, order_id=result.get("order_id"))
            return result
        except BrokerError as e:
            self.log.error("sell_failed", symbol=symbol, error=str(e))
            return None

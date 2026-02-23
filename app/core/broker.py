"""
Alpaca Broker abstraction layer.
Handles all interactions with the Alpaca Trading API.
"""
from typing import Dict, List, Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
from alpaca.common.exceptions import APIError
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class BrokerError(Exception):
    """Custom exception for broker-related errors."""
    pass


class AlpacaBroker:
    """
    Alpaca trading broker abstraction.
    Provides methods to interact with Alpaca's trading API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True,
        extended_hours: bool = False,
    ):
        """
        Initialize Alpaca trading client.

        Args:
            api_key: Alpaca API key. If None, reads from settings.
            secret_key: Alpaca secret key. If None, reads from settings.
            paper: Whether to use paper trading (default True).
            extended_hours: Whether to use extended hours trading (default False).
        """
        if api_key is None or secret_key is None:
            settings = get_settings()
            api_key = api_key or settings.alpaca_api_key
            secret_key = secret_key or settings.alpaca_secret_key
            paper = settings.is_paper_trading
            extended_hours = settings.extended_hours_enabled

        self.extended_hours = extended_hours

        logger.info("initializing_alpaca_broker", paper=paper)

        self.client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper,
        )
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key,
        )

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the latest trade price for a symbol."""
        try:
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self.data_client.get_stock_latest_trade(request)
            if symbol in trades:
                return float(trades[symbol].price)
            return None
        except Exception as e:
            logger.error("failed_to_get_price", symbol=symbol, error=str(e))
            return None

    def get_account(self) -> Dict:
        """
        Get account information including buying power, equity, etc.

        Returns:
            Dict with account information

        Raises:
            BrokerError: If API call fails
        """
        try:
            account = self.client.get_account()
            return {
                "account_number": account.account_number,
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "equity": float(account.equity),
                "status": account.status,
                "currency": account.currency,
                "pattern_day_trader": account.pattern_day_trader,
            }
        except APIError as e:
            logger.error("failed_to_get_account", error=str(e))
            raise BrokerError(f"Failed to get account info: {str(e)}")

    def get_positions(self) -> List[Dict]:
        """
        Get all open positions.

        Returns:
            List of position dictionaries

        Raises:
            BrokerError: If API call fails
        """
        try:
            positions = self.client.get_all_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "side": pos.side,
                }
                for pos in positions
            ]
        except APIError as e:
            logger.error("failed_to_get_positions", error=str(e))
            raise BrokerError(f"Failed to get positions: {str(e)}")

    def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Submit an order to Alpaca.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            side: "buy" or "sell"
            quantity: Number of shares
            order_type: "market" or "limit"
            limit_price: Required for limit orders and extended hours

        Returns:
            Dict with order information

        Raises:
            BrokerError: If order submission fails
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            if self.extended_hours and limit_price is not None:
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=order_side,
                    limit_price=round(limit_price, 2),
                    time_in_force=TimeInForce.GTC,
                    extended_hours=True
                )
            else:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.DAY
                )

            # Submit order
            order = self.client.submit_order(order_request)

            logger.info(
                "order_submitted",
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_id=order.id,
                status=order.status
            )

            return {
                "order_id": order.id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": float(order.qty),
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            }

        except APIError as e:
            logger.error(
                "order_submission_failed",
                symbol=symbol,
                side=side,
                quantity=quantity,
                error=str(e)
            )
            raise BrokerError(f"Failed to submit order: {str(e)}")

    def get_order_status(self, order_id: str) -> Dict:
        """
        Get the status of a specific order.

        Args:
            order_id: Alpaca order ID

        Returns:
            Dict with order information

        Raises:
            BrokerError: If API call fails
        """
        try:
            order = self.client.get_order_by_id(order_id)
            return {
                "order_id": order.id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": float(order.qty),
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            }
        except APIError as e:
            logger.error("failed_to_get_order_status", order_id=order_id, error=str(e))
            raise BrokerError(f"Failed to get order status: {str(e)}")

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: Alpaca order ID

        Returns:
            True if cancellation successful

        Raises:
            BrokerError: If cancellation fails
        """
        try:
            self.client.cancel_order_by_id(order_id)
            logger.info("order_canceled", order_id=order_id)
            return True
        except APIError as e:
            logger.error("failed_to_cancel_order", order_id=order_id, error=str(e))
            raise BrokerError(f"Failed to cancel order: {str(e)}")

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a specific symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with position info, or None if no position exists

        Raises:
            BrokerError: If API call fails
        """
        try:
            position = self.client.get_open_position(symbol)
            return {
                "symbol": position.symbol,
                "qty": float(position.qty),
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "market_value": float(position.market_value),
                "unrealized_pl": float(position.unrealized_pl),
                "unrealized_plpc": float(position.unrealized_plpc),
                "side": position.side,
            }
        except APIError as e:
            if "position does not exist" in str(e).lower():
                return None
            logger.error("failed_to_get_position", symbol=symbol, error=str(e))
            raise BrokerError(f"Failed to get position: {str(e)}")

    def close_position(self, symbol: str) -> Dict:
        """
        Close an entire position for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with order information

        Raises:
            BrokerError: If closing position fails
        """
        try:
            order = self.client.close_position(symbol)
            logger.info("position_closed", symbol=symbol, order_id=order.id)
            return {
                "order_id": order.id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": float(order.qty),
                "status": order.status.value,
            }
        except APIError as e:
            logger.error("failed_to_close_position", symbol=symbol, error=str(e))
            raise BrokerError(f"Failed to close position: {str(e)}")


# Singleton instance
_broker_instance: Optional[AlpacaBroker] = None


def get_broker() -> AlpacaBroker:
    """
    Get singleton broker instance (reads credentials from settings).
    Used by the webhook endpoint and admin API.
    """
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = AlpacaBroker()  # falls back to settings when no args given
    return _broker_instance

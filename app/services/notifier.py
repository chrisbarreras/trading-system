"""
Notification service for trade alerts.
Currently supports console logging only.
"""
import structlog
from typing import Dict, Optional

logger = structlog.get_logger()


class NotificationService:
    """
    Service for sending trading notifications.
    Currently logs to console. Can be extended to support Telegram, email, etc.
    """

    def __init__(self):
        """Initialize notification service."""
        logger.info("notification_service_initialized")

    async def notify_trade_executed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float],
        order_id: str,
        strategy: str
    ):
        """
        Notify that a trade was successfully executed.

        Args:
            symbol: Stock symbol
            side: buy or sell
            quantity: Number of shares
            price: Filled price
            order_id: Broker order ID
            strategy: Strategy name
        """
        price_str = f"${price:.2f}" if price is not None else "PENDING"
        message = (
            f"✅ Trade Executed: {side.upper()} {int(quantity)} shares of {symbol} "
            f"at {price_str} (Order: {order_id}) [Strategy: {strategy}]"
        )
        logger.info(
            "trade_executed",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_id=order_id,
            strategy=strategy
        )
        # Print to console for visibility
        print(f"\n{message}\n")

    async def notify_trade_failed(
        self,
        symbol: str,
        side: str,
        reason: str,
        strategy: str
    ):
        """
        Notify that a trade failed.

        Args:
            symbol: Stock symbol
            side: buy or sell
            reason: Failure reason
            strategy: Strategy name
        """
        message = (
            f"❌ Trade Failed: {side.upper()} {symbol} - {reason} "
            f"[Strategy: {strategy}]"
        )
        logger.error(
            "trade_failed",
            symbol=symbol,
            side=side,
            reason=reason,
            strategy=strategy
        )
        # Print to console for visibility
        print(f"\n{message}\n")

    async def notify_signal_received(
        self,
        symbol: str,
        action: str,
        strategy: str
    ):
        """
        Notify that a signal was received.

        Args:
            symbol: Stock symbol
            action: buy or sell
            strategy: Strategy name
        """
        logger.info(
            "signal_received",
            symbol=symbol,
            action=action,
            strategy=strategy
        )

    async def notify_error(
        self,
        error_type: str,
        message: str,
        context: Optional[Dict] = None
    ):
        """
        Notify about a system error.

        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
        """
        logger.error(
            "system_error",
            error_type=error_type,
            message=message,
            context=context or {}
        )
        print(f"\n🚨 ERROR: {error_type} - {message}\n")


# Singleton instance
_notifier_instance: Optional[NotificationService] = None


def get_notifier() -> NotificationService:
    """
    Get singleton notifier instance.
    """
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = NotificationService()
    return _notifier_instance

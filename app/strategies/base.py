"""
Base strategy class that all trading strategies must inherit from.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Each strategy must implement the required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize strategy with configuration.

        Args:
            config: Strategy-specific configuration dict
        """
        self.config = config
        self.name = self.__class__.__name__
        logger.info("strategy_initialized", strategy=self.name)

    @abstractmethod
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate if the trading signal is well-formed and should be processed.

        Args:
            signal: Trading signal dict from webhook

        Returns:
            True if signal is valid, False otherwise
        """
        pass

    @abstractmethod
    def should_execute(self, signal: Dict[str, Any], account_info: Dict) -> bool:
        """
        Determine if trade should be executed based on strategy rules.

        Args:
            signal: Trading signal dict
            account_info: Current account information

        Returns:
            True if trade should be executed, False otherwise
        """
        pass

    @abstractmethod
    def calculate_position_size(
        self,
        signal: Dict[str, Any],
        account_info: Dict
    ) -> float:
        """
        Calculate the position size (number of shares/contracts).

        Args:
            signal: Trading signal dict
            account_info: Current account information

        Returns:
            Number of shares to trade
        """
        pass

    def prepare_order(
        self,
        signal: Dict[str, Any],
        account_info: Dict
    ) -> Dict[str, Any]:
        """
        Prepare the order for execution.
        Can be overridden for custom order types.

        Args:
            signal: Trading signal dict
            account_info: Current account information

        Returns:
            Dict with order details (symbol, side, quantity, order_type)
        """
        quantity = self.calculate_position_size(signal, account_info)
        return {
            "symbol": signal["ticker"],
            "side": signal["action"],
            "quantity": quantity,
            "order_type": "market",
            "strategy_name": self.name
        }

    def on_trade_executed(self, trade_result: Dict) -> None:
        """
        Hook called after trade is successfully executed.
        Can be used for logging, updating strategy state, etc.

        Args:
            trade_result: Result from broker order submission
        """
        logger.info(
            "trade_executed_callback",
            strategy=self.name,
            symbol=trade_result.get("symbol"),
            order_id=trade_result.get("order_id")
        )

    def on_trade_rejected(self, signal: Dict[str, Any], reason: str) -> None:
        """
        Hook called when trade is rejected.
        Can be used for logging, alerting, etc.

        Args:
            signal: Trading signal that was rejected
            reason: Reason for rejection
        """
        logger.warning(
            "trade_rejected_callback",
            strategy=self.name,
            symbol=signal.get("ticker"),
            reason=reason
        )

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get strategy metadata for display/logging.

        Returns:
            Dict with strategy information
        """
        return {
            "name": self.name,
            "config": self.config
        }

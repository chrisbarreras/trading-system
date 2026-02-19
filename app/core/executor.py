"""
Trade execution orchestration.
Coordinates signal validation, strategy execution, broker interaction, and persistence.
"""
from datetime import datetime
from typing import Dict, Optional
import structlog
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.broker import get_broker, BrokerError
from app.core.exceptions import ExecutionError, ValidationError, RiskLimitError
from app.core.validator import validate_symbol
from app.strategies.registry import StrategyRegistry
from app.models.trade import Trade, TradeStatus, TradeSide
from app.models.signal import Signal
from app.services.notifier import get_notifier

logger = structlog.get_logger()


class TradeExecutor:
    """
    Orchestrates trade execution from signal to completion.
    """

    def __init__(self):
        """Initialize trade executor."""
        self.settings = get_settings()
        self.broker = get_broker()
        self.notifier = get_notifier()
        logger.info("trade_executor_initialized")

    async def execute_signal(self, signal_dict: Dict, db: Session) -> Dict:
        """
        Execute a trading signal end-to-end.

        Args:
            signal_dict: Trading signal from webhook
            db: Database session

        Returns:
            Dict with execution result

        Raises:
            ExecutionError: If execution fails
        """
        symbol = signal_dict.get("ticker")
        action = signal_dict.get("action")
        strategy_name = signal_dict.get("strategy")

        logger.info(
            "executing_signal",
            symbol=symbol,
            action=action,
            strategy=strategy_name
        )

        # Notify signal received
        await self.notifier.notify_signal_received(symbol, action, strategy_name)

        try:
            # Validate symbol
            validate_symbol(symbol)

            # Load strategy
            strategy_config = {
                "max_positions": self.settings.max_positions,
                "position_size_pct": self.settings.position_size_pct,
                "max_position_size_usd": self.settings.max_position_size_usd,
                "min_buying_power": self.settings.min_buying_power,
                "min_trade_size_usd": self.settings.min_trade_size_usd,
                "position_sizing_mode": self.settings.position_sizing_mode,
                "buying_power_reserve_pct": self.settings.buying_power_reserve_pct
            }
            strategy = StrategyRegistry.get_strategy(strategy_name, strategy_config)

            # Validate signal with strategy
            if not strategy.validate_signal(signal_dict):
                raise ValidationError("Signal failed strategy validation")

            # Get account info
            account_info = self.broker.get_account()
            positions = self.broker.get_positions()
            account_info["open_positions"] = len(positions)

            # Check if we should execute
            if not strategy.should_execute(signal_dict, account_info):
                raise ValidationError("Strategy rejected trade execution")

            # Prepare order
            order_details = strategy.prepare_order(signal_dict, account_info)

            # Always fetch the live market price so we can enforce the position
            # limit in dollar terms regardless of what price the signal contained.
            # (Signal price drives share count; if it's wrong, actual spend can
            # far exceed MAX_POSITION_SIZE_USD without this check.)
            current_price = self.broker.get_current_price(order_details["symbol"])

            if current_price and order_details["quantity"] > 0:
                actual_cost = order_details["quantity"] * current_price
                if actual_cost > self.settings.max_position_size_usd:
                    adjusted_quantity = int(self.settings.max_position_size_usd / current_price)
                    logger.warning(
                        "position_size_adjusted_for_market_price",
                        symbol=order_details["symbol"],
                        original_quantity=order_details["quantity"],
                        adjusted_quantity=adjusted_quantity,
                        signal_price=signal_dict.get("price"),
                        market_price=current_price,
                        actual_cost=actual_cost,
                        max_position_usd=self.settings.max_position_size_usd,
                    )
                    order_details["quantity"] = adjusted_quantity

            if order_details["quantity"] <= 0:
                raise ValidationError("Position size is zero after market price validation")

            # Calculate limit price for extended hours trading
            limit_price = None
            if self.settings.extended_hours_enabled and current_price:
                buffer = 0.005  # 0.5% buffer
                if order_details["side"] == "buy":
                    limit_price = current_price * (1 + buffer)
                else:
                    limit_price = current_price * (1 - buffer)
                logger.info(
                    "extended_hours_limit_price",
                    symbol=order_details["symbol"],
                    current_price=current_price,
                    limit_price=round(limit_price, 2),
                    side=order_details["side"]
                )

            # Submit order to broker
            order_result = self.broker.submit_order(
                symbol=order_details["symbol"],
                side=order_details["side"],
                quantity=order_details["quantity"],
                order_type=order_details.get("order_type", "market"),
                limit_price=limit_price
            )

            # Save trade to database
            trade = Trade(
                symbol=symbol,
                side=TradeSide.BUY if action == "buy" else TradeSide.SELL,
                quantity=order_details["quantity"],
                price=order_result.get("filled_avg_price"),
                strategy_name=strategy_name,
                order_id=str(order_result["order_id"]),  # Convert UUID to string for SQLite
                status=TradeStatus.FILLED if order_result["status"] == "filled" else TradeStatus.PENDING,
                filled_at=datetime.utcnow() if order_result["status"] == "filled" else None
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)

            # Notify success
            await self.notifier.notify_trade_executed(
                symbol=symbol,
                side=action,
                quantity=order_details["quantity"],
                price=order_result.get("filled_avg_price"),
                order_id=str(order_result["order_id"]),
                strategy=strategy_name
            )

            # Call strategy hook
            strategy.on_trade_executed(order_result)

            logger.info(
                "trade_execution_successful",
                trade_id=trade.id,
                order_id=order_result["order_id"]
            )

            return {
                "success": True,
                "trade_id": trade.id,
                "order_id": order_result["order_id"],
                "message": "Trade executed successfully"
            }

        except (ValidationError, BrokerError, RiskLimitError) as e:
            error_message = str(e)
            logger.error(
                "trade_execution_failed",
                symbol=symbol,
                action=action,
                strategy=strategy_name,
                error=error_message
            )

            # Save failed trade to database
            trade = Trade(
                symbol=symbol,
                side=TradeSide.BUY if action == "buy" else TradeSide.SELL,
                quantity=0,
                price=None,
                strategy_name=strategy_name,
                order_id=None,
                status=TradeStatus.REJECTED,
                error_message=error_message
            )
            db.add(trade)
            db.commit()

            # Notify failure
            await self.notifier.notify_trade_failed(
                symbol=symbol,
                side=action,
                reason=error_message,
                strategy=strategy_name
            )

            return {
                "success": False,
                "error": error_message,
                "message": "Trade execution failed"
            }

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(
                "trade_execution_unexpected_error",
                symbol=symbol,
                action=action,
                error=error_message,
                exc_info=True
            )

            # Notify error
            await self.notifier.notify_error(
                error_type="execution_error",
                message=error_message,
                context=signal_dict
            )

            raise ExecutionError(error_message)


# Singleton instance
_executor_instance: Optional[TradeExecutor] = None


def get_executor() -> TradeExecutor:
    """
    Get singleton executor instance.
    """
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = TradeExecutor()
    return _executor_instance

"""
Example momentum trading strategy.
"""
from typing import Dict, Any
import structlog
from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry

logger = structlog.get_logger()


@StrategyRegistry.register("momentum")
class MomentumStrategy(BaseStrategy):
    """
    Simple momentum strategy that executes trades on TradingView signals.
    Uses fixed percentage position sizing.
    """

    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate that signal has required fields.

        Args:
            signal: Trading signal from webhook

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        required_fields = ["ticker", "action"]
        for field in required_fields:
            if field not in signal or not signal[field]:
                logger.warning(
                    "signal_validation_failed",
                    strategy=self.name,
                    missing_field=field
                )
                return False

        # Check action is valid
        if signal["action"] not in ["buy", "sell"]:
            logger.warning(
                "signal_validation_failed",
                strategy=self.name,
                invalid_action=signal["action"]
            )
            return False

        return True

    def should_execute(self, signal: Dict[str, Any], account_info: Dict) -> bool:
        """
        Determine if trade should be executed.
        Now uses soft buying power checks - positions are scaled instead of rejected.

        Args:
            signal: Trading signal
            account_info: Current account information

        Returns:
            True if trade should execute, False otherwise
        """
        buying_power = float(account_info.get("buying_power", 0))
        min_buying_power = self.config.get("min_buying_power", 100.0)

        # Only reject if critically low (below $100 default)
        if buying_power < min_buying_power:
            logger.warning(
                "critically_low_buying_power",
                strategy=self.name,
                buying_power=buying_power,
                min_required=min_buying_power
            )
            return False

        # For buy signals, check if we can afford at least minimum trade
        if signal["action"] == "buy":
            price = signal.get("price", 0)
            min_trade_size = self.config.get("min_trade_size_usd", 50.0)

            if price <= 0:
                logger.warning(
                    "invalid_price_in_signal",
                    strategy=self.name,
                    symbol=signal["ticker"]
                )
                return False

            # Can we afford at least 1 share AND meet minimum trade size?
            if buying_power < max(price, min_trade_size):
                logger.warning(
                    "insufficient_buying_power_for_trade",
                    strategy=self.name,
                    symbol=signal["ticker"],
                    buying_power=buying_power,
                    share_price=price,
                    min_trade_size=min_trade_size
                )
                return False

        # Keep existing max_positions check structure (currently commented)
        if signal["action"] == "buy":
            max_positions = self.config.get("max_positions", 5)
            # Future: Check actual position count

        return True

    def calculate_position_size(
        self,
        signal: Dict[str, Any],
        account_info: Dict
    ) -> float:
        """
        Calculate position size using adaptive buying-power-aware algorithm.

        Algorithm:
        1. Calculate portfolio-based target (e.g., 15% of portfolio)
        2. Calculate buying-power limit (available capital - reserve)
        3. Use minimum of both to ensure order can execute
        4. Apply min/max constraints

        Args:
            signal: Trading signal
            account_info: Current account information

        Returns:
            Number of shares to trade (0 if trade should be rejected)
        """
        # Extract account data
        portfolio_value = float(account_info.get("portfolio_value", 0))
        buying_power = float(account_info.get("buying_power", 0))

        # Get configuration
        position_pct = self.config.get("position_size_pct", 0.10)
        max_position_usd = self.config.get("max_position_size_usd", 10000)
        min_trade_size_usd = self.config.get("min_trade_size_usd", 50.0)
        reserve_pct = self.config.get("buying_power_reserve_pct", 0.05)
        sizing_mode = self.config.get("position_sizing_mode", "adaptive")

        # Validate price
        price = signal.get("price")
        if not price or price <= 0:
            logger.warning(
                "no_price_in_signal",
                strategy=self.name,
                symbol=signal["ticker"]
            )
            return 0

        # For sell signals, return 0 (placeholder for now)
        if signal["action"] == "sell":
            return 0  # Future: look up actual position quantity

        # Calculate portfolio-based target
        portfolio_target_usd = portfolio_value * position_pct

        # Calculate buying-power limit (keep reserve for fees)
        available_capital = buying_power * (1 - reserve_pct)

        # Adaptive mode: use minimum of both constraints
        if sizing_mode == "adaptive":
            target_value_usd = min(portfolio_target_usd, available_capital)

            # Log when buying power constrains position size
            if available_capital < portfolio_target_usd:
                reduction_pct = (portfolio_target_usd - target_value_usd) / portfolio_target_usd * 100
                logger.info(
                    "position_size_reduced_by_buying_power",
                    strategy=self.name,
                    symbol=signal["ticker"],
                    portfolio_target=portfolio_target_usd,
                    buying_power_limit=available_capital,
                    final_target=target_value_usd,
                    reduction_pct=round(reduction_pct, 1)
                )
        elif sizing_mode == "buying_power":
            target_value_usd = available_capital
        else:  # portfolio mode (old behavior)
            target_value_usd = portfolio_target_usd

        # Apply maximum position size constraint
        target_value_usd = min(target_value_usd, max_position_usd)

        # Calculate number of shares
        quantity = int(target_value_usd / price)

        # Check minimum trade size
        estimated_value = quantity * price
        if estimated_value < min_trade_size_usd:
            logger.warning(
                "trade_below_minimum_size",
                strategy=self.name,
                symbol=signal["ticker"],
                estimated_value=estimated_value,
                min_required=min_trade_size_usd
            )
            return 0

        # Ensure at least 1 share
        quantity = max(1, quantity)

        # Final safety check: can we actually afford this?
        final_cost = quantity * price
        if final_cost > buying_power:
            quantity = int(buying_power / price)
            logger.warning(
                "position_size_scaled_to_max_affordable",
                strategy=self.name,
                symbol=signal["ticker"],
                adjusted_quantity=quantity
            )

        logger.info(
            "position_size_calculated",
            strategy=self.name,
            symbol=signal["ticker"],
            quantity=quantity,
            price=price,
            estimated_value=quantity * price,
            buying_power=buying_power,
            portfolio_value=portfolio_value
        )

        return quantity

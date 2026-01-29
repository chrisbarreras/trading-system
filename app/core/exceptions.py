"""
Custom exception classes for the trading system.
"""


class TradingSystemError(Exception):
    """Base exception for all trading system errors."""
    pass


class ValidationError(TradingSystemError):
    """Raised when signal validation fails."""
    pass


class ExecutionError(TradingSystemError):
    """Raised when trade execution fails."""
    pass


class BrokerError(TradingSystemError):
    """Raised when broker API calls fail."""
    pass


class StrategyError(TradingSystemError):
    """Raised when strategy-related errors occur."""
    pass


class RiskLimitError(TradingSystemError):
    """Raised when risk limits are violated."""
    pass

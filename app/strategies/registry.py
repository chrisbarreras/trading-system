"""
Strategy registry for managing and loading strategies.
"""
from typing import Dict, Type, List
import structlog
from app.strategies.base import BaseStrategy

logger = structlog.get_logger()


class StrategyRegistry:
    """
    Registry for managing strategy instances.
    Maps strategy names from TradingView to strategy classes.
    """

    _strategies: Dict[str, Type[BaseStrategy]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a strategy.

        Usage:
            @StrategyRegistry.register("momentum")
            class MomentumStrategy(BaseStrategy):
                ...
        """
        def decorator(strategy_class: Type[BaseStrategy]):
            cls._strategies[name.lower()] = strategy_class
            logger.info("strategy_registered", name=name, class_name=strategy_class.__name__)
            return strategy_class
        return decorator

    @classmethod
    def get_strategy(cls, name: str, config: Dict) -> BaseStrategy:
        """
        Get a strategy instance by name.

        Args:
            name: Strategy name (from TradingView webhook)
            config: Configuration dict for the strategy

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy not found
        """
        strategy_class = cls._strategies.get(name.lower())
        if not strategy_class:
            available = cls.list_strategies()
            raise ValueError(
                f"Strategy '{name}' not found in registry. "
                f"Available strategies: {available}"
            )
        return strategy_class(config)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        List all registered strategies.

        Returns:
            List of strategy names
        """
        return list(cls._strategies.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a strategy is registered.

        Args:
            name: Strategy name

        Returns:
            True if registered, False otherwise
        """
        return name.lower() in cls._strategies

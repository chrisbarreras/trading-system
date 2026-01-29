"""
Configuration management using Pydantic Settings.
Loads settings from environment variables (.env files).
"""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Supports both paper trading and live trading modes.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Trading Mode
    trading_mode: Literal["paper", "live"] = "paper"

    # Alpaca API Credentials
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Database
    database_url: str = "sqlite:///./trading_paper.db"

    # TradingView Webhook Security
    tradingview_webhook_secret: str

    # Risk Management Parameters
    max_positions: int = 5
    position_size_pct: float = 0.10
    max_daily_trades: int = 20
    max_position_size_usd: float = 10000.0

    # Advanced Position Sizing
    min_buying_power: float = 100.0
    min_trade_size_usd: float = 50.0
    position_sizing_mode: Literal["portfolio", "buying_power", "adaptive"] = "adaptive"
    buying_power_reserve_pct: float = 0.05

    # Logging
    log_level: str = "INFO"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8080

    @property
    def is_paper_trading(self) -> bool:
        """Check if currently in paper trading mode."""
        return self.trading_mode == "paper"

    @property
    def is_live_trading(self) -> bool:
        """Check if currently in live trading mode."""
        return self.trading_mode == "live"

    def validate_live_trading(self) -> None:
        """
        Validate configuration for live trading.
        Raises ValueError if configuration is unsafe for live trading.
        """
        if self.trading_mode == "live":
            # Ensure we're not using paper trading URL in live mode
            if "paper" in self.alpaca_base_url.lower():
                raise ValueError(
                    "Live trading mode is enabled but using paper trading URL! "
                    "This could cause serious issues. "
                    "Check your ALPACA_BASE_URL environment variable."
                )

            # Ensure API keys are set
            if not self.alpaca_api_key or self.alpaca_api_key == "your_live_api_key_here":
                raise ValueError(
                    "Live trading mode requires valid Alpaca API keys. "
                    "Set ALPACA_API_KEY in your .env.live file."
                )

            # Warn about risk parameters
            if self.max_position_size_usd > 10000:
                print(
                    f"WARNING: Max position size is ${self.max_position_size_usd}. "
                    "This is quite high for live trading. Consider lowering it."
                )

            if self.position_size_pct > 0.10:
                print(
                    f"WARNING: Position size is {self.position_size_pct*100}% of portfolio. "
                    "This is quite high for live trading. Consider lowering it."
                )

    def validate_paper_trading(self) -> None:
        """
        Validate configuration for paper trading.
        Raises ValueError if configuration seems incorrect.
        """
        if self.trading_mode == "paper":
            # Ensure we're using paper trading URL
            if "paper" not in self.alpaca_base_url.lower():
                raise ValueError(
                    "Paper trading mode is enabled but not using paper trading URL! "
                    "Check your ALPACA_BASE_URL environment variable. "
                    "It should be https://paper-api.alpaca.markets"
                )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid re-reading .env file on every call.
    Call this function to access settings throughout the application.
    """
    settings = Settings()

    # Validate based on trading mode
    if settings.is_live_trading:
        settings.validate_live_trading()
    else:
        settings.validate_paper_trading()

    return settings

"""
Pydantic schemas for TradingView webhook payloads.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class TradingSignal(BaseModel):
    """
    Schema for TradingView webhook payload.
    """
    ticker: str = Field(..., description="Stock symbol (e.g., AAPL)")
    action: str = Field(..., description="Trade action: 'buy' or 'sell'")
    strategy: str = Field(..., description="Strategy name")
    price: Optional[float] = Field(None, description="Current price from TradingView")
    time: Optional[str] = Field(None, description="Timestamp from TradingView")

    @validator("action")
    def validate_action(cls, v):
        """Ensure action is buy or sell."""
        v = v.lower()
        if v not in ["buy", "sell"]:
            raise ValueError("action must be 'buy' or 'sell'")
        return v

    @validator("ticker")
    def validate_ticker(cls, v):
        """Ensure ticker is not empty and uppercase."""
        v = v.strip().upper()
        if not v:
            raise ValueError("ticker cannot be empty")
        return v

    @validator("strategy")
    def validate_strategy(cls, v):
        """Ensure strategy name is not empty."""
        v = v.strip().lower()
        if not v:
            raise ValueError("strategy cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "action": "buy",
                "strategy": "momentum",
                "price": 150.25,
                "time": "2024-01-01T10:00:00Z"
            }
        }


class WebhookResponse(BaseModel):
    """
    Response schema for webhook endpoint.
    """
    status: str = Field(..., description="Status of webhook processing")
    message: Optional[str] = Field(None, description="Additional message")
    signal_id: Optional[int] = Field(None, description="Database ID of the signal")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "received",
                "message": "Trade signal queued for execution",
                "signal_id": 123
            }
        }

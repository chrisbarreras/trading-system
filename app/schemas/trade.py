"""
Pydantic schemas for trade-related API responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TradeResponse(BaseModel):
    """
    Schema for trade information in API responses.
    """
    id: int
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    strategy_name: str
    order_id: Optional[str]
    status: str
    created_at: Optional[str]
    filled_at: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "symbol": "AAPL",
                "side": "buy",
                "quantity": 10.0,
                "price": 150.25,
                "strategy_name": "MomentumStrategy",
                "order_id": "abc123",
                "status": "filled",
                "created_at": "2024-01-01T10:00:00",
                "filled_at": "2024-01-01T10:00:05",
                "error_message": None
            }
        }


class AccountResponse(BaseModel):
    """
    Schema for account information in API responses.
    """
    account_number: str
    buying_power: float
    cash: float
    portfolio_value: float
    equity: float
    status: str
    currency: str
    pattern_day_trader: bool

    class Config:
        json_schema_extra = {
            "example": {
                "account_number": "ABC123",
                "buying_power": 50000.0,
                "cash": 25000.0,
                "portfolio_value": 100000.0,
                "equity": 100000.0,
                "status": "ACTIVE",
                "currency": "USD",
                "pattern_day_trader": False
            }
        }

"""
Database models for trades.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
import enum
from app.models.base import Base


class TradeStatus(enum.Enum):
    """Trade status enumeration."""
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELED = "canceled"


class TradeSide(enum.Enum):
    """Trade side enumeration."""
    BUY = "buy"
    SELL = "sell"


class Trade(Base):
    """
    Trade model representing an executed or attempted trade.
    Stores all relevant information for audit and analysis.
    """
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)

    # Trade Details
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(SQLEnum(TradeSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Filled price (null if rejected)

    # Strategy Info
    strategy_name = Column(String(50), nullable=False, index=True)

    # Broker Info
    order_id = Column(String(50), nullable=True, index=True)  # Alpaca order ID
    status = Column(SQLEnum(TradeStatus), nullable=False, default=TradeStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    filled_at = Column(DateTime, nullable=True)

    # Error Info (if rejected)
    error_message = Column(String(500), nullable=True)

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side.value}, "
            f"quantity={self.quantity}, status={self.status.value}, "
            f"strategy={self.strategy_name})>"
        )

    def to_dict(self):
        """Convert trade to dictionary for API responses."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "strategy_name": self.strategy_name,
            "order_id": self.order_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "error_message": self.error_message
        }

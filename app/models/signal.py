"""
Database models for trading signals (webhook payloads).
Stores raw webhook data for audit trail.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.models.base import Base


class Signal(Base):
    """
    Signal model representing a raw webhook payload from TradingView.
    Stores the complete payload for audit and debugging purposes.
    """
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)

    # Signal Details
    ticker = Column(String(10), nullable=False, index=True)
    action = Column(String(10), nullable=False)  # buy/sell
    strategy = Column(String(50), nullable=False, index=True)

    # Raw Payload
    raw_payload = Column(Text, nullable=False)  # JSON string of full webhook payload

    # Metadata
    source_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    processed = Column(Integer, default=0, nullable=False)  # 0 = pending, 1 = processed, 2 = failed

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Processing Result
    trade_id = Column(Integer, nullable=True)  # FK to trades table (if processed successfully)
    error_message = Column(String(500), nullable=True)

    def __repr__(self):
        return (
            f"<Signal(id={self.id}, ticker={self.ticker}, action={self.action}, "
            f"strategy={self.strategy}, processed={self.processed})>"
        )

    def to_dict(self):
        """Convert signal to dictionary for API responses."""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "action": self.action,
            "strategy": self.strategy,
            "processed": bool(self.processed),
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "trade_id": self.trade_id,
            "error_message": self.error_message
        }

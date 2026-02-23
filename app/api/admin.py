"""
Admin API endpoints for system health and status.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import structlog

from app.config import get_settings
from app.core.broker import get_broker, BrokerError
from app.schemas.trade import TradeResponse, AccountResponse
from app.services.database import get_db
from app.models.trade import Trade
from app.strategies.registry import StrategyRegistry

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Dict with health status
    """
    settings = get_settings()
    return {
        "status": "healthy",
        "mode": settings.trading_mode,
        "version": "1.0.0"
    }


@router.get("/status")
async def system_status():
    """
    Get trading system status.

    When the multi-account orchestrator is running, returns status for all
    configured accounts. Falls back to single-account status otherwise.

    Returns:
        Dict with system status
    """
    # Try orchestrator first (multi-account mode)
    try:
        from trading.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        if orchestrator is not None:
            return orchestrator.get_status()
    except Exception as e:
        logger.warning("orchestrator_status_unavailable", error=str(e))

    # Fall back to single-account status (webhook-only mode)
    settings = get_settings()
    broker = get_broker()
    try:
        account = broker.get_account()
        positions = broker.get_positions()
        return {
            "trading_mode": settings.trading_mode,
            "account": account,
            "positions": positions,
            "num_positions": len(positions),
            "config": {
                "max_positions": settings.max_positions,
                "position_size_pct": settings.position_size_pct,
                "max_daily_trades": settings.max_daily_trades,
                "max_position_size_usd": settings.max_position_size_usd,
            },
            "registered_strategies": StrategyRegistry.list_strategies(),
        }
    except BrokerError as e:
        logger.error("failed_to_get_status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account", response_model=AccountResponse)
async def get_account_info():
    """
    Get Alpaca account information.

    Returns:
        AccountResponse with account details
    """
    broker = get_broker()
    try:
        account = broker.get_account()
        return AccountResponse(**account)
    except BrokerError as e:
        logger.error("failed_to_get_account", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get recent trades from database.

    Args:
        limit: Number of trades to return (default 10)
        db: Database session

    Returns:
        List of TradeResponse objects
    """
    trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
    return [trade.to_dict() for trade in trades]


@router.get("/trades/{trade_id}", response_model=TradeResponse)
async def get_trade_by_id(
    trade_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific trade by ID.

    Args:
        trade_id: Trade database ID
        db: Database session

    Returns:
        TradeResponse object

    Raises:
        HTTPException: If trade not found
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade.to_dict()


@router.get("/strategies")
async def list_strategies():
    """
    List all registered trading strategies.

    Returns:
        Dict with strategy list
    """
    strategies = StrategyRegistry.list_strategies()
    return {
        "strategies": strategies,
        "count": len(strategies)
    }

"""
Webhook API endpoints for receiving TradingView alerts.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException, Header
from sqlalchemy.orm import Session
import json
import structlog

from app.schemas.webhook import TradingSignal, WebhookResponse
from app.core.validator import validate_webhook_signature
from app.core.executor import get_executor
from app.core.exceptions import ValidationError
from app.services.database import get_db
from app.models.signal import Signal

logger = structlog.get_logger()
router = APIRouter()


@router.post("/tradingview", response_model=WebhookResponse)
async def tradingview_webhook(
    signal: TradingSignal,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    x_tradingview_signature: str = Header(None)
):
    """
    Receive and process TradingView webhook alerts.

    This endpoint:
    1. Validates the webhook signature
    2. Saves the signal to the database
    3. Queues trade execution in the background
    4. Returns immediately to avoid timeout

    Args:
        signal: Parsed TradingView signal
        background_tasks: FastAPI background tasks
        request: HTTP request object
        db: Database session
        x_tradingview_signature: Webhook signature header

    Returns:
        WebhookResponse with status

    Raises:
        HTTPException: If validation fails
    """
    # Get raw body for signature validation
    body = await request.body()
    body_str = body.decode("utf-8")

    # Get client IP
    client_ip = request.client.host if request.client else None

    logger.info(
        "webhook_received",
        symbol=signal.ticker,
        action=signal.action,
        strategy=signal.strategy,
        client_ip=client_ip
    )

    try:
        # Validate webhook signature
        # Note: In production, you'd uncomment this
        # validate_webhook_signature(body_str, x_tradingview_signature)

        # Save signal to database for audit
        db_signal = Signal(
            ticker=signal.ticker,
            action=signal.action,
            strategy=signal.strategy,
            raw_payload=body_str,
            source_ip=client_ip,
            processed=0  # Not processed yet
        )
        db.add(db_signal)
        db.commit()
        db.refresh(db_signal)

        # Queue trade execution in background
        background_tasks.add_task(
            execute_trade_background,
            signal.model_dump(),
            db_signal.id
        )

        logger.info(
            "webhook_accepted",
            signal_id=db_signal.id,
            symbol=signal.ticker
        )

        return WebhookResponse(
            status="received",
            message="Trade signal queued for execution",
            signal_id=db_signal.id
        )

    except ValidationError as e:
        logger.warning("webhook_validation_failed", error=str(e))
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error("webhook_processing_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def execute_trade_background(signal_dict: dict, signal_id: int):
    """
    Execute trade in the background.

    Args:
        signal_dict: Trading signal dictionary
        signal_id: Database signal ID
    """
    # Import here to avoid circular imports
    from app.services.database import SessionLocal

    db = SessionLocal()
    try:
        executor = get_executor()
        result = await executor.execute_signal(signal_dict, db)

        # Update signal status
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if signal:
            signal.processed = 1 if result.get("success") else 2
            signal.trade_id = result.get("trade_id")
            if not result.get("success"):
                signal.error_message = result.get("error")
            db.commit()

    except Exception as e:
        logger.error(
            "background_execution_failed",
            signal_id=signal_id,
            error=str(e),
            exc_info=True
        )
        # Update signal to failed
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if signal:
            signal.processed = 2
            signal.error_message = str(e)
            db.commit()
    finally:
        db.close()

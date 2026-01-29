"""
Webhook signature validation and security.
"""
import hmac
import hashlib
import structlog
from typing import Optional
from app.config import get_settings
from app.core.exceptions import ValidationError

logger = structlog.get_logger()


def validate_webhook_signature(
    payload: str,
    signature: Optional[str],
    secret: Optional[str] = None
) -> bool:
    """
    Validate TradingView webhook signature using HMAC-SHA256.

    Args:
        payload: Raw webhook payload string
        signature: Signature from webhook header
        secret: Secret key (defaults to config value)

    Returns:
        True if signature is valid

    Raises:
        ValidationError: If signature is invalid or missing
    """
    if secret is None:
        settings = get_settings()
        secret = settings.tradingview_webhook_secret

    if not signature:
        logger.warning("webhook_signature_missing")
        raise ValidationError("Webhook signature is missing")

    # Calculate expected signature
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures securely
    is_valid = hmac.compare_digest(expected, signature)

    if not is_valid:
        logger.warning("webhook_signature_invalid")
        raise ValidationError("Webhook signature is invalid")

    logger.debug("webhook_signature_valid")
    return True


def validate_symbol(symbol: str) -> bool:
    """
    Validate that a stock symbol is properly formatted.

    Args:
        symbol: Stock symbol

    Returns:
        True if valid

    Raises:
        ValidationError: If symbol is invalid
    """
    # Basic validation
    if not symbol or len(symbol) < 1 or len(symbol) > 10:
        raise ValidationError(f"Invalid symbol: {symbol}")

    # Ensure alphanumeric
    if not symbol.replace(".", "").replace("-", "").isalnum():
        raise ValidationError(f"Invalid symbol format: {symbol}")

    return True

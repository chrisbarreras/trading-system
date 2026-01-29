"""
Main FastAPI application for the trading system.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import get_settings
from app.utils.logger import configure_logging
from app.services.database import init_db
from app.api import webhooks, admin

# Import strategies to register them
from app.strategies import momentum  # noqa: F401

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    settings = get_settings()

    # Configure logging
    configure_logging()

    logger.info(
        "trading_system_starting",
        mode=settings.trading_mode,
        version="1.0.0"
    )

    # Initialize database
    init_db()
    logger.info("database_initialized")

    # Log configuration
    logger.info(
        "configuration_loaded",
        trading_mode=settings.trading_mode,
        max_positions=settings.max_positions,
        position_size_pct=settings.position_size_pct,
        max_daily_trades=settings.max_daily_trades
    )

    # Yield control to the application
    yield

    # Shutdown
    logger.info("trading_system_shutting_down")


# Create FastAPI app
app = FastAPI(
    title="Automated Trading System",
    description="Receives TradingView alerts and executes trades via Alpaca API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhooks.router, prefix="/webhook", tags=["Webhooks"])
app.include_router(admin.router, prefix="", tags=["Admin"])


@app.get("/")
async def root():
    """
    Root endpoint.
    """
    settings = get_settings()
    return {
        "name": "Automated Trading System",
        "version": "1.0.0",
        "mode": settings.trading_mode,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "webhook": "/webhook/tradingview",
            "trades": "/trades",
            "strategies": "/strategies"
        }
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

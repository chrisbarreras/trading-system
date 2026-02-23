"""
Single-process entry point for the trading system.

Starts the FastAPI server in a background daemon thread (for /health and admin
endpoints) and runs the multi-account orchestrator in the main thread.

Usage:
    python run_trading.py [--config accounts.yaml]
"""
import argparse
import threading
import structlog

from app.utils.logger import configure_logging

logger = structlog.get_logger()


def start_api_server(host: str = "0.0.0.0", port: int = 8080) -> threading.Thread:
    """Start the FastAPI server in a daemon thread."""
    import uvicorn

    thread = threading.Thread(
        target=uvicorn.run,
        kwargs={
            "app": "app.main:app",
            "host": host,
            "port": port,
            "log_level": "warning",  # suppress uvicorn access logs; structlog handles app logs
        },
        daemon=True,  # exits when the main thread exits
        name="api-server",
    )
    thread.start()
    logger.info("api_server_started", host=host, port=port)
    return thread


def main():
    parser = argparse.ArgumentParser(description="Multi-account trading system")
    parser.add_argument(
        "--config",
        default="accounts.yaml",
        help="Path to accounts config file (default: accounts.yaml)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="API server port (default: 8080)",
    )
    args = parser.parse_args()

    configure_logging()

    # Import here so logging is configured first
    from trading.orchestrator import Orchestrator, set_orchestrator

    logger.info("trading_system_starting", config=args.config)

    orchestrator = Orchestrator(args.config)
    set_orchestrator(orchestrator)

    # Start FastAPI in background thread
    start_api_server(host=args.host, port=args.port)

    # Run orchestrator in main thread (blocks until Ctrl+C)
    orchestrator.run()

    logger.info("trading_system_stopped")


if __name__ == "__main__":
    main()

# Copilot / Agent Instructions for this repo

Purpose: help an AI coding agent get productive quickly by documenting the repo's architecture, conventions, and common developer workflows with concrete file references and examples.

## Big picture (what to know first)
- Two main components:
  - `app/` — FastAPI service that receives TradingView-like webhooks and executes trades via Alpaca. Key entrypoint: `app.main` (lifespan hooks initialize logging and DB). See `app/api/webhooks.py` for the public webhook contract.
  - `scanner/` — Market scanner and strategy implementations that generate signals and POST them to the trading service (`/webhook/tradingview`). See `scanner/scanner.py` and `scanner/strategies.py`.
- Trading flow: scanner -> POST webhook -> `webhook/tradingview` -> persisted `Signal` -> background task -> `TradeExecutor` -> `Broker` -> save `Trade`.
- State and audit: signals/trades are stored in SQLite by default (`app/services/database.py` + models in `app/models/`). Alembic exists for migrations (`alembic/`).

## Key files to reference (always open these first)
- `app/main.py` — app lifecycle, logging init, DB init (calls `init_db()`)
- `app/config.py` — pydantic settings (.env support), safety checks for `live` mode
- `app/api/webhooks.py` — webhook schema and processing pipeline
- `app/core/executor.py` — central execution logic (strategy → broker → DB → notifications)
- `app/core/broker.py` — Alpaca API wrapper; raise `BrokerError` on failures
- `app/strategies/*` — strategy interface and implementations; register via `StrategyRegistry`
- `app/services/database.py` — engine/session helpers and `init_db()`
- `scanner/` — scanner CLI and strategy implementations that POST payloads
- `README.md` — operational commands (start scripts, .env, scanning patterns)

## Conventions & patterns agents must follow
- Strategy pattern: strategies are registered with the decorator `@StrategyRegistry.register("name")` and must implement methods used by `TradeExecutor`:
  - `validate_signal(signal: Dict) -> bool`
  - `should_execute(signal: Dict, account_info: Dict) -> bool`
  - `prepare_order(...)` / `calculate_position_size(...)` (see `app/strategies/momentum.py` for an example)
  - Optional hook: `on_trade_executed(order_result)`
- Singletons accessed via `get_*()` functions: `get_broker()`, `get_executor()`, `get_notifier()` — reuse these instead of instantiating directly.
- Background execution: webhook handler adds a FastAPI `BackgroundTask` that calls `execute_trade_background` (see `app/api/webhooks.py`). Always ensure DB sessions used in background tasks use `SessionLocal()` from `app.services.database` and are closed after use.
- Logging: structured logging via `structlog`. Initialize with `app.utils.logger.configure_logging()` (called in startup lifecycle).
- Webhook security: HMAC signature validation helper `validate_webhook_signature(payload, signature)` is provided in `app/core/validator.py`. Note: signature validation is currently commented out in the webhook handler for easier local testing; don't remove it for production.
- Settings & safety: `app/config.py` enforces live/trading safety checks — any agent changes touching runtime config should preserve these checks.
- DB access: use the `get_db()` dependency in endpoints; for ad-hoc or background tasks use `SessionLocal` and always `close()` sessions.

## Developer workflows & commands
- Setup:
  - pip install -r requirements.txt (and `scanner_requirements.txt` for scanner-specific deps)
  - Create `.env` with Alpaca keys and `TRADINGVIEW_WEBHOOK_SECRET` (see `README.md`)
- Run service locally (dev):
  - `python -m uvicorn app.main:app --host 0.0.0.0 --port 8080` (or use `start_all.bat`)
- Run scanner (dry-run):
  - `python run_scanner.py --dry-run --strategy rsi` — scanner prints signals without posting
- Run scanner (live to service):
  - `python run_scanner.py --schedule --strategy rsi` or use provided batch files
- Tests & quick checks:
  - `python test_scanner.py` — manual scanner checks (prints diagnostic output)
  - `pytest` — run unit tests (repo has a minimal `tests/` tree; prefer adding focused tests for new code)
- DB management:
  - `python reset_database.py` to clear data
  - Use `alembic/` for schema migrations in production

## Integration points & external dependencies
- Alpaca trading API (via `alpaca-py`) — use `app/core/broker.py` wrapper; errors become `BrokerError`.
- Yahoo Finance (scanner data source) — used by `scanner.data_source.YahooFinanceSource`.
- Webhooks: POST JSON with fields: `ticker`, `action` (`buy`/`sell`), `strategy`, `price` to `/webhook/tradingview`. Header `x-tradingview-signature` expected for HMAC validation if enabled.

## Error handling & tests to add
- The system uses domain-specific exceptions (`app/core/exceptions.py`). Prefer raising these over generic exceptions for clarity (ValidationError, BrokerError, RiskLimitError).
- Add unit tests for:
  - Strategy `validate_signal` and `should_execute` logic (example: `app/strategies/momentum.py`)
  - `TradeExecutor.execute_signal` edge cases (insufficient buying power, broker failures)
  - Webhook signature validation (valid & invalid)

## Example edits an agent might be asked to perform
- Register a new strategy: add a class in `app/strategies/` and decorate with `@StrategyRegistry.register("mystrategy")`. Implement the 3 core methods (`validate_signal`, `should_execute`, `calculate_position_size`/`prepare_order`). See `momentum.py` for a template.
- Add an endpoint: follow `app/api/admin.py` patterns (use Pydantic response models in `app/schemas/*` and `get_db()` dependency for DB access).
- Integrate a new notifier (Telegram/Slack): implement same `NotificationService` async methods and return via `get_notifier()` singleton.

---
If anything here is unclear, point to the exact file or workflow you want more details on and I'll expand this document with short code examples or tests. Thank you!
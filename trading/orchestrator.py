"""
Orchestrator: single-process manager for all AccountRunners.
Uses the schedule library to run swing accounts daily and day accounts every 15 minutes.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import schedule
import structlog

from trading.config_loader import load_accounts_config, SystemConfig
from trading.account_runner import AccountRunner

logger = structlog.get_logger()

ET = ZoneInfo("America/New_York")

# Module-level singleton for access from the admin API
_orchestrator_instance: Optional["Orchestrator"] = None


def set_orchestrator(instance: "Orchestrator") -> None:
    global _orchestrator_instance
    _orchestrator_instance = instance


def get_orchestrator() -> Optional["Orchestrator"]:
    return _orchestrator_instance


def is_market_hours() -> bool:
    """
    Return True if current ET time is within regular market hours on a weekday.
    9:30 AM – 4:00 PM ET, Monday–Friday.
    """
    now = datetime.now(ET)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    hour, minute = now.hour, now.minute
    if hour == 9:
        return minute >= 30
    return 10 <= hour < 16


class Orchestrator:
    """
    Manages multiple AccountRunners, each on its own schedule.

    - Swing accounts: scan once per trading day at 09:35 ET.
    - Day accounts: scan every 15 minutes during market hours;
                    close all positions at 15:55 ET.
    """

    def __init__(self, config_path: str = "accounts.yaml"):
        self.config: SystemConfig = load_accounts_config(config_path)
        self.symbols = self._load_symbols()
        self.runners: Dict[str, AccountRunner] = {}
        self._build_runners()

        logger.info(
            "orchestrator_initialized",
            accounts=len(self.runners),
            symbols=len(self.symbols),
        )

    def _load_symbols(self) -> list:
        path = Path(self.config.symbols_file)
        if not path.exists():
            logger.warning(
                "symbols_file_not_found",
                path=str(path),
                fallback="using empty list",
            )
            return []
        with open(path, "r") as f:
            symbols = [line.strip() for line in f if line.strip()]
        logger.info("symbols_loaded", count=len(symbols), file=str(path))
        return symbols

    def _build_runners(self) -> None:
        for acc in self.config.accounts:
            try:
                self.runners[acc.id] = AccountRunner(acc, self.symbols)
                logger.info(
                    "account_runner_created",
                    account=acc.id,
                    strategy=acc.strategy_name,
                    type=acc.type,
                )
            except Exception as e:
                logger.error("account_runner_failed", account=acc.id, error=str(e))

    def _safe_scan(self, runner: AccountRunner) -> None:
        """Run a scan cycle, isolating failures to the individual account."""
        if not is_market_hours():
            logger.debug("market_closed_skipping_scan", account=runner.config.id)
            return
        try:
            runner.run_scan_cycle()
        except Exception as e:
            logger.error(
                "scan_cycle_error",
                account=runner.config.id,
                error=str(e),
                exc_info=True,
            )

    def _close_day_positions(self) -> None:
        """EOD close for all day-trading accounts."""
        now = datetime.now(ET)
        if now.weekday() >= 5:
            return
        for runner in self.runners.values():
            if runner.config.type == "day":
                try:
                    runner.close_all_positions()
                except Exception as e:
                    logger.error(
                        "eod_close_error",
                        account=runner.config.id,
                        error=str(e),
                        exc_info=True,
                    )

    def schedule_jobs(self) -> None:
        for runner in self.runners.values():
            if runner.config.type == "day":
                schedule.every(15).minutes.do(self._safe_scan, runner)
            else:
                schedule.every().day.at("09:35").do(self._safe_scan, runner)

        schedule.every().day.at("15:55").do(self._close_day_positions)

        logger.info("jobs_scheduled", total_runners=len(self.runners))

    def run(self) -> None:
        """Block and run all scheduled jobs. Catches KeyboardInterrupt cleanly."""
        self.schedule_jobs()

        # Run an immediate scan for all accounts on startup
        for runner in self.runners.values():
            self._safe_scan(runner)

        logger.info("orchestrator_running")
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            logger.info("orchestrator_stopped")

    def get_status(self) -> dict:
        """Aggregate status across all accounts for the admin /status endpoint."""
        return {
            "orchestrator": "running",
            "account_count": len(self.runners),
            "symbol_count": len(self.symbols),
            "accounts": [runner.get_status() for runner in self.runners.values()],
        }

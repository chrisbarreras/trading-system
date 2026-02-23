"""
Loads and parses accounts.yaml into typed dataclasses.
Resolves ${ENV_VAR} references from the environment.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import yaml

ENV_VAR_PATTERN = re.compile(r'^\$\{(.+)\}$')


def _resolve(value: str) -> str:
    """Resolve ${VAR_NAME} to the corresponding environment variable."""
    match = ENV_VAR_PATTERN.match(str(value))
    if match:
        var_name = match.group(1)
        resolved = os.environ.get(var_name)
        if resolved is None:
            raise ValueError(
                f"Environment variable '{var_name}' referenced in accounts.yaml is not set"
            )
        return resolved
    return value


@dataclass
class RiskConfig:
    position_size_pct: float = 0.10
    max_positions: int = 5
    max_position_size_usd: float = 10000.0
    min_buying_power: float = 100.0
    min_trade_size_usd: float = 50.0
    buying_power_reserve_pct: float = 0.05


@dataclass
class AccountConfig:
    id: str
    name: str
    type: str                  # "swing" | "day"
    alpaca_api_key: str
    alpaca_secret_key: str
    strategy_name: str         # "rsi" | "macd" | "ma_cross" | "bb" | "combo"
    strategy_params: dict = field(default_factory=dict)
    risk: RiskConfig = field(default_factory=RiskConfig)


@dataclass
class SystemConfig:
    symbols_file: str
    accounts: List[AccountConfig]
    backtest_accounts: List[AccountConfig]


def _parse_account_list(raw_list: list) -> List[AccountConfig]:
    result = []
    for acc in raw_list:
        risk_raw = acc.get("risk", {})
        result.append(AccountConfig(
            id=acc["id"],
            name=acc.get("name", acc["id"]),
            type=acc["type"],
            alpaca_api_key=_resolve(acc["alpaca_api_key"]),
            alpaca_secret_key=_resolve(acc["alpaca_secret_key"]),
            strategy_name=acc["strategy"],
            strategy_params=acc.get("strategy_params", {}) or {},
            risk=RiskConfig(**risk_raw) if risk_raw else RiskConfig(),
        ))
    return result


def load_accounts_config(path: str = "accounts.yaml") -> SystemConfig:
    """
    Parse accounts.yaml and return a SystemConfig.

    Args:
        path: Path to accounts.yaml file.

    Returns:
        SystemConfig with resolved credentials.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If a referenced environment variable is not set.
    """
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    return SystemConfig(
        symbols_file=raw.get("symbols_file", "stock_symbols_top500.txt"),
        accounts=_parse_account_list(raw.get("accounts", [])),
        backtest_accounts=_parse_account_list(raw.get("backtest_accounts", [])),
    )

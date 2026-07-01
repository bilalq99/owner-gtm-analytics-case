"""Configuration loading and validation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PairConfig:
    base_mint: str
    base_symbol: str
    base_decimals: int
    quote_mint: str
    quote_symbol: str
    quote_decimals: int


@dataclass
class EngineConfig:
    poll_seconds: int
    price_probe_sol: float
    state_dir: str


@dataclass
class RiskConfig:
    starting_sol: float
    max_position_sol: float
    per_trade_sol: float
    max_total_invested_sol: float
    max_daily_spend_sol: float
    daily_loss_limit_sol: float
    max_slippage_bps: int
    min_seconds_between_trades: int
    kill_switch_file: str


@dataclass
class StrategyConfig:
    name: str
    fast_window: int
    slow_window: int
    rsi_window: int
    rsi_overbought: float
    rsi_oversold: float
    take_profit_pct: float
    stop_loss_pct: float
    dca_interval_minutes: int


@dataclass
class Secrets:
    """Loaded from environment, never from the config file or logs."""
    keypair_path: str | None = None
    private_key_base58: str | None = None
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    jupiter_base_url: str = "https://quote-api.jup.ag/v6"


@dataclass
class Config:
    pair: PairConfig
    engine: EngineConfig
    risk: RiskConfig
    strategy: StrategyConfig
    secrets: Secrets = field(default_factory=Secrets)

    def validate(self) -> None:
        r = self.risk
        if r.per_trade_sol <= 0:
            raise ValueError("risk.per_trade_sol must be > 0")
        if r.per_trade_sol > r.max_position_sol:
            raise ValueError("risk.per_trade_sol cannot exceed risk.max_position_sol")
        if r.max_position_sol > r.max_total_invested_sol:
            raise ValueError("risk.max_position_sol cannot exceed risk.max_total_invested_sol")
        if not 1 <= r.max_slippage_bps <= 5000:
            raise ValueError("risk.max_slippage_bps must be between 1 and 5000 (50%)")
        if self.engine.poll_seconds < 1:
            raise ValueError("engine.poll_seconds must be >= 1")
        s = self.strategy
        if s.name not in ("momentum", "dca"):
            raise ValueError(f"unknown strategy '{s.name}'")
        if s.fast_window >= s.slow_window:
            raise ValueError("strategy.fast_window must be < slow_window")
        if self.engine.price_probe_sol <= 0:
            raise ValueError("engine.price_probe_sol must be > 0")


def _load_secrets() -> Secrets:
    return Secrets(
        keypair_path=os.environ.get("SOLANA_KEYPAIR_PATH") or None,
        private_key_base58=os.environ.get("SOLANA_PRIVATE_KEY_BASE58") or None,
        rpc_url=os.environ.get("SOLANA_RPC_URL") or "https://api.mainnet-beta.solana.com",
        jupiter_base_url=os.environ.get("JUPITER_BASE_URL") or "https://quote-api.jup.ag/v6",
    )


def _maybe_load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader so we don't add a dependency. Does not overwrite real env vars."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def load_config(path: str) -> Config:
    _maybe_load_dotenv()
    raw: dict[str, Any] = yaml.safe_load(Path(path).read_text())
    cfg = Config(
        pair=PairConfig(**raw["pair"]),
        engine=EngineConfig(**raw["engine"]),
        risk=RiskConfig(**raw["risk"]),
        strategy=StrategyConfig(**raw["strategy"]),
        secrets=_load_secrets(),
    )
    cfg.validate()
    return cfg

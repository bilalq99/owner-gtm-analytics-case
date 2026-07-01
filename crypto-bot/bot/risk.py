"""Risk manager: hard caps and circuit breakers. The bot CANNOT trade past these."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .config import RiskConfig
from .portfolio import Portfolio


@dataclass
class Decision:
    approved: bool
    reason: str


def _utc_day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


class RiskManager:
    """Enforces position/spend/loss caps, a cooldown, slippage, and a kill switch.

    Daily counters reset at UTC midnight. State persists so caps survive restarts.
    """

    def __init__(self, cfg: RiskConfig, state_dir: str, kill_switch_dir: str = ".") -> None:
        self.cfg = cfg
        self.state_path = Path(state_dir) / "risk_state.json"
        self.kill_switch_path = Path(kill_switch_dir) / cfg.kill_switch_file
        self.day = ""
        self.spent_today_sol = 0.0
        self.day_start_equity_sol = 0.0
        self._load()

    # ---------- persistence ----------
    def _load(self) -> None:
        if self.state_path.exists():
            d = json.loads(self.state_path.read_text())
            self.day = d.get("day", "")
            self.spent_today_sol = d.get("spent_today_sol", 0.0)
            self.day_start_equity_sol = d.get("day_start_equity_sol", 0.0)

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({
            "day": self.day,
            "spent_today_sol": self.spent_today_sol,
            "day_start_equity_sol": self.day_start_equity_sol,
        }, indent=2))

    # ---------- per-cycle bookkeeping ----------
    def roll_day(self, now_ts: float, equity_sol: float) -> None:
        today = _utc_day(now_ts)
        if today != self.day:
            self.day = today
            self.spent_today_sol = 0.0
            self.day_start_equity_sol = equity_sol
            self._save()

    def daily_loss_sol(self, equity_sol: float) -> float:
        if self.day_start_equity_sol <= 0:
            return 0.0
        return self.day_start_equity_sol - equity_sol

    # ---------- gates ----------
    def kill_switch_engaged(self) -> bool:
        return self.kill_switch_path.exists()

    def _cooldown_ok(self, pf: Portfolio, now_ts: float) -> bool:
        if not pf.trades:
            return True
        return (now_ts - pf.trades[-1].ts) >= self.cfg.min_seconds_between_trades

    def check_slippage(self, realized_slippage_bps: float) -> Decision:
        if realized_slippage_bps > self.cfg.max_slippage_bps:
            return Decision(False, f"slippage {realized_slippage_bps:.0f}bps > cap {self.cfg.max_slippage_bps}bps")
        return Decision(True, "ok")

    def check_buy(self, pf: Portfolio, price_sol: float, now_ts: float, equity_sol: float) -> Decision:
        c = self.cfg
        if self.kill_switch_engaged():
            return Decision(False, f"KILL SWITCH active ({self.kill_switch_path})")
        if self.daily_loss_sol(equity_sol) >= c.daily_loss_limit_sol:
            return Decision(False, f"daily loss limit reached ({self.daily_loss_sol(equity_sol):.4f} SOL)")
        if not self._cooldown_ok(pf, now_ts):
            return Decision(False, "cooldown: too soon since last trade")
        size = c.per_trade_sol
        if pf.sol_balance < size:
            return Decision(False, f"insufficient SOL ({pf.sol_balance:.4f} < {size:.4f})")
        if pf.position_value_sol(price_sol) + size > c.max_position_sol + 1e-9:
            return Decision(False, f"would exceed max position ({c.max_position_sol} SOL)")
        if pf.total_invested_sol() + size > c.max_total_invested_sol + 1e-9:
            return Decision(False, f"would exceed lifetime invested cap ({c.max_total_invested_sol} SOL)")
        if self.spent_today_sol + size > c.max_daily_spend_sol + 1e-9:
            return Decision(False, f"would exceed daily spend cap ({c.max_daily_spend_sol} SOL)")
        return Decision(True, "ok")

    def check_sell(self, pf: Portfolio, now_ts: float) -> Decision:
        if self.kill_switch_engaged():
            # Protective sells (stop-loss) should still be allowed even under kill switch.
            # We allow SELLs through so the bot can flatten risk; flip this if you want a hard freeze.
            return Decision(True, "kill switch active but allowing protective sell")
        if pf.base_balance <= 0:
            return Decision(False, "no position to sell")
        if not self._cooldown_ok(pf, now_ts):
            return Decision(False, "cooldown: too soon since last trade")
        return Decision(True, "ok")

    def record_spend(self, sol_amount: float) -> None:
        self.spent_today_sol += sol_amount
        self._save()

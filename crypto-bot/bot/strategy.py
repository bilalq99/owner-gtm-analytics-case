"""Trading strategies and indicators.

Strategies are pure decision functions over a price history + current position.
They emit a Signal; they never touch the network or place orders themselves.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import StrategyConfig
from .portfolio import Portfolio


@dataclass
class Signal:
    action: str          # "BUY" | "SELL" | "HOLD"
    reason: str
    sell_fraction: float = 1.0   # fraction of position to sell on a SELL


# ---------------- indicators (pure) ----------------

def sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def rsi(values: list[float], window: int) -> float | None:
    if len(values) < window + 1:
        return None
    gains, losses = 0.0, 0.0
    for prev, cur in zip(values[-window - 1:-1], values[-window:]):
        change = cur - prev
        if change >= 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / window
    avg_loss = losses / window
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ---------------- strategies ----------------

class Strategy:
    def __init__(self, cfg: StrategyConfig) -> None:
        self.cfg = cfg

    def decide(self, prices: list[float], pf: Portfolio, now_ts: float) -> Signal:
        raise NotImplementedError

    # shared capital-preservation exits, checked before any strategy-specific logic
    def _protective_exit(self, price: float, pf: Portfolio) -> Signal | None:
        if pf.base_balance <= 0 or pf.avg_cost_sol <= 0:
            return None
        change_pct = (price - pf.avg_cost_sol) / pf.avg_cost_sol * 100.0
        if change_pct <= -self.cfg.stop_loss_pct:
            return Signal("SELL", f"stop-loss hit ({change_pct:.1f}% vs cost)")
        if change_pct >= self.cfg.take_profit_pct:
            return Signal("SELL", f"take-profit hit ({change_pct:+.1f}% vs cost)")
        return None


class MomentumStrategy(Strategy):
    def decide(self, prices: list[float], pf: Portfolio, now_ts: float) -> Signal:
        price = prices[-1]
        exit_sig = self._protective_exit(price, pf)
        if exit_sig:
            return exit_sig

        c = self.cfg
        if len(prices) < c.slow_window + 1:
            return Signal("HOLD", "warming up (not enough history)")

        fast_now = sma(prices, c.fast_window)
        slow_now = sma(prices, c.slow_window)
        fast_prev = sma(prices[:-1], c.fast_window)
        slow_prev = sma(prices[:-1], c.slow_window)
        r = rsi(prices, c.rsi_window)
        if None in (fast_now, slow_now, fast_prev, slow_prev, r):
            return Signal("HOLD", "indicators not ready")

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if crossed_up and r < c.rsi_overbought:
            return Signal("BUY", f"golden cross (fast>{slow_now:.2e}), RSI {r:.0f}")
        if crossed_up and r >= c.rsi_overbought:
            return Signal("HOLD", f"cross up but overbought (RSI {r:.0f})")
        if crossed_down and pf.base_balance > 0:
            return Signal("SELL", f"death cross (fast<slow), RSI {r:.0f}")
        return Signal("HOLD", f"no signal (RSI {r:.0f})")


class DcaStrategy(Strategy):
    def decide(self, prices: list[float], pf: Portfolio, now_ts: float) -> Signal:
        price = prices[-1]
        exit_sig = self._protective_exit(price, pf)
        if exit_sig:
            return exit_sig

        interval_s = self.cfg.dca_interval_minutes * 60
        last_buy_ts = max((t.ts for t in pf.trades if t.side == "BUY"), default=0.0)
        if now_ts - last_buy_ts >= interval_s:
            return Signal("BUY", f"DCA interval elapsed ({self.cfg.dca_interval_minutes}m)")
        return Signal("HOLD", "within DCA interval")


def build_strategy(cfg: StrategyConfig) -> Strategy:
    if cfg.name == "momentum":
        return MomentumStrategy(cfg)
    if cfg.name == "dca":
        return DcaStrategy(cfg)
    raise ValueError(f"unknown strategy '{cfg.name}'")

"""The trading engine: one cycle = observe -> decide -> risk-check -> execute -> record."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from .config import Config
from .executor import build_executor
from .portfolio import Portfolio
from .prices import JupiterClient, PriceError
from .risk import RiskManager
from .strategy import build_strategy

log = logging.getLogger("bot.engine")


class Engine:
    def __init__(self, cfg: Config, live: bool) -> None:
        self.cfg = cfg
        self.live = live
        self.state_dir = cfg.engine.state_dir
        self.client = JupiterClient(cfg)
        self.strategy = build_strategy(cfg.strategy)
        self.executor = build_executor(cfg, live)
        self.risk = RiskManager(cfg.risk, self.state_dir)
        self.portfolio = Portfolio.load(
            Path(self.state_dir) / "portfolio.json", cfg.risk.starting_sol
        )
        self.prices: list[float] = []
        self.max_history = max(cfg.strategy.slow_window, cfg.strategy.rsi_window) * 4 + 10

    # ---------- helpers ----------
    def _atomic(self, amount: float, decimals: int) -> int:
        return int(round(amount * 10 ** decimals))

    def _slippage_bps(self, side: str, ref_price: float, fill_price: float) -> float:
        if ref_price <= 0:
            return 0.0
        if side == "BUY":
            adverse = (fill_price - ref_price) / ref_price
        else:
            adverse = (ref_price - fill_price) / ref_price
        return max(0.0, adverse * 10_000)

    # ---------- one cycle ----------
    def step(self) -> None:
        p = self.cfg.pair
        now = time.time()
        try:
            price = self.client.get_price_in_sol()
        except PriceError as e:
            log.warning("price fetch failed, skipping cycle: %s", e)
            return

        self.prices.append(price)
        if len(self.prices) > self.max_history:
            self.prices = self.prices[-self.max_history:]

        equity = self.portfolio.total_equity_sol(price)
        self.risk.roll_day(now, equity)

        signal = self.strategy.decide(self.prices, self.portfolio, now)
        upnl = self.portfolio.unrealized_pnl_sol(price)
        log.info(
            "%s=%.3e SOL | pos=%.4f %s (%.4f SOL) | cash=%.4f SOL | uPnL=%+.4f rPnL=%+.4f | %s: %s",
            p.base_symbol, price, self.portfolio.base_balance, p.base_symbol,
            self.portfolio.position_value_sol(price), self.portfolio.sol_balance,
            upnl, self.portfolio.realized_pnl_sol, signal.action, signal.reason,
        )

        if signal.action == "BUY":
            self._do_buy(price, now, equity)
        elif signal.action == "SELL":
            self._do_sell(price, now, signal.sell_fraction)

        self.portfolio.save(Path(self.state_dir) / "portfolio.json")

    def _do_buy(self, ref_price: float, now: float, equity: float) -> None:
        p, c = self.cfg.pair, self.cfg.risk
        gate = self.risk.check_buy(self.portfolio, ref_price, now, equity)
        if not gate.approved:
            log.info("BUY blocked: %s", gate.reason)
            return
        amount_atomic = self._atomic(c.per_trade_sol, p.quote_decimals)
        try:
            quote = self.client.get_quote(p.quote_mint, p.base_mint, amount_atomic, c.max_slippage_bps)
        except PriceError as e:
            log.warning("BUY aborted, no quote: %s", e)
            return
        fill_price = (quote.in_amount_atomic / 10 ** p.quote_decimals) / (
            quote.out_amount_atomic / 10 ** p.base_decimals)
        slip = self._slippage_bps("BUY", ref_price, fill_price)
        sd = self.risk.check_slippage(slip)
        if not sd.approved:
            log.info("BUY aborted: %s", sd.reason)
            return
        res = self.executor.execute("BUY", quote)
        if not res.ok:
            log.error("BUY failed: %s", res.error)
            return
        self.portfolio.apply_buy(res.base_amount, res.sol_amount, res.fill_price_sol,
                                 self.executor.mode, res.tx_sig)
        self.risk.record_spend(res.sol_amount)
        log.info("BUY filled: %.4f %s for %.4f SOL @ %.3e (slip %.0fbps) tx=%s",
                 res.base_amount, p.base_symbol, res.sol_amount, res.fill_price_sol, slip, res.tx_sig)

    def _do_sell(self, ref_price: float, now: float, fraction: float) -> None:
        p, c = self.cfg.pair, self.cfg.risk
        gate = self.risk.check_sell(self.portfolio, now)
        if not gate.approved:
            log.info("SELL blocked: %s", gate.reason)
            return
        sell_base = self.portfolio.base_balance * max(0.0, min(1.0, fraction))
        if sell_base <= 0:
            return
        amount_atomic = self._atomic(sell_base, p.base_decimals)
        try:
            quote = self.client.get_quote(p.base_mint, p.quote_mint, amount_atomic, c.max_slippage_bps)
        except PriceError as e:
            log.warning("SELL aborted, no quote: %s", e)
            return
        fill_price = (quote.out_amount_atomic / 10 ** p.quote_decimals) / (
            quote.in_amount_atomic / 10 ** p.base_decimals)
        slip = self._slippage_bps("SELL", ref_price, fill_price)
        sd = self.risk.check_slippage(slip)
        if not sd.approved:
            log.info("SELL aborted: %s", sd.reason)
            return
        res = self.executor.execute("SELL", quote)
        if not res.ok:
            log.error("SELL failed: %s", res.error)
            return
        self.portfolio.apply_sell(res.base_amount, res.sol_amount, res.fill_price_sol,
                                  self.executor.mode, res.tx_sig)
        log.info("SELL filled: %.4f %s for %.4f SOL @ %.3e (slip %.0fbps) tx=%s",
                 res.base_amount, p.base_symbol, res.sol_amount, res.fill_price_sol, slip, res.tx_sig)

    # ---------- loops ----------
    def run_forever(self) -> None:
        log.info("Engine starting in %s mode. Kill switch: create '%s' to halt.",
                 self.executor.mode.upper(), self.risk.kill_switch_path)
        while True:
            try:
                self.step()
            except Exception:  # noqa: BLE001 - never let one bad cycle kill the bot
                log.exception("cycle error (continuing)")
            time.sleep(self.cfg.engine.poll_seconds)

    def run_once(self) -> None:
        self.step()

"""Portfolio: balances, cost basis, realized/unrealized P&L, persisted to disk."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Trade:
    ts: float
    side: str            # "BUY" or "SELL"
    price_sol: float     # price per base token, in SOL, actually filled
    base_amount: float   # base tokens transacted
    sol_amount: float    # SOL transacted
    mode: str            # "paper" or "live"
    tx_sig: str = ""     # live only


@dataclass
class Portfolio:
    sol_balance: float
    base_balance: float = 0.0
    avg_cost_sol: float = 0.0          # average cost basis per base token, in SOL
    realized_pnl_sol: float = 0.0
    trades: list[Trade] = field(default_factory=list)

    # ----- mutations -----
    def apply_buy(self, base_amount: float, sol_spent: float, price_sol: float, mode: str, tx_sig: str = "") -> None:
        if base_amount <= 0:
            return
        prev_cost = self.avg_cost_sol * self.base_balance
        self.base_balance += base_amount
        self.sol_balance -= sol_spent
        self.avg_cost_sol = (prev_cost + sol_spent) / self.base_balance
        self.trades.append(Trade(_now(), "BUY", price_sol, base_amount, sol_spent, mode, tx_sig))

    def apply_sell(self, base_amount: float, sol_received: float, price_sol: float, mode: str, tx_sig: str = "") -> None:
        base_amount = min(base_amount, self.base_balance)
        if base_amount <= 0:
            return
        cost_of_sold = self.avg_cost_sol * base_amount
        self.realized_pnl_sol += sol_received - cost_of_sold
        self.base_balance -= base_amount
        self.sol_balance += sol_received
        if self.base_balance <= 1e-12:
            self.base_balance = 0.0
            self.avg_cost_sol = 0.0
        self.trades.append(Trade(_now(), "SELL", price_sol, base_amount, sol_received, mode, tx_sig))

    # ----- views -----
    def position_value_sol(self, price_sol: float) -> float:
        return self.base_balance * price_sol

    def unrealized_pnl_sol(self, price_sol: float) -> float:
        return self.base_balance * (price_sol - self.avg_cost_sol)

    def total_equity_sol(self, price_sol: float) -> float:
        return self.sol_balance + self.position_value_sol(price_sol)

    def total_invested_sol(self) -> float:
        """Lifetime SOL spent on buys (used for the lifetime deployment cap)."""
        return sum(t.sol_amount for t in self.trades if t.side == "BUY")

    # ----- persistence -----
    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(p)

    @classmethod
    def load(cls, path: str | Path, starting_sol: float) -> "Portfolio":
        p = Path(path)
        if not p.exists():
            return cls(sol_balance=starting_sol)
        data = json.loads(p.read_text())
        trades = [Trade(**t) for t in data.get("trades", [])]
        return cls(
            sol_balance=data["sol_balance"],
            base_balance=data.get("base_balance", 0.0),
            avg_cost_sol=data.get("avg_cost_sol", 0.0),
            realized_pnl_sol=data.get("realized_pnl_sol", 0.0),
            trades=trades,
        )


def _now() -> float:
    import time
    return time.time()

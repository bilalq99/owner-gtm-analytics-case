import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.portfolio import Portfolio


def test_buy_sets_cost_basis_and_reduces_cash():
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(base_amount=1000, sol_spent=0.1, price_sol=0.0001, mode="paper")
    assert pf.base_balance == 1000
    assert abs(pf.sol_balance - 0.9) < 1e-12
    assert abs(pf.avg_cost_sol - 0.0001) < 1e-12


def test_averaging_cost_basis_across_two_buys():
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")   # cost 0.0001
    pf.apply_buy(1000, 0.3, 0.0003, "paper")   # cost 0.0003
    # 0.4 SOL for 2000 tokens -> 0.0002 avg
    assert abs(pf.avg_cost_sol - 0.0002) < 1e-12


def test_realized_pnl_on_profitable_sell():
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")
    pf.apply_sell(1000, 0.2, 0.0002, "paper")  # bought 0.1, sold 0.2
    assert abs(pf.realized_pnl_sol - 0.1) < 1e-12
    assert pf.base_balance == 0.0
    assert pf.avg_cost_sol == 0.0


def test_unrealized_pnl_and_equity():
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")
    # price doubles
    assert abs(pf.unrealized_pnl_sol(0.0002) - 0.1) < 1e-12
    assert abs(pf.total_equity_sol(0.0002) - (0.9 + 0.2)) < 1e-12


def test_partial_sell_keeps_cost_basis():
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")
    pf.apply_sell(500, 0.1, 0.0002, "paper")
    assert pf.base_balance == 500
    assert abs(pf.avg_cost_sol - 0.0001) < 1e-12  # unchanged by sells


def test_persistence_roundtrip(tmp_path):
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")
    path = tmp_path / "pf.json"
    pf.save(path)
    loaded = Portfolio.load(path, starting_sol=999)
    assert loaded.base_balance == 1000
    assert abs(loaded.sol_balance - 0.9) < 1e-12
    assert len(loaded.trades) == 1


def test_total_invested_counts_only_buys():
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")
    pf.apply_sell(1000, 0.2, 0.0002, "paper")
    assert abs(pf.total_invested_sol() - 0.1) < 1e-12

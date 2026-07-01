import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.config import RiskConfig
from bot.portfolio import Portfolio
from bot.risk import RiskManager


def make_risk(tmp_path, **over):
    base = dict(
        starting_sol=1.0, max_position_sol=0.25, per_trade_sol=0.05,
        max_total_invested_sol=0.5, max_daily_spend_sol=0.2,
        daily_loss_limit_sol=0.15, max_slippage_bps=100,
        min_seconds_between_trades=120, kill_switch_file="STOP",
    )
    base.update(over)
    cfg = RiskConfig(**base)
    return RiskManager(cfg, str(tmp_path), kill_switch_dir=str(tmp_path))


def test_buy_approved_normally(tmp_path):
    rm = make_risk(tmp_path)
    pf = Portfolio(sol_balance=1.0)
    rm.roll_day(1000, 1.0)
    d = rm.check_buy(pf, price_sol=0.0001, now_ts=1000, equity_sol=1.0)
    assert d.approved


def test_kill_switch_blocks_buy(tmp_path):
    rm = make_risk(tmp_path)
    (tmp_path / "STOP").write_text("halt")
    pf = Portfolio(sol_balance=1.0)
    rm.roll_day(1000, 1.0)
    d = rm.check_buy(pf, 0.0001, 1000, 1.0)
    assert not d.approved and "KILL" in d.reason


def test_insufficient_balance_blocks_buy(tmp_path):
    rm = make_risk(tmp_path)
    pf = Portfolio(sol_balance=0.01)  # < per_trade 0.05
    rm.roll_day(1000, 0.01)
    d = rm.check_buy(pf, 0.0001, 1000, 0.01)
    assert not d.approved and "insufficient" in d.reason


def test_max_position_cap(tmp_path):
    rm = make_risk(tmp_path, max_position_sol=0.05, per_trade_sol=0.05,
                   min_seconds_between_trades=0)
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.05, 0.00005, "paper")  # position already at 0.05 at cost price
    now = pf.trades[-1].ts + 1
    rm.roll_day(now, 1.0)
    # value at price 0.00005 == 0.05, adding 0.05 exceeds cap
    d = rm.check_buy(pf, 0.00005, now, 1.0)
    assert not d.approved and "max position" in d.reason


def test_daily_spend_cap(tmp_path):
    rm = make_risk(tmp_path, max_daily_spend_sol=0.05, per_trade_sol=0.05)
    pf = Portfolio(sol_balance=1.0)
    rm.roll_day(1000, 1.0)
    rm.record_spend(0.05)  # already spent the daily cap
    d = rm.check_buy(pf, 0.0001, 2000, 1.0)
    assert not d.approved and "daily spend" in d.reason


def test_lifetime_invested_cap(tmp_path):
    rm = make_risk(tmp_path, max_total_invested_sol=0.1, per_trade_sol=0.05,
                   max_position_sol=0.1, max_daily_spend_sol=1.0,
                   min_seconds_between_trades=0)
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.05, 0.00005, "paper")
    pf.apply_sell(1000, 0.05, 0.00005, "paper")  # flat position, but 0.05 lifetime invested
    pf.apply_buy(1000, 0.05, 0.00005, "paper")   # 0.10 lifetime invested
    now = pf.trades[-1].ts + 1
    rm.roll_day(now, 1.0)
    d = rm.check_buy(pf, 0.00005, now, 1.0)       # would push to 0.15 > 0.10 cap
    assert not d.approved and "lifetime" in d.reason


def test_daily_loss_circuit_breaker(tmp_path):
    rm = make_risk(tmp_path, daily_loss_limit_sol=0.1)
    pf = Portfolio(sol_balance=1.0)
    rm.roll_day(1000, 1.0)          # day starts at equity 1.0
    d = rm.check_buy(pf, 0.0001, 2000, equity_sol=0.85)  # down 0.15 > 0.1 limit
    assert not d.approved and "daily loss" in d.reason


def test_cooldown_blocks_rapid_trades(tmp_path):
    rm = make_risk(tmp_path, min_seconds_between_trades=120)
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.05, 0.00005, "paper")
    rm.roll_day(pf.trades[-1].ts + 10, 1.0)
    d = rm.check_buy(pf, 0.00005, pf.trades[-1].ts + 10, 1.0)
    assert not d.approved and "cooldown" in d.reason


def test_slippage_gate(tmp_path):
    rm = make_risk(tmp_path, max_slippage_bps=100)
    assert rm.check_slippage(50).approved
    assert not rm.check_slippage(150).approved


def test_day_rolls_and_resets_spend(tmp_path):
    rm = make_risk(tmp_path)
    rm.roll_day(0, 1.0)            # 1970-01-01
    rm.record_spend(0.1)
    assert rm.spent_today_sol == 0.1
    rm.roll_day(90_000, 1.0)      # next UTC day
    assert rm.spent_today_sol == 0.0

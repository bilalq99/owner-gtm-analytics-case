import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.config import StrategyConfig
from bot.portfolio import Portfolio
from bot.strategy import MomentumStrategy, DcaStrategy, sma, rsi


def make_cfg(**over):
    base = dict(
        name="momentum", fast_window=3, slow_window=5, rsi_window=3,
        rsi_overbought=75, rsi_oversold=30, take_profit_pct=30.0,
        stop_loss_pct=15.0, dca_interval_minutes=60,
    )
    base.update(over)
    return StrategyConfig(**base)


def test_sma_and_rsi_basic():
    assert sma([1, 2, 3], 3) == 2
    assert sma([1, 2], 3) is None
    # strictly rising series -> RSI 100
    assert rsi([1, 2, 3, 4], 3) == 100.0


def test_stop_loss_triggers_sell():
    cfg = make_cfg()
    s = MomentumStrategy(cfg)
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")  # cost 0.0001
    # price down 20% > 15% stop
    sig = s.decide([0.00008], pf, now_ts=1000)
    assert sig.action == "SELL"
    assert "stop-loss" in sig.reason


def test_take_profit_triggers_sell():
    cfg = make_cfg()
    s = MomentumStrategy(cfg)
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")
    sig = s.decide([0.00014], pf, now_ts=1000)  # +40% > 30% tp
    assert sig.action == "SELL"
    assert "take-profit" in sig.reason


def test_warmup_holds():
    cfg = make_cfg()
    s = MomentumStrategy(cfg)
    pf = Portfolio(sol_balance=1.0)
    sig = s.decide([0.0001, 0.0001], pf, now_ts=1000)
    assert sig.action == "HOLD"


def test_golden_cross_buys():
    # gradual move so fast SMA crosses above slow SMA on the last step while RSI
    # stays below overbought (a single-candle spike would max RSI and be filtered out)
    cfg = make_cfg(fast_window=2, slow_window=3, rsi_window=3, rsi_overbought=90)
    s = MomentumStrategy(cfg)
    pf = Portfolio(sol_balance=1.0)
    prices = [2.0, 3.0, 1.0, 2.0, 3.0]
    sig = s.decide(prices, pf, now_ts=1000)
    assert sig.action == "BUY"


def test_overbought_blocks_buy():
    cfg = make_cfg(fast_window=2, slow_window=3, rsi_window=2, rsi_overbought=50)
    s = MomentumStrategy(cfg)
    pf = Portfolio(sol_balance=1.0)
    prices = [1.0, 1.0, 1.0, 1.0, 2.0]  # RSI will be 100 > 50
    sig = s.decide(prices, pf, now_ts=1000)
    assert sig.action == "HOLD"
    assert "overbought" in sig.reason


def test_dca_buys_after_interval():
    cfg = make_cfg(name="dca", dca_interval_minutes=1)
    s = DcaStrategy(cfg)
    pf = Portfolio(sol_balance=1.0)
    sig = s.decide([0.0001], pf, now_ts=10_000)  # no prior buys -> last_buy_ts=0
    assert sig.action == "BUY"


def test_dca_holds_within_interval():
    cfg = make_cfg(name="dca", dca_interval_minutes=60)
    s = DcaStrategy(cfg)
    pf = Portfolio(sol_balance=1.0)
    pf.apply_buy(1000, 0.1, 0.0001, "paper")
    sig = s.decide([0.0001], pf, now_ts=pf.trades[-1].ts + 5)
    assert sig.action == "HOLD"

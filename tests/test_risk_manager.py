import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from risk.risk_manager import RiskManager
from core.state_manager import BotState

CFG = {"risk_per_trade_pct": 1.0, "max_exposure_per_asset_pct": 7.5,
       "max_total_exposure_pct": 30.0, "daily_loss_limit_pct": 3.0,
       "weekly_loss_limit_pct": 5.0, "max_drawdown_pct": 10.0, "max_open_positions": 3}

def test_clamp_exposure():
    rm = RiskManager(CFG); rm.initialize(1000)
    d = rm.evaluate_entry("BTCUSDT", 1000, {}, 100, 95)
    assert d.allowed
    assert d.adjusted_quote <= 75.0 + 1e-6

def test_max_positions():
    rm = RiskManager(CFG); rm.initialize(1000)
    states = {f"S{i}": BotState(symbol=f"S{i}", in_position=True, entry_price=1.0, quantity=1.0) for i in range(3)}
    assert not rm.evaluate_entry("NEW", 1000, states, 100, 95).allowed

def test_daily_loss_veto():
    rm = RiskManager(CFG); rm.initialize(1000)
    assert not rm.evaluate_entry("X", 960, {}, 100, 95).allowed

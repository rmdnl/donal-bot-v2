import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from risk.breakeven_manager import BreakevenManager
from core.state_manager import BotState

def test_trigger():
    bm = BreakevenManager(enabled=True, trigger_atr_multiplier=1.0)
    st = BotState(symbol="X", in_position=True, entry_price=100.0, entry_atr=2.0)
    assert bm.check(st, 101.0) is None
    assert bm.check(st, 102.5) == 100.0

def test_disabled():
    bm = BreakevenManager(enabled=False)
    st = BotState(symbol="X", in_position=True, entry_price=100.0, entry_atr=2.0)
    assert bm.check(st, 110.0) is None

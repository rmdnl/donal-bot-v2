import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.state_manager import StateManager, BotState

def test_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        sm = StateManager(os.path.join(d, "t.db"))
        sm.save_state(BotState(symbol="BTCUSDT", in_position=True, entry_price=100.0, quantity=1.5, strategy="DONAL"))
        ld = sm.load_state("BTCUSDT")
        assert ld.in_position and ld.entry_price == 100.0 and ld.strategy == "DONAL"

def test_breakeven_update():
    with tempfile.TemporaryDirectory() as d:
        sm = StateManager(os.path.join(d, "t.db"))
        sm.save_state(BotState(symbol="ETHUSDT", in_position=True, entry_price=2000.0, quantity=1.0))
        sm.update_breakeven("ETHUSDT", 2000.0)
        ld = sm.load_state("ETHUSDT")
        assert ld.breakeven_triggered and ld.sl_price == 2000.0

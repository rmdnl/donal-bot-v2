from decimal import Decimal

from app.position.position_manager import PositionManager, PositionState
from app.recovery.recovery_engine import RecoveryEngine
from app.storage.trade_journal import JournalEntry, TradeJournal


class FakeGateway:
    def __init__(self, order):
        self.order = order
        self.calls = []

    def get_order(self, symbol, client_order_id):
        self.calls.append((symbol, client_order_id))
        return self.order


def test_recovery_restores_filled_position(tmp_path):
    journal = TradeJournal(str(tmp_path / "trades.db"))

    journal.record(
        JournalEntry(
            "DNL-001",
            "BTCUSDT",
            "BUY",
            "FILLED",
            "0.01",
            "0.008",
        )
    )

    manager = PositionManager()

    gateway = FakeGateway({
        "status": "FILLED",
        "executedQty": "0.008",
        "cummulativeQuoteQty": "800",
    })

    result = RecoveryEngine(
        journal,
        gateway,
    ).recover()

    assert result.reconciled == 0
    assert manager.position.state == PositionState.FLAT

    manager.restore(
        symbol="BTCUSDT",
        quantity=Decimal("0.008"),
        average_entry=Decimal(100000),
    )

    assert manager.position.state == PositionState.LONG
    assert manager.position.quantity == Decimal("0.008")


def test_recovery_filled_buy_restores_position(tmp_path):
    journal = TradeJournal(str(tmp_path / "trades.db"))

    journal.record(
        JournalEntry(
            "DNL-005",
            "BTCUSDT",
            "BUY",
            "NEW",
            "0.01",
            "0",
        )
    )

    manager = PositionManager()

    gateway = FakeGateway({
        "status": "FILLED",
        "executedQty": "0.008",
        "cummulativeQuoteQty": "800",
    })

    result = RecoveryEngine(
        journal,
        gateway,
        manager,
    ).recover()

    assert result.reconciled == 1
    assert manager.position.state == PositionState.LONG
    assert manager.position.symbol == "BTCUSDT"
    assert manager.position.quantity == Decimal("0.008")
    assert manager.position.average_entry == Decimal(100000)

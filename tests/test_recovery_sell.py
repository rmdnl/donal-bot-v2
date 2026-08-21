from decimal import Decimal

from app.position.fill_reconciler import FillReconciler
from app.position.position_manager import PositionManager, PositionState
from app.recovery.recovery_engine import RecoveryEngine
from app.storage.trade_journal import JournalEntry, TradeJournal


class FakeGateway:
    def __init__(self):
        self.calls = []

    def get_order(self, symbol, client_order_id):
        self.calls.append((symbol, client_order_id))


def test_recovery_does_not_reopen_position_after_filled_sell(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-BUY-RECOVERY",
            "BTCUSDT",
            "BUY",
            "FILLED",
            "0.00007",
            "0.00007",
        )
    )

    journal.record(
        JournalEntry(
            "DNL-SELL-RECOVERY",
            "BTCUSDT",
            "SELL",
            "FILLED",
            "0.00007",
            "0.00007",
        )
    )

    positions = PositionManager()
    gateway = FakeGateway()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    result = RecoveryEngine(
        journal,
        gateway,
        reconciler,
    ).recover()

    assert result.checked == 0
    assert result.reconciled == 0
    assert result.skipped == 0
    assert result.failed == 0

    assert positions.position.state == PositionState.FLAT
    assert positions.position.quantity == Decimal(0)
    assert gateway.calls == []


def test_sell_journal_is_terminal_and_not_pending(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-SELL-TERMINAL",
            "BTCUSDT",
            "SELL",
            "FILLED",
            "0.00007",
            "0.00007",
        )
    )

    pending = journal.pending()

    assert all(
        entry.client_order_id != "DNL-SELL-TERMINAL"
        for entry in pending
    )

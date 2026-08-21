from app.recovery.recovery_engine import RecoveryEngine
from app.storage.trade_journal import (
    JournalEntry,
    TradeJournal,
)


class FakeGateway:
    def __init__(self):
        self.calls = []

    def get_order(self, symbol, client_order_id):
        self.calls.append(
            (symbol, client_order_id)
        )


def test_recovery_reconciles_pending_orders(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-001",
            "BTCUSDT",
            "BUY",
            "NEW",
            "0.01",
            "0",
        )
    )

    gateway = FakeGateway()
    result = RecoveryEngine(
        journal,
        gateway,
    ).recover()

    assert result.checked == 1
    assert result.reconciled == 1
    assert gateway.calls == [
        ("BTCUSDT", "DNL-001")
    ]


def test_recovery_ignores_terminal_orders(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-002",
            "BTCUSDT",
            "BUY",
            "FILLED",
            "0.01",
            "0.01",
        )
    )

    gateway = FakeGateway()
    result = RecoveryEngine(
        journal,
        gateway,
    ).recover()

    assert result.checked == 0
    assert result.reconciled == 0
    assert gateway.calls == []


def test_recovery_handles_multiple_orders(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-003",
            "BTCUSDT",
            "BUY",
            "PARTIALLY_FILLED",
            "0.01",
            "0.005",
        )
    )

    journal.record(
        JournalEntry(
            "DNL-004",
            "ETHUSDT",
            "BUY",
            "NEW",
            "0.1",
            "0",
        )
    )

    gateway = FakeGateway()
    result = RecoveryEngine(
        journal,
        gateway,
    ).recover()

    assert result.checked == 2
    assert result.reconciled == 2
    assert len(gateway.calls) == 2

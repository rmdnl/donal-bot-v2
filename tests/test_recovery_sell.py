from decimal import Decimal

from app.position.fill_reconciler import Fill, FillReconciler
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


def test_recovery_keeps_remaining_position_after_partial_sell(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-BUY-PARTIAL-RECOVERY",
            "BTCUSDT",
            "BUY",
            "FILLED",
            "0.00007",
            "0.00007",
        )
    )

    journal.record(
        JournalEntry(
            "DNL-SELL-PARTIAL-RECOVERY",
            "BTCUSDT",
            "SELL",
            "FILLED",
            "0.00004",
            "0.00004",
        )
    )

    positions = PositionManager()
    positions.restore(
        symbol="BTCUSDT",
        quantity=Decimal("0.00003"),
        average_entry=Decimal("77857.73"),
        total_fees=Decimal("0.00312007"),
    )

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
    assert result.failed == 0

    assert positions.position.state == PositionState.LONG
    assert positions.position.symbol == "BTCUSDT"
    assert positions.position.quantity == Decimal("0.00003")
    assert positions.position.average_entry == Decimal("77857.73")
    assert positions.position.total_fees == Decimal("0.00312007")

    assert gateway.calls == []


def test_duplicate_partial_sell_does_not_reduce_position_twice(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    reconciler.reconcile(
        Fill(
            client_order_id="DNL-BUY-PARTIAL-IDEMPOTENT",
            symbol="BTCUSDT",
            side="BUY",
            quantity=Decimal("0.00010"),
            executed_quantity=Decimal("0.00010"),
            price=Decimal(77800),
            fee=Decimal("0.0001"),
            status="FILLED",
        )
    )

    sell = Fill(
        client_order_id="DNL-SELL-PARTIAL-IDEMPOTENT",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.00004"),
        executed_quantity=Decimal("0.00004"),
        price=Decimal(78000),
        fee=Decimal("0.00312"),
        status="FILLED",
    )

    first = reconciler.reconcile(sell)
    second = reconciler.reconcile(sell)

    assert first == second
    assert second.state == PositionState.LONG
    assert second.quantity == Decimal("0.00006")
    assert second.total_fees == (
        Decimal("0.0001")
        + Decimal("0.00312")
    )






def test_restart_recovery_rebuilds_flat_position_after_filled_sell(
    tmp_path,
):
    db_path = str(tmp_path / "trades.db")

    journal = TradeJournal(db_path)

    journal.record(
        JournalEntry(
            "DNL-BUY-RESTART",
            "BTCUSDT",
            "BUY",
            "FILLED",
            "0.00007",
            "0.00007",
        )
    )

    journal.record(
        JournalEntry(
            "DNL-SELL-RESTART",
            "BTCUSDT",
            "SELL",
            "FILLED",
            "0.00007",
            "0.00007",
        )
    )

    # Simulate bot restart:
    # new PositionManager, no in-memory position.
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )
    gateway = FakeGateway()

    result = RecoveryEngine(
        journal,
        gateway,
        reconciler,
    ).recover()

    assert result.checked == 0
    assert result.reconciled == 0
    assert result.failed == 0

    assert positions.position.state == PositionState.FLAT
    assert positions.position.quantity == Decimal(0)
    assert gateway.calls == []

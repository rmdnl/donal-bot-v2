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


def test_replay_filled_buy_and_partial_sell_after_restart(
    tmp_path,
):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-REPLAY-BUY",
            symbol="BTCUSDT",
            side="BUY",
            status="FILLED",
            quantity="0.00010",
            executed_quantity="0.00010",
            price="77800",
            fee="0.0001",
        )
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-REPLAY-SELL",
            symbol="BTCUSDT",
            side="SELL",
            status="FILLED",
            quantity="0.00003",
            executed_quantity="0.00003",
            price="78000",
            fee="0.00003",
        )
    )

    manager = PositionManager()
    gateway = FakeGateway(None)

    recovery = RecoveryEngine(
        journal,
        gateway,
        manager,
    )

    recovery.rebuild_position()

    assert manager.position.state == PositionState.LONG
    assert manager.position.symbol == "BTCUSDT"
    assert manager.position.quantity == Decimal("0.00007")
    assert manager.position.average_entry == Decimal(77800)
    assert manager.position.total_fees == Decimal("0.00013")


def test_replay_filled_buy_and_full_sell_after_restart(
    tmp_path,
):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-REPLAY-FULL-BUY",
            symbol="BTCUSDT",
            side="BUY",
            status="FILLED",
            quantity="0.00010",
            executed_quantity="0.00010",
            price="77800",
            fee="0.0001",
        )
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-REPLAY-FULL-SELL",
            symbol="BTCUSDT",
            side="SELL",
            status="FILLED",
            quantity="0.00010",
            executed_quantity="0.00010",
            price="78000",
            fee="0.0001",
        )
    )

    manager = PositionManager()
    recovery = RecoveryEngine(
        journal,
        FakeGateway(None),
        manager,
    )

    recovery.rebuild_position()

    assert manager.position.state == PositionState.FLAT
    assert manager.position.quantity == Decimal(0)
    assert manager.position.realized_pnl == Decimal("0.01980")
    assert manager.position.total_fees == Decimal("0.0002")


def test_rebuild_position_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-IDEMP-BUY",
            symbol="BTCUSDT",
            side="BUY",
            status="FILLED",
            quantity="0.00010",
            executed_quantity="0.00010",
            price="77800",
            fee="0.0001",
        )
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-IDEMP-SELL",
            symbol="BTCUSDT",
            side="SELL",
            status="FILLED",
            quantity="0.00003",
            executed_quantity="0.00003",
            price="78000",
            fee="0.00003",
        )
    )

    manager = PositionManager()
    recovery = RecoveryEngine(
        journal,
        FakeGateway(None),
        manager,
    )

    recovery.rebuild_position()

    first = manager.position

    recovery.rebuild_position()

    second = manager.position

    assert second == first
    assert second.state == PositionState.LONG
    assert second.quantity == Decimal("0.00007")
    assert second.realized_pnl == Decimal("0.00587")
    assert second.total_fees == Decimal("0.00013")


def test_rebuild_position_is_idempotent_after_restart(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-CRASH-BUY",
            "BTCUSDT",
            "BUY",
            "FILLED",
            "0.00010",
            "0.00010",
            "77800",
            "0.0001",
        )
    )

    journal.record(
        JournalEntry(
            "DNL-CRASH-SELL",
            "BTCUSDT",
            "SELL",
            "FILLED",
            "0.00003",
            "0.00003",
            "78000",
            "0.00003",
        )
    )

    manager = PositionManager()

    recovery = RecoveryEngine(
        journal,
        FakeGateway(None),
        manager,
    )

    recovery.rebuild_position()
    first = manager.position

    recovery.rebuild_position()
    second = manager.position

    assert second == first
    assert second.state == PositionState.LONG
    assert second.symbol == "BTCUSDT"
    assert second.quantity == Decimal("0.00007")
    assert second.total_fees == Decimal("0.00013")


def test_rebuild_position_after_full_sell_is_flat(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-CRASH-FULL-BUY",
            "BTCUSDT",
            "BUY",
            "FILLED",
            "0.00010",
            "0.00010",
            "77800",
            "0.0001",
        )
    )

    journal.record(
        JournalEntry(
            "DNL-CRASH-FULL-SELL",
            "BTCUSDT",
            "SELL",
            "FILLED",
            "0.00010",
            "0.00010",
            "78000",
            "0.0001",
        )
    )

    manager = PositionManager()

    recovery = RecoveryEngine(
        journal,
        FakeGateway(None),
        manager,
    )

    recovery.rebuild_position()

    assert manager.position.state == PositionState.FLAT
    assert manager.position.quantity == Decimal(0)
    assert manager.position.total_fees == Decimal("0.0002")


def test_rebuild_position_ignores_non_filled_orders(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    journal.record(
        JournalEntry(
            "DNL-PENDING-BUY",
            "BTCUSDT",
            "BUY",
            "NEW",
            "0.00010",
            "0",
            "0",
            "0",
        )
    )

    manager = PositionManager()

    recovery = RecoveryEngine(
        journal,
        FakeGateway(None),
        manager,
    )

    recovery.rebuild_position()

    assert manager.position.state == PositionState.FLAT
    assert manager.position.quantity == Decimal(0)

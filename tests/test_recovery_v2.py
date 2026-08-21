from decimal import Decimal
from unittest.mock import Mock

from app.position.fill_reconciler import FillReconciler
from app.position.position_manager import PositionManager
from app.recovery.recovery_engine import RecoveryEngine
from app.storage.trade_journal import (
    JournalEntry,
    TradeJournal,
)

FILLED_ORDER = {
    "symbol": "BTCUSDT",
    "orderId": 5567361,
    "clientOrderId": "DNL-TEST-001",
    "origQty": "0.00007000",
    "executedQty": "0.00007000",
    "cummulativeQuoteQty": "5.45004110",
    "status": "FILLED",
    "side": "BUY",
    "fills": [
        {
            "price": "77857.73",
            "qty": "0.00007000",
            "commission": "0.00000007",
            "commissionAsset": "BTC",
        }
    ],
}


def make_engine(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    gateway = Mock()

    return (
        RecoveryEngine(
            journal=journal,
            gateway=gateway,
            reconciler=reconciler,
        ),
        journal,
        positions,
        gateway,
    )


def test_recovery_reconciles_filled_pending_order(tmp_path):
    engine, journal, positions, gateway = make_engine(
        tmp_path
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-TEST-001",
            symbol="BTCUSDT",
            side="BUY",
            status="NEW",
            quantity="0.00007000",
            executed_quantity="0",
        )
    )

    gateway.get_order.return_value = FILLED_ORDER

    result = engine.recover()

    assert result.checked == 1
    assert result.reconciled == 1
    assert result.failed == 0

    assert positions.position.quantity == Decimal(
        "0.00007000"
    )
    assert positions.position.symbol == "BTCUSDT"

    entry = journal.get("DNL-TEST-001")

    assert entry is not None
    assert entry.status == "FILLED"


def test_recovery_does_not_duplicate_filled_order(
    tmp_path,
):
    engine, journal, positions, gateway = make_engine(
        tmp_path
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-TEST-001",
            symbol="BTCUSDT",
            side="BUY",
            status="NEW",
            quantity="0.00007000",
            executed_quantity="0",
        )
    )

    gateway.get_order.return_value = FILLED_ORDER

    first = engine.recover()

    assert first.reconciled == 1

    second = engine.recover()

    assert second.checked == 0
    assert positions.position.quantity == Decimal(
        "0.00007000"
    )


def test_recovery_skips_non_terminal_order(tmp_path):
    engine, journal, positions, gateway = make_engine(
        tmp_path
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-TEST-002",
            symbol="BTCUSDT",
            side="BUY",
            status="NEW",
            quantity="0.00007000",
            executed_quantity="0",
        )
    )

    gateway.get_order.return_value = {
        **FILLED_ORDER,
        "status": "NEW",
    }

    result = engine.recover()

    assert result.checked == 1
    assert result.reconciled == 0
    assert result.skipped == 1
    assert positions.position.quantity == Decimal(0)


def test_recovery_handles_multiple_orders(tmp_path):
    engine, journal, _positions, gateway = make_engine(
        tmp_path
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-TEST-001",
            symbol="BTCUSDT",
            side="BUY",
            status="NEW",
            quantity="0.00007000",
            executed_quantity="0",
        )
    )

    journal.record(
        JournalEntry(
            client_order_id="DNL-TEST-002",
            symbol="ETHUSDT",
            side="BUY",
            status="NEW",
            quantity="0.002",
            executed_quantity="0",
        )
    )

    gateway.get_order.side_effect = [
        FILLED_ORDER,
        {
            **FILLED_ORDER,
            "symbol": "ETHUSDT",
            "clientOrderId": "DNL-TEST-002",
            "origQty": "0.002",
            "executedQty": "0.002",
            "cummulativeQuoteQty": "8",
            "fills": [
                {
                    "price": "4000",
                    "qty": "0.002",
                    "commission": "0.000002",
                    "commissionAsset": "ETH",
                }
            ],
        },
    ]

    result = engine.recover()

    assert result.checked == 2
    assert result.reconciled == 1
    assert result.failed == 1

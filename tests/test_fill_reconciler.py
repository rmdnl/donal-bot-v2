from decimal import Decimal

import pytest

from app.position.fill_reconciler import (
    Fill,
    FillReconciler,
    FillReconciliationError,
)
from app.position.position_manager import PositionManager
from app.storage.trade_journal import TradeJournal


def make_fill(
    client_order_id="DNL-TEST-001",
):
    return Fill(
        client_order_id=client_order_id,
        symbol="BTCUSDT",
        side="BUY",
        quantity=Decimal("0.00007"),
        executed_quantity=Decimal("0.00007"),
        price=Decimal("77857.73"),
        fee=Decimal("0.00000007"),
        status="FILLED",
    )


def test_filled_order_updates_journal_and_position(
    tmp_path,
):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    result = FillReconciler(
        journal,
        positions,
    ).reconcile(make_fill())

    assert result.symbol == "BTCUSDT"
    assert result.quantity == Decimal("0.00007")
    assert result.average_entry == Decimal(
        "77857.73"
    )
    assert result.total_fees == Decimal(
        "0.00000007"
    )
    assert result.realized_pnl == -Decimal(
        "0.00000007"
    )

    entry = journal.get("DNL-TEST-001")

    assert entry is not None
    assert entry.status == "FILLED"
    assert entry.executed_quantity == "0.00007"


def test_reconciliation_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    reconciler = FillReconciler(
        journal,
        positions,
    )

    first = reconciler.reconcile(
        make_fill()
    )

    second = reconciler.reconcile(
        make_fill()
    )

    assert first == second
    assert positions.position.quantity == Decimal(
        "0.00007"
    )


def test_different_filled_order_cannot_duplicate_position(
    tmp_path,
):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    reconciler = FillReconciler(
        journal,
        positions,
    )

    reconciler.reconcile(
        make_fill("DNL-TEST-001")
    )

    with pytest.raises(
        FillReconciliationError,
    ):
        reconciler.reconcile(
            make_fill("DNL-TEST-002")
        )


def test_unfilled_order_is_rejected(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    fill = make_fill()
    fill = Fill(
        **{
            **fill.__dict__,
            "status": "NEW",
        }
    )

    with pytest.raises(
        FillReconciliationError
    ):
        FillReconciler(
            journal,
            positions,
        ).reconcile(fill)

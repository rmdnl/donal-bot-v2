from decimal import Decimal

import pytest

from app.position.fill_reconciler import (
    Fill,
    FillReconciler,
    FillReconciliationError,
)
from app.position.position_manager import (
    PositionManager,
    PositionState,
)
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


def test_sell_fill_closes_long_position_and_updates_journal(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    reconciler = FillReconciler(
        journal,
        positions,
    )

    buy = make_fill("DNL-BUY-001")
    reconciler.reconcile(buy)

    sell = Fill(
        client_order_id="DNL-SELL-001",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.00007"),
        executed_quantity=Decimal("0.00007"),
        price=Decimal(78000),
        fee=Decimal("0.00546"),
        status="FILLED",
    )

    result = reconciler.reconcile(sell)

    assert result.state == PositionState.FLAT
    assert result.quantity == Decimal(0)
    assert result.realized_pnl > Decimal(0)

    buy_entry = journal.get("DNL-BUY-001")
    sell_entry = journal.get("DNL-SELL-001")

    assert buy_entry is not None
    assert sell_entry is not None
    assert buy_entry.side == "BUY"
    assert sell_entry.side == "SELL"
    assert sell_entry.status == "FILLED"
    assert sell_entry.executed_quantity == "0.00007"


def test_duplicate_sell_fill_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    buy = make_fill("DNL-BUY-IDEMPOTENT")
    reconciler.reconcile(buy)

    sell = Fill(
        client_order_id="DNL-SELL-IDEMPOTENT",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.00007"),
        executed_quantity=Decimal("0.00007"),
        price=Decimal(78000),
        fee=Decimal("0.00546"),
        status="FILLED",
    )

    first = reconciler.reconcile(sell)

    pnl_after_first = first.realized_pnl
    fees_after_first = first.total_fees

    second = reconciler.reconcile(sell)

    assert second == first
    assert second.state == PositionState.FLAT
    assert second.quantity == Decimal(0)
    assert second.realized_pnl == pnl_after_first
    assert second.total_fees == fees_after_first

    entry = journal.get("DNL-SELL-IDEMPOTENT")
    assert entry is not None
    assert entry.status == "FILLED"


def test_partial_sell_keeps_remaining_long_and_accounts_fee(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    buy = make_fill("DNL-BUY-PARTIAL")
    reconciler.reconcile(buy)

    sell = Fill(
        client_order_id="DNL-SELL-PARTIAL-001",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.00004"),
        executed_quantity=Decimal("0.00004"),
        price=Decimal(78000),
        fee=Decimal("0.00312"),
        status="FILLED",
    )

    result = reconciler.reconcile(sell)

    assert result.state == PositionState.LONG
    assert result.symbol == "BTCUSDT"
    assert result.quantity == Decimal("0.00003")
    assert result.average_entry == Decimal("77857.73")
    assert result.total_fees == (
        Decimal("0.00000007")
        + Decimal("0.00312")
    )


def test_second_partial_sell_closes_remaining_position(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    reconciler.reconcile(
        make_fill("DNL-BUY-PARTIAL-002")
    )

    first_sell = Fill(
        client_order_id="DNL-SELL-PARTIAL-002-A",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.00004"),
        executed_quantity=Decimal("0.00004"),
        price=Decimal(78000),
        fee=Decimal("0.00312"),
        status="FILLED",
    )

    reconciler.reconcile(first_sell)

    second_sell = Fill(
        client_order_id="DNL-SELL-PARTIAL-002-B",
        symbol="BTCUSDT",
        side="SELL",
        quantity=Decimal("0.00003"),
        executed_quantity=Decimal("0.00003"),
        price=Decimal(78100),
        fee=Decimal("0.002343"),
        status="FILLED",
    )

    result = reconciler.reconcile(second_sell)

    assert result.state == PositionState.FLAT
    assert result.quantity == Decimal(0)
    assert result.symbol == ""
    assert result.total_fees == (
        Decimal("0.00000007")
        + Decimal("0.00312")
        + Decimal("0.002343")
    )

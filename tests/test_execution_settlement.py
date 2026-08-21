from decimal import Decimal

import pytest

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
)
from app.execution.execution_settlement import (
    ExecutionSettlement,
    ExecutionSettlementError,
)
from app.position.fill_reconciler import FillReconciler
from app.position.position_manager import (
    PositionManager,
    PositionState,
)
from app.storage.trade_journal import TradeJournal


def test_filled_buy_is_settled_into_position(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    order = ExchangeOrder(
        client_order_id="DNL-SETTLE-BUY",
        exchange_order_id="100",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100.0,
        side="BUY",
        fee=0.001,
    )

    result = settlement.settle(order)

    assert result.state == PositionState.LONG
    assert result.symbol == "BTCUSDT"
    assert result.quantity == Decimal("0.001")
    assert result.average_entry == Decimal(100000)
    assert result.total_fees == Decimal("0.001")


def test_filled_sell_is_settled_into_flat_position(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    reconciler = FillReconciler(
        journal,
        manager,
    )

    settlement = ExecutionSettlement(reconciler)

    buy = ExchangeOrder(
        client_order_id="DNL-SETTLE-BUY",
        exchange_order_id="100",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100.0,
        side="BUY",
        fee=0.001,
    )

    settlement.settle(buy)

    sell = ExchangeOrder(
        client_order_id="DNL-SETTLE-SELL",
        exchange_order_id="101",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=101.0,
        side="SELL",
        fee=0.001,
    )

    result = settlement.settle(sell)

    assert result.state == PositionState.FLAT
    assert result.quantity == Decimal(0)
    assert result.total_fees == Decimal("0.002")


def test_settlement_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    order = ExchangeOrder(
        client_order_id="DNL-IDEMP-SETTLE",
        exchange_order_id="200",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100.0,
        side="BUY",
        fee=0.001,
    )

    first = settlement.settle(order)
    second = settlement.settle(order)

    assert first == second
    assert manager.position.state == PositionState.LONG
    assert manager.position.quantity == Decimal("0.001")


def test_non_filled_order_cannot_settle(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    order = ExchangeOrder(
        client_order_id="DNL-NOT-FILLED",
        exchange_order_id="201",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.NEW,
        requested_quantity=0.001,
        executed_quantity=0.0,
        side="BUY",
    )

    with pytest.raises(ExecutionSettlementError):
        settlement.settle(order)


def test_buy_then_sell_e2e_returns_flat(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    buy = ExchangeOrder(
        client_order_id="DNL-E2E-SELL-BUY",
        exchange_order_id="300",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100.0,
        side="BUY",
        fee=Decimal("0.001"),
    )

    settlement.settle(buy)

    assert manager.position.state == PositionState.LONG

    sell = ExchangeOrder(
        client_order_id="DNL-E2E-SELL-SELL",
        exchange_order_id="301",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=101.0,
        side="SELL",
        fee=Decimal("0.001"),
    )

    result = settlement.settle(sell)

    assert result.state == PositionState.FLAT
    assert result.quantity == Decimal(0)
    assert result.total_fees == Decimal("0.002")
    assert result.realized_pnl == Decimal("0.998")

    buy_entry = journal.get("DNL-E2E-SELL-BUY")
    sell_entry = journal.get("DNL-E2E-SELL-SELL")

    assert buy_entry is not None
    assert sell_entry is not None

    assert buy_entry.side == "BUY"
    assert sell_entry.side == "SELL"
    assert sell_entry.price == "101000"
    assert sell_entry.fee == "0.001"


def test_sell_settlement_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()
    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    buy = ExchangeOrder(
        client_order_id="DNL-IDEMP-BUY",
        exchange_order_id="400",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100.0,
        side="BUY",
        fee=Decimal("0.001"),
    )

    settlement.settle(buy)

    sell = ExchangeOrder(
        client_order_id="DNL-IDEMP-SELL",
        exchange_order_id="401",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=101.0,
        side="SELL",
        fee=Decimal("0.001"),
    )

    first = settlement.settle(sell)

    pnl_after_first = first.realized_pnl
    fees_after_first = first.total_fees

    second = settlement.settle(sell)

    assert second == first
    assert second.state == PositionState.FLAT
    assert second.quantity == Decimal(0)
    assert second.realized_pnl == pnl_after_first
    assert second.total_fees == fees_after_first

    sell_entry = journal.get("DNL-IDEMP-SELL")
    assert sell_entry is not None
    assert sell_entry.status == "FILLED"


def test_partial_fill_settles_only_executed_quantity(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    order = ExchangeOrder(
        client_order_id="DNL-PARTIAL-SETTLE",
        exchange_order_id="900",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.PARTIALLY_FILLED,
        requested_quantity=0.005,
        executed_quantity=0.002,
        executed_quote_quantity=200,
        side="BUY",
        fee=Decimal("0.001"),
    )

    result = settlement.settle(order)

    assert result.state == PositionState.LONG
    assert result.symbol == "BTCUSDT"
    assert result.quantity == Decimal("0.002")
    assert result.average_entry == Decimal(100000)
    assert result.total_fees == Decimal("0.001")

    entry = journal.get("DNL-PARTIAL-SETTLE")
    assert entry is not None
    assert entry.executed_quantity == "0.002"


def test_partial_fill_settlement_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    order = ExchangeOrder(
        client_order_id="DNL-PARTIAL-IDEMP",
        exchange_order_id="901",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.PARTIALLY_FILLED,
        requested_quantity=0.005,
        executed_quantity=0.002,
        executed_quote_quantity=200,
        side="BUY",
        fee=Decimal("0.001"),
    )

    first = settlement.settle(order)

    assert first.state == PositionState.LONG
    assert first.quantity == Decimal("0.002")

    second = settlement.settle(order)

    assert second == first
    assert second.state == PositionState.LONG
    assert second.quantity == Decimal("0.002")
    assert second.total_fees == Decimal("0.001")

    entry = journal.get("DNL-PARTIAL-IDEMP")
    assert entry is not None
    assert entry.executed_quantity == "0.002"


def test_partial_fill_progression_applies_only_new_delta(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    manager = PositionManager()

    settlement = ExecutionSettlement(
        FillReconciler(journal, manager)
    )

    first = ExchangeOrder(
        client_order_id="DNL-PARTIAL-DELTA",
        exchange_order_id="902",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.PARTIALLY_FILLED,
        requested_quantity=0.005,
        executed_quantity=0.002,
        executed_quote_quantity=200,
        side="BUY",
        fee=Decimal("0.001"),
    )

    settlement.settle(first)

    assert manager.position.quantity == Decimal("0.002")

    second = ExchangeOrder(
        client_order_id="DNL-PARTIAL-DELTA",
        exchange_order_id="902",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.005,
        executed_quantity=0.005,
        executed_quote_quantity=500,
        side="BUY",
        fee=Decimal("0.0025"),
    )

    settlement.settle(second)

    assert manager.position.state == PositionState.LONG
    assert manager.position.quantity == Decimal("0.005")

    # Hanya delta 0.003 yang boleh diterapkan.
    assert manager.position.quantity != Decimal("0.007")

    # Fee harus mengikuti fill yang benar-benar diterapkan.
    assert manager.position.total_fees == Decimal("0.0025")

    entry = journal.get("DNL-PARTIAL-DELTA")
    assert entry is not None
    assert entry.executed_quantity == "0.005"

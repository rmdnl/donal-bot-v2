from decimal import Decimal

import pytest

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
)
from app.portfolio.position_sync import (
    PositionSyncError,
    PositionSynchronizer,
)
from app.position.position_manager import (
    PositionManager,
    PositionState,
)


def _order(
    status: ExchangeOrderStatus,
    executed: float = 0.01,
) -> ExchangeOrder:
    return ExchangeOrder(
        client_order_id="DNL-BTC-001",
        exchange_order_id="123",
        symbol="BTCUSDT",
        status=status,
        requested_quantity=executed,
        executed_quantity=executed,
    )


def test_filled_buy_creates_position():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    sync.apply_buy_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(100000),
    )

    assert manager.position.state == PositionState.LONG
    assert manager.position.quantity == Decimal("0.01")
    assert manager.position.average_entry == Decimal(100000)


def test_non_filled_order_rejected():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    with pytest.raises(PositionSyncError):
        sync.apply_buy_fill(
            _order(ExchangeOrderStatus.NEW),
            Decimal(100000),
        )


def test_zero_fill_rejected():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    with pytest.raises(PositionSyncError):
        sync.apply_buy_fill(
            _order(ExchangeOrderStatus.FILLED, 0),
            Decimal(100000),
        )


def test_filled_sell_reduces_position():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    sync.apply_buy_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(100000),
    )

    sync.apply_sell_fill(
        _order(ExchangeOrderStatus.FILLED, 0.003),
        Decimal(101000),
    )

    assert manager.position.state == PositionState.LONG
    assert manager.position.quantity == Decimal("0.007")
    assert manager.position.realized_pnl == Decimal(3)


def test_filled_sell_closes_position():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    sync.apply_buy_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(100000),
    )

    sync.apply_sell_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(101000),
    )

    assert manager.position.state == PositionState.FLAT
    assert manager.position.quantity == Decimal(0)
    assert manager.position.realized_pnl == Decimal(10)


def test_sell_without_long_position_rejected():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    with pytest.raises(PositionSyncError):
        sync.apply_sell_fill(
            _order(ExchangeOrderStatus.FILLED, 0.01),
            Decimal(101000),
        )


def test_sell_more_than_position_rejected():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    sync.apply_buy_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(100000),
    )

    with pytest.raises(PositionSyncError):
        sync.apply_sell_fill(
            _order(ExchangeOrderStatus.FILLED, 0.02),
            Decimal(101000),
        )


def test_filled_sell_applies_fee_to_pnl_and_total_fees():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    sync.apply_buy_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(100000),
    )

    sync.apply_sell_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(101000),
        fee=Decimal(1),
    )

    assert manager.position.state == PositionState.FLAT
    assert manager.position.quantity == Decimal(0)
    assert manager.position.realized_pnl == Decimal(9)
    assert manager.position.total_fees == Decimal(1)


def test_filled_buy_applies_fee():
    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    sync.apply_buy_fill(
        _order(ExchangeOrderStatus.FILLED, 0.01),
        Decimal(100000),
        fee=Decimal(1),
    )

    assert manager.position.state == PositionState.LONG
    assert manager.position.quantity == Decimal("0.01")
    assert manager.position.average_entry == Decimal(100000)
    assert manager.position.realized_pnl == Decimal(-1)
    assert manager.position.total_fees == Decimal(1)


def test_position_sync_buy_sell_accounting_matches_position_manager():
    buy_price = Decimal(77800)
    sell_price = Decimal(78000)
    quantity = Decimal("0.00010")
    buy_fee = Decimal("0.0001")
    sell_fee = Decimal("0.00003")

    manager = PositionManager()
    sync = PositionSynchronizer(manager)

    sync.apply_buy_fill(
        _order(
            ExchangeOrderStatus.FILLED,
            float(quantity),
        ),
        buy_price,
        fee=buy_fee,
    )

    sync.apply_sell_fill(
        _order(
            ExchangeOrderStatus.FILLED,
            float(quantity),
        ),
        sell_price,
        fee=sell_fee,
    )

    expected_pnl = (
        sell_price - buy_price
    ) * quantity - buy_fee - sell_fee

    assert manager.position.state == PositionState.FLAT
    assert manager.position.quantity == Decimal(0)
    assert manager.position.realized_pnl == expected_pnl
    assert manager.position.total_fees == (
        buy_fee + sell_fee
    )


def test_fill_reconciler_and_position_sync_match_accounting(
    tmp_path,
):
    from app.position.fill_reconciler import (
        Fill,
        FillReconciler,
    )
    from app.storage.trade_journal import TradeJournal

    buy_price = Decimal(77800)
    sell_price = Decimal(78000)
    quantity = Decimal("0.00010")
    buy_fee = Decimal("0.0001")
    sell_fee = Decimal("0.00003")

    # Path A: FillReconciler
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    reconciler_manager = PositionManager()
    reconciler = FillReconciler(
        journal,
        reconciler_manager,
    )

    reconciler.reconcile(
        Fill(
            client_order_id="DNL-CROSS-BUY",
            symbol="BTCUSDT",
            side="BUY",
            quantity=quantity,
            executed_quantity=quantity,
            price=buy_price,
            fee=buy_fee,
            status="FILLED",
        )
    )

    reconciler_result = reconciler.reconcile(
        Fill(
            client_order_id="DNL-CROSS-SELL",
            symbol="BTCUSDT",
            side="SELL",
            quantity=quantity,
            executed_quantity=quantity,
            price=sell_price,
            fee=sell_fee,
            status="FILLED",
        )
    )

    # Path B: PositionSynchronizer
    sync_manager = PositionManager()
    sync = PositionSynchronizer(sync_manager)

    sync.apply_buy_fill(
        _order(
            ExchangeOrderStatus.FILLED,
            float(quantity),
        ),
        buy_price,
        fee=buy_fee,
    )

    sync.apply_sell_fill(
        _order(
            ExchangeOrderStatus.FILLED,
            float(quantity),
        ),
        sell_price,
        fee=sell_fee,
    )

    sync_result = sync_manager.position

    assert sync_result.state == reconciler_result.state
    assert sync_result.quantity == reconciler_result.quantity
    assert sync_result.realized_pnl == (
        reconciler_result.realized_pnl
    )
    assert sync_result.total_fees == (
        reconciler_result.total_fees
    )

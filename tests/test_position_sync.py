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

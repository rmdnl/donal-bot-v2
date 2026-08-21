from decimal import Decimal

import pytest

from app.position.position_manager import (
    PositionError,
    PositionManager,
    PositionState,
)


def test_enter_long():
    manager = PositionManager()

    position = manager.enter(
        "BTCUSDT",
        Decimal("0.01"),
        Decimal(100000),
    )

    assert position.state == PositionState.LONG
    assert position.quantity == Decimal("0.01")
    assert position.average_entry == Decimal(100000)


def test_exit_calculates_profit():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.01"),
        Decimal(100000),
    )

    position = manager.exit(
        Decimal("0.01"),
        Decimal(101000),
    )

    assert position.state == PositionState.FLAT
    assert position.realized_pnl == Decimal(10)


def test_cannot_enter_twice():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.01"),
        Decimal(100000),
    )

    with pytest.raises(PositionError):
        manager.enter(
            "BTCUSDT",
            Decimal("0.01"),
            Decimal(101000),
        )


def test_cannot_exit_more_than_position():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.01"),
        Decimal(100000),
    )

    with pytest.raises(PositionError):
        manager.exit(
            Decimal("0.02"),
            Decimal(101000),
        )

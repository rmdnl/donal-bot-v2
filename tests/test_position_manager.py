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


def test_partial_exit_realized_pnl():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.008"),
        Decimal(100000),
    )

    position = manager.exit(
        Decimal("0.003"),
        Decimal(101000),
    )

    assert position.state == PositionState.LONG
    assert position.quantity == Decimal("0.005")
    assert position.realized_pnl == Decimal(3)


def test_multiple_partial_exits_accumulate_pnl():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.010"),
        Decimal(100000),
    )

    manager.exit(
        Decimal("0.003"),
        Decimal(101000),
    )

    position = manager.exit(
        Decimal("0.002"),
        Decimal(99000),
    )

    assert position.quantity == Decimal("0.005")
    assert position.realized_pnl == Decimal(1)


def test_full_exit_preserves_realized_pnl():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.010"),
        Decimal(100000),
    )

    position = manager.exit(
        Decimal("0.010"),
        Decimal(101000),
    )

    assert position.state == PositionState.FLAT
    assert position.quantity == Decimal(0)
    assert position.realized_pnl == Decimal(10)

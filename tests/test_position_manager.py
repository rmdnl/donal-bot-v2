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


def test_entry_fee_reduces_realized_pnl():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.01"),
        Decimal(100000),
        fee=Decimal(1),
    )

    position = manager.exit(
        Decimal("0.01"),
        Decimal(101000),
        fee=Decimal(1),
    )

    assert position.state == PositionState.FLAT
    assert position.realized_pnl == Decimal(8)
    assert position.total_fees == Decimal(2)


def test_negative_fee_rejected():
    manager = PositionManager()

    with pytest.raises(PositionError):
        manager.enter(
            "BTCUSDT",
            Decimal("0.01"),
            Decimal(100000),
            fee=Decimal(-1),
        )


def test_restore_long_position():
    manager = PositionManager()

    position = manager.restore(
        symbol="BTCUSDT",
        quantity=Decimal("0.008"),
        average_entry=Decimal(100000),
        realized_pnl=Decimal(3),
    )

    assert position.state == PositionState.LONG
    assert position.symbol == "BTCUSDT"
    assert position.quantity == Decimal("0.008")
    assert position.average_entry == Decimal(100000)
    assert position.realized_pnl == Decimal(3)


def test_restore_rejects_empty_position():
    manager = PositionManager()

    with pytest.raises(PositionError):
        manager.restore(
            symbol="BTCUSDT",
            quantity=Decimal(0),
            average_entry=Decimal(100000),
        )


def test_restore_rejects_invalid_price():
    manager = PositionManager()

    with pytest.raises(PositionError):
        manager.restore(
            symbol="BTCUSDT",
            quantity=Decimal("0.008"),
            average_entry=Decimal(0),
        )

def test_full_exit_with_fee_closes_position_safely():
    manager = PositionManager()

    manager.enter(
        "BTCUSDT",
        Decimal("0.00007"),
        Decimal("77857.73"),
        fee=Decimal("0.00000007"),
    )

    position = manager.exit(
        Decimal("0.00007"),
        Decimal("77814.33"),
        fee=Decimal("0.00544700"),
    )

    assert position.state == PositionState.FLAT
    assert position.quantity == Decimal(0)
    assert position.average_entry == Decimal(0)
    assert position.total_fees == (
        Decimal("0.00000007")
        + Decimal("0.00544700")
    )
    assert position.realized_pnl < Decimal(0)

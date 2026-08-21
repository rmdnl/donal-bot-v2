import pytest

from app.execution.order_manager import (
    OrderManager,
    OrderManagerError,
    OrderState,
)


def test_full_entry_lifecycle():
    manager = OrderManager()

    order = manager.create_entry(
        client_order_id="donal-BTCUSDT-001",
        symbol="BTCUSDT",
        quantity=1.0,
    )

    assert order.state == OrderState.ENTRY_PENDING

    manager.acknowledge(
        "donal-BTCUSDT-001",
        "exchange-123",
    )

    manager.update_fill(
        "donal-BTCUSDT-001",
        1.0,
    )

    assert order.state == OrderState.FILLED_UNPROTECTED

    manager.mark_protected(
        "donal-BTCUSDT-001",
    )

    assert order.state == OrderState.PROTECTED

    manager.begin_exit(
        "donal-BTCUSDT-001",
    )

    assert order.state == OrderState.EXIT_PENDING

    manager.close(
        "donal-BTCUSDT-001",
    )

    assert order.state == OrderState.CLOSED


def test_partial_fill():
    manager = OrderManager()

    order = manager.create_entry(
        client_order_id="donal-SOLUSDT-001",
        symbol="SOLUSDT",
        quantity=10.0,
    )

    manager.update_fill(
        "donal-SOLUSDT-001",
        4.0,
    )

    assert order.state == OrderState.PARTIALLY_FILLED
    assert order.filled_quantity == 4.0
    assert order.remaining_quantity == 6.0


def test_duplicate_client_order_id_rejected():
    manager = OrderManager()

    manager.create_entry(
        client_order_id="same-id",
        symbol="BTCUSDT",
        quantity=1.0,
    )

    with pytest.raises(OrderManagerError):
        manager.create_entry(
            client_order_id="same-id",
            symbol="BTCUSDT",
            quantity=1.0,
        )


def test_overfill_rejected():
    manager = OrderManager()

    manager.create_entry(
        client_order_id="overfill",
        symbol="BTCUSDT",
        quantity=1.0,
    )

    with pytest.raises(OrderManagerError):
        manager.update_fill(
            "overfill",
            1.1,
        )


def test_invalid_protection_transition():
    manager = OrderManager()

    manager.create_entry(
        client_order_id="invalid",
        symbol="BTCUSDT",
        quantity=1.0,
    )

    with pytest.raises(OrderManagerError):
        manager.mark_protected("invalid")


def test_recovery_state():
    manager = OrderManager()

    order = manager.create_entry(
        client_order_id="recovery",
        symbol="BTCUSDT",
        quantity=1.0,
    )

    manager.recovery("recovery")

    assert order.state == OrderState.ERROR_RECOVERY


def test_invalid_quantity():
    manager = OrderManager()

    with pytest.raises(OrderManagerError):
        manager.create_entry(
            client_order_id="bad",
            symbol="BTCUSDT",
            quantity=0,
        )

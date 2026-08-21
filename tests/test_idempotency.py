import pytest

from app.execution.idempotency import (
    IdempotencyError,
    make_client_order_id,
)


def test_same_signal_same_id():
    a = make_client_order_id("BTCUSDT", "signal-001")
    b = make_client_order_id("BTCUSDT", "signal-001")

    assert a == b


def test_different_signal_different_id():
    a = make_client_order_id("BTCUSDT", "signal-001")
    b = make_client_order_id("BTCUSDT", "signal-002")

    assert a != b


def test_symbol_normalized():
    a = make_client_order_id("btcusdt", "signal-001")
    b = make_client_order_id("BTCUSDT", "signal-001")

    assert a == b


def test_empty_signal_rejected():
    with pytest.raises(IdempotencyError):
        make_client_order_id("BTCUSDT", "")


def test_invalid_symbol_rejected():
    with pytest.raises(IdempotencyError):
        make_client_order_id("BTC-USDT", "signal-001")

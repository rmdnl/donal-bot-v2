from __future__ import annotations

from unittest.mock import patch

from app.config.settings import Settings
from app.exchange.binance_orders import BinanceOrderClient


def _client() -> BinanceOrderClient:
    return BinanceOrderClient(
        Settings(
            binance_api_key="test-key",
            binance_api_secret="test-secret",
        )
    )


def test_market_buy_uses_post() -> None:
    client = _client()

    with patch.object(
        client,
        "_request",
        return_value={"orderId": 123},
    ) as request:
        result = client.place_market_buy(
            "BTCUSDT",
            "0.001",
            "donal-test-001",
        )

    assert result["orderId"] == 123
    request.assert_called_once_with(
        "POST",
        "/api/v3/order",
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "0.001",
            "newClientOrderId": "donal-test-001",
        },
    )


def test_get_order_uses_get() -> None:
    client = _client()

    with patch.object(
        client,
        "_request",
        return_value={"status": "FILLED"},
    ) as request:
        result = client.get_order(
            "BTCUSDT",
            "donal-test-001",
        )

    assert result["status"] == "FILLED"
    request.assert_called_once_with(
        "GET",
        "/api/v3/order",
        {
            "symbol": "BTCUSDT",
            "origClientOrderId": "donal-test-001",
        },
    )


def test_cancel_order_uses_delete() -> None:
    client = _client()

    with patch.object(
        client,
        "_request",
        return_value={"status": "CANCELED"},
    ) as request:
        result = client.cancel_order(
            "BTCUSDT",
            "donal-test-001",
        )

    assert result["status"] == "CANCELED"
    request.assert_called_once_with(
        "DELETE",
        "/api/v3/order",
        {
            "symbol": "BTCUSDT",
            "origClientOrderId": "donal-test-001",
        },
    )


def test_market_buy_rejects_invalid_quantity() -> None:
    client = _client()

    try:
        client.place_market_buy(
            "BTCUSDT",
            "abc",
            "donal-test-001",
        )
    except ValueError as exc:
        assert "numeric" in str(exc)
    else:
        raise AssertionError("Expected invalid quantity error")


def test_market_buy_rejects_zero_quantity() -> None:
    client = _client()

    try:
        client.place_market_buy(
            "BTCUSDT",
            "0",
            "donal-test-001",
        )
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("Expected positive quantity error")

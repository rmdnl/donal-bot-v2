from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config.settings import Settings
from app.exchange.binance_orders import BinanceOrderClient, BinanceOrderError


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


def test_reconcile_order_returns_found() -> None:
    client = _client()

    with patch.object(
        client,
        "get_order",
        return_value={
            "orderId": 123,
            "status": "FILLED",
            "clientOrderId": "donal-test-001",
        },
    ) as get_order:
        result = client.reconcile_order(
            "BTCUSDT",
            "donal-test-001",
        )

    assert result.status == "FOUND"
    assert result.order_id == 123
    assert result.raw["status"] == "FILLED"

    get_order.assert_called_once_with(
        "BTCUSDT",
        "donal-test-001",
    )


def test_reconcile_order_returns_not_found() -> None:
    client = _client()

    with patch.object(
        client,
        "get_order",
        side_effect=BinanceOrderError(
            "Binance order HTTP 400: Unknown order sent. (code -2013)"
        ),
    ):
        result = client.reconcile_order(
            "BTCUSDT",
            "donal-test-001",
        )

    assert result.status == "NOT_FOUND"
    assert result.order_id is None


def test_reconcile_order_does_not_hide_unknown_error() -> None:
    client = _client()

    with patch.object(
        client,
        "get_order",
        side_effect=BinanceOrderError(
            "Binance order transport error: timeout"
        ),
    ):
        try:
            client.reconcile_order(
                "BTCUSDT",
                "donal-test-001",
            )
        except BinanceOrderError as exc:
            assert "transport error" in str(exc)
        else:
            raise AssertionError(
                "Expected transport error to propagate"
            )


def test_place_market_sell_builds_sell_market_order():
    from unittest.mock import patch

    settings = Settings(
        binance_api_key="test-key",
        binance_api_secret="test-secret",
    )
    client = BinanceOrderClient(settings)

    expected = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "MARKET",
        "quantity": "0.00007000",
        "newClientOrderId": "DNL-SELL-TEST-001",
    }

    with patch.object(
        client,
        "_request",
        return_value={"status": "FILLED"},
    ) as request:
        result = client.place_market_sell(
            "BTCUSDT",
            "0.00007000",
            "DNL-SELL-TEST-001",
        )

    assert result["status"] == "FILLED"
    request.assert_called_once_with(
        "POST",
        "/api/v3/order",
        expected,
    )


def test_request_timeout_raises_timeout_error(monkeypatch):
    client = _client()

    def fake_urlopen(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(
        "app.exchange.binance_orders.urlopen",
        fake_urlopen,
    )

    with pytest.raises(TimeoutError):
        client._request(
            "POST",
            "/api/v3/order",
            {
                "symbol": "BTCUSDT",
                "side": "SELL",
                "type": "MARKET",
                "quantity": "0.01",
                "newClientOrderId": "DNL-TIMEOUT-001",
            },
        )



def test_request_socket_timeout_reaches_reconciliation(monkeypatch):

    client = _client()

    def fake_urlopen(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(
        "app.exchange.binance_orders.urlopen",
        fake_urlopen,
    )

    with pytest.raises(TimeoutError):
        client._request(
            "POST",
            "/api/v3/order",
            {
                "symbol": "BTCUSDT",
                "side": "SELL",
                "type": "MARKET",
                "quantity": "0.01",
                "newClientOrderId": "DNL-SOCKET-TIMEOUT-001",
            },
        )


def test_request_urlerror_remains_binance_order_error(monkeypatch):
    from urllib.error import URLError

    client = _client()

    def fake_urlopen(*args, **kwargs):
        raise URLError("connection failed")

    monkeypatch.setattr(
        "app.exchange.binance_orders.urlopen",
        fake_urlopen,
    )

    with pytest.raises(BinanceOrderError) as exc:
        client._request(
            "POST",
            "/api/v3/order",
            {
                "symbol": "BTCUSDT",
                "side": "SELL",
                "type": "MARKET",
                "quantity": "0.01",
                "newClientOrderId": "DNL-URLERROR-001",
            },
        )

    assert "transport error" in str(exc.value)

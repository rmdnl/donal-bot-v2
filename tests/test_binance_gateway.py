from __future__ import annotations

from unittest.mock import patch

from app.config.settings import Settings
from app.exchange.binance_gateway import BinanceGateway


def test_server_time() -> None:
    gateway = BinanceGateway(Settings())

    with patch(
        "app.exchange.binance_gateway.BinanceClient.get",
        return_value={"serverTime": 1234567890},
    ):
        assert gateway.server_time() == 1234567890


def test_sync_time() -> None:
    gateway = BinanceGateway(Settings())

    with patch.object(
        gateway,
        "server_time",
        return_value=1_000_000,
    ), patch(
        "app.exchange.binance_gateway.time.time",
        return_value=999.9,
    ):
        offset = gateway.sync_time()

    assert offset == 100


def test_account_requires_credentials() -> None:
    gateway = BinanceGateway(Settings())

    try:
        gateway.account()
    except ValueError as exc:
        assert "BINANCE_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing API key error")

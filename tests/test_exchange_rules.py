from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.exchange.binance_client import BinanceClient
from app.exchange.exchange_rules import (
    ExchangeRulesError,
    ExchangeRulesLoader,
)


def payload():
    return {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "filters": [
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "0.00001000",
                        "maxQty": "9000.00000000",
                        "stepSize": "0.00001000",
                    },
                    {
                        "filterType": "NOTIONAL",
                        "minNotional": "5.00000000",
                    },
                ],
            }
        ]
    }


def test_loads_symbol_rules():
    client = Mock(spec=BinanceClient)
    client.get.return_value = payload()

    result = ExchangeRulesLoader(client).load("btcusdt")

    assert result.symbol == "BTCUSDT"
    assert result.min_qty == Decimal("0.00001000")
    assert result.step_size == Decimal("0.00001000")
    assert result.min_notional == Decimal("5.00000000")


def test_invalid_symbol_rejected():
    with pytest.raises(ExchangeRulesError):
        ExchangeRulesLoader(
            Mock(spec=BinanceClient)
        ).load("")


def test_missing_symbol_rejected():
    client = Mock(spec=BinanceClient)
    client.get.return_value = {"symbols": []}

    with pytest.raises(ExchangeRulesError):
        ExchangeRulesLoader(client).load("BTCUSDT")


def test_missing_lot_size_rejected():
    client = Mock(spec=BinanceClient)

    data = payload()
    data["symbols"][0]["filters"] = [
        {
            "filterType": "NOTIONAL",
            "minNotional": "5",
        }
    ]

    client.get.return_value = data

    with pytest.raises(ExchangeRulesError):
        ExchangeRulesLoader(client).load("BTCUSDT")

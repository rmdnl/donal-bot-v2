from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.exchange.binance_orders import BinanceOrderClient
from app.exchange.order_validator import SymbolRules
from app.execution.safe_order_executor import (
    SafeOrderError,
    SafeOrderExecutor,
)

RULES = SymbolRules(
    min_qty=Decimal("0.00001"),
    step_size=Decimal("0.00001"),
    min_notional=Decimal(5),
)


def test_dry_run_validates_without_order():
    client = Mock(spec=BinanceOrderClient)

    executor = SafeOrderExecutor(
        client,
        dry_run=True,
    )

    result = executor.buy(
        symbol="BTCUSDT",
        quantity=Decimal("0.001"),
        price=Decimal(100000),
        rules=RULES,
        client_order_id="DNL-001",
    )

    assert result.symbol == "BTCUSDT"
    assert result.quantity == Decimal("0.001")
    assert result.notional == Decimal(100)
    assert result.order is None

    client.place_market_buy.assert_not_called()


def test_invalid_order_never_reaches_exchange():
    client = Mock(spec=BinanceOrderClient)

    executor = SafeOrderExecutor(
        client,
        dry_run=False,
    )

    with pytest.raises(SafeOrderError):
        executor.buy(
            symbol="BTCUSDT",
            quantity=Decimal("0.00001"),
            price=Decimal(100000),
            rules=RULES,
            client_order_id="DNL-002",
        )

    client.place_market_buy.assert_not_called()


def test_valid_live_order_reaches_exchange():
    client = Mock(spec=BinanceOrderClient)

    client.place_market_buy.return_value = {
        "symbol": "BTCUSDT",
        "status": "FILLED",
        "orderId": 123,
    }

    executor = SafeOrderExecutor(
        client,
        dry_run=False,
    )

    result = executor.buy(
        symbol="BTCUSDT",
        quantity=Decimal("0.00123"),
        price=Decimal(100000),
        rules=RULES,
        client_order_id="DNL-003",
    )

    assert result.quantity == Decimal("0.00123")
    assert result.order["status"] == "FILLED"

    client.place_market_buy.assert_called_once_with(
        symbol="BTCUSDT",
        quantity="0.00123",
        client_order_id="DNL-003",
    )

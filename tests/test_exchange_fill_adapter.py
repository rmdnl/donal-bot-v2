from decimal import Decimal

import pytest

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
)
from app.position.exchange_fill_adapter import (
    ExchangeFillAdapter,
    ExchangeFillAdapterError,
)


def test_exchange_order_to_buy_fill():
    order = ExchangeOrder(
        client_order_id="DNL-BUY-FILL-001",
        exchange_order_id="100",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100.0,
        side="BUY",
        fee=0.001,
    )

    fill = ExchangeFillAdapter().from_order(order)

    assert fill.client_order_id == "DNL-BUY-FILL-001"
    assert fill.symbol == "BTCUSDT"
    assert fill.side == "BUY"
    assert fill.quantity == Decimal("0.001")
    assert fill.executed_quantity == Decimal("0.001")
    assert fill.price == Decimal(100000)
    assert fill.fee == Decimal("0.001")
    assert fill.status == "FILLED"


def test_exchange_order_to_sell_fill():
    order = ExchangeOrder(
        client_order_id="DNL-SELL-FILL-001",
        exchange_order_id="101",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=99.5,
        side="SELL",
        fee=0.002,
    )

    fill = ExchangeFillAdapter().from_order(order)

    assert fill.side == "SELL"
    assert fill.price == Decimal(99500)
    assert fill.fee == Decimal("0.002")


def test_non_filled_order_rejected():
    order = ExchangeOrder(
        client_order_id="DNL-NEW-001",
        exchange_order_id="102",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.NEW,
        requested_quantity=0.001,
        executed_quantity=0.0,
        side="BUY",
    )

    with pytest.raises(ExchangeFillAdapterError):
        ExchangeFillAdapter().from_order(order)


def test_invalid_side_rejected():
    order = ExchangeOrder(
        client_order_id="DNL-BAD-SIDE",
        exchange_order_id="103",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100,
        side="HOLD",
    )

    with pytest.raises(ExchangeFillAdapterError):
        ExchangeFillAdapter().from_order(order)

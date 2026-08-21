from decimal import Decimal

import pytest

from app.position.binance_fill_adapter import (
    BinanceFillAdapter,
    BinanceFillAdapterError,
)

ORDER = {
    "symbol": "BTCUSDT",
    "orderId": 5567361,
    "clientOrderId": "DNL-TEST-121566739C0A",
    "origQty": "0.00007000",
    "executedQty": "0.00007000",
    "cummulativeQuoteQty": "5.45004110",
    "status": "FILLED",
    "side": "BUY",
    "fills": [
        {
            "price": "77857.73",
            "qty": "0.00007000",
            "commission": "0.00000007",
            "commissionAsset": "BTC",
        }
    ],
}


def test_converts_binance_order_to_fill():
    fill = BinanceFillAdapter().from_order(ORDER)

    assert fill.client_order_id == (
        "DNL-TEST-121566739C0A"
    )
    assert fill.symbol == "BTCUSDT"
    assert fill.side == "BUY"
    assert fill.status == "FILLED"
    assert fill.quantity == Decimal("0.00007000")
    assert fill.executed_quantity == Decimal("0.00007000")
    assert fill.price == Decimal("77857.73")
    assert fill.fee == Decimal("0.0054500411")


def test_multiple_fills_are_aggregated():
    order = {
        **ORDER,
        "executedQty": "0.00010",
        "cummulativeQuoteQty": "7.8",
        "origQty": "0.00010",
        "fills": [
            {
                "price": "78000",
                "qty": "0.00005",
                "commission": "0.00000005",
                "commissionAsset": "BTC",
            },
            {
                "price": "78000",
                "qty": "0.00005",
                "commission": "0.00000005",
                "commissionAsset": "BTC",
            },
        ],
    }

    fill = BinanceFillAdapter().from_order(order)

    assert fill.price == Decimal(78000)
    assert fill.fee == Decimal("0.00780000")


def test_invalid_order_rejected():
    with pytest.raises(BinanceFillAdapterError):
        BinanceFillAdapter().from_order({})


def test_zero_executed_quantity_rejected():
    order = {
        **ORDER,
        "executedQty": "0",
    }

    with pytest.raises(BinanceFillAdapterError):
        BinanceFillAdapter().from_order(order)


def test_sell_fee_in_quote_asset_is_not_multiplied():
    order = {
        **ORDER,
        "side": "SELL",
        "fills": [
            {
                "price": "77857.73",
                "qty": "0.00007000",
                "commission": "0.00545004",
                "commissionAsset": "USDT",
            }
        ],
    }

    fill = BinanceFillAdapter().from_order(order)

    assert fill.fee == Decimal("0.00545004")


def test_base_asset_fee_is_converted_to_quote():
    order = {
        **ORDER,
        "side": "SELL",
        "fills": [
            {
                "price": "77857.73",
                "qty": "0.00007000",
                "commission": "0.00000007",
                "commissionAsset": "BTC",
            }
        ],
    }

    fill = BinanceFillAdapter().from_order(order)

    assert fill.fee == Decimal("0.0054500411")


def test_unsupported_fee_asset_is_rejected():
    order = {
        **ORDER,
        "fills": [
            {
                "price": "77857.73",
                "qty": "0.00007000",
                "commission": "0.01",
                "commissionAsset": "BNB",
            }
        ],
    }

    with pytest.raises(BinanceFillAdapterError):
        BinanceFillAdapter().from_order(order)

from decimal import Decimal

from app.position.binance_fill_adapter import BinanceFillAdapter
from app.position.position_manager import PositionManager

BUY_ORDER = {
    "symbol": "BTCUSDT",
    "clientOrderId": "DNL-TEST-121566739C0A",
    "origQty": "0.00007000",
    "executedQty": "0.00007000",
    "cummulativeQuoteQty": "5.45004110",
    "status": "FILLED",
    "side": "BUY",
    "fills": [
        {
            "price": "77857.73000000",
            "qty": "0.00007000",
            "commission": "0.00000007",
            "commissionAsset": "BTC",
        }
    ],
}

SELL_ORDER = {
    "symbol": "BTCUSDT",
    "clientOrderId": "DNL-SELL-TEST-001",
    "origQty": "0.00007000",
    "executedQty": "0.00007000",
    "cummulativeQuoteQty": "5.44700310",
    "status": "FILLED",
    "side": "SELL",
    "fills": [
        {
            "price": "77814.33000000",
            "qty": "0.00007000",
            "commission": "0.00544700",
            "commissionAsset": "USDT",
        }
    ],
}


def test_buy_sell_returns_position_to_flat():
    adapter = BinanceFillAdapter()
    manager = PositionManager()

    buy = adapter.from_order(BUY_ORDER)

    position = manager.enter(
        symbol=buy.symbol,
        quantity=buy.executed_quantity,
        price=buy.price,
        fee=buy.fee,
    )

    assert position.quantity == Decimal("0.00007000")
    assert position.state.value == "LONG"

    sell = adapter.from_order(SELL_ORDER)

    position = manager.exit(
        quantity=sell.executed_quantity,
        price=sell.price,
        fee=sell.fee,
    )

    assert position.state.value == "FLAT"
    assert position.quantity == Decimal(0)
    assert position.realized_pnl < Decimal(0)
    assert position.total_fees > Decimal(0)

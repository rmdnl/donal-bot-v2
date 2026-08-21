from app.exchange.binance_execution_gateway import (
    BinanceExecutionGateway,
)
from app.execution.execution_adapter import (
    ExchangeOrderStatus,
)


class FakeClient:
    def place_market_buy(self, **kwargs):
        return {
            "symbol": "BTCUSDT",
            "orderId": 123,
            "clientOrderId": kwargs["client_order_id"],
            "status": "FILLED",
            "side": "BUY",
            "origQty": "0.001",
            "executedQty": "0.001",
            "cummulativeQuoteQty": "100.50",
            "fills": [
                {
                    "price": "100500",
                    "qty": "0.001",
                    "commission": "0.000001",
                }
            ],
        }

    def place_market_sell(self, **kwargs):
        return self.place_market_buy(**kwargs) | {
            "side": "SELL",
        }

    def get_order(self, **kwargs):
        return self.place_market_buy(
            client_order_id=kwargs["client_order_id"]
        )


def test_buy_maps_binance_response_to_exchange_order():
    gateway = BinanceExecutionGateway(FakeClient())

    order = gateway.place_market_buy(
        "BTCUSDT",
        0.001,
        "DNL-BTCUSDT-test",
    )

    assert order.symbol == "BTCUSDT"
    assert order.client_order_id == "DNL-BTCUSDT-test"
    assert order.exchange_order_id == "123"
    assert order.status == ExchangeOrderStatus.FILLED
    assert order.executed_quantity == 0.001
    assert order.executed_quote_quantity == 100.50
    assert order.side == "BUY"

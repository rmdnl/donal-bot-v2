from __future__ import annotations

from decimal import Decimal

from app.exchange.binance_orders import BinanceOrderClient
from app.execution.execution_adapter import (
    ExchangeGateway,
    ExchangeOrder,
    ExchangeOrderStatus,
)


class BinanceExecutionGateway(ExchangeGateway):
    def __init__(self, client: BinanceOrderClient) -> None:
        self.client = client

    @staticmethod
    def _status(value: str | None) -> ExchangeOrderStatus:
        try:
            return ExchangeOrderStatus(value or "UNKNOWN")
        except ValueError:
            return ExchangeOrderStatus.UNKNOWN

    @staticmethod
    def _float(value) -> float:
        try:
            return float(Decimal(str(value)))
        except (TypeError, ValueError, ArithmeticError):
            return 0.0

    @classmethod
    def _from_response(cls, payload: dict) -> ExchangeOrder:
        fills = payload.get("fills") or []

        executed_quantity = cls._float(
            payload.get("executedQty", "0")
        )
        quote_quantity = cls._float(
            payload.get("cummulativeQuoteQty", "0")
        )

        fee = 0.0
        if fills:
            fee = sum(
                cls._float(fill.get("commission", "0"))
                for fill in fills
            )

        return ExchangeOrder(
            client_order_id=str(
                payload.get("clientOrderId", "")
            ),
            exchange_order_id=str(
                payload.get("orderId", "")
            ),
            symbol=str(
                payload.get("symbol", "")
            ).upper(),
            status=cls._status(
                payload.get("status")
            ),
            requested_quantity=cls._float(
                payload.get("origQty", "0")
            ),
            executed_quantity=executed_quantity,
            executed_quote_quantity=quote_quantity,
            side=str(
                payload.get("side", "")
            ).upper(),
            fee=fee,
        )

    def place_market_buy(
        self,
        symbol: str,
        quantity: float,
        client_order_id: str,
    ) -> ExchangeOrder:
        payload = self.client.place_market_buy(
            symbol=symbol,
            quantity=str(quantity),
            client_order_id=client_order_id,
        )
        return self._from_response(payload)

    def place_market_sell(
        self,
        symbol: str,
        quantity: float,
        client_order_id: str,
    ) -> ExchangeOrder:
        payload = self.client.place_market_sell(
            symbol=symbol,
            quantity=str(quantity),
            client_order_id=client_order_id,
        )
        return self._from_response(payload)

    def get_order(
        self,
        symbol: str,
        client_order_id: str,
    ) -> ExchangeOrder:
        payload = self.client.get_order(
            symbol=symbol,
            client_order_id=client_order_id,
        )
        return self._from_response(payload)

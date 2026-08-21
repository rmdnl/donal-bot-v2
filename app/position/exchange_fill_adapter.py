from __future__ import annotations

from decimal import Decimal

from app.execution.execution_adapter import ExchangeOrder
from app.position.fill_reconciler import Fill


class ExchangeFillAdapterError(ValueError):
    pass


class ExchangeFillAdapter:
    def from_order(
        self,
        order: ExchangeOrder,
    ) -> Fill:
        if not isinstance(order, ExchangeOrder):
            raise ExchangeFillAdapterError(
                "order must be an ExchangeOrder"
            )

        if order.status.value not in {
            "FILLED",
            "PARTIALLY_FILLED",
        }:
            raise ExchangeFillAdapterError(
                "order has no executable fill"
            )

        if not order.client_order_id:
            raise ExchangeFillAdapterError(
                "client_order_id is required"
            )

        if not order.symbol:
            raise ExchangeFillAdapterError(
                "symbol is required"
            )

        side = order.side.upper().strip()
        if side not in {"BUY", "SELL"}:
            raise ExchangeFillAdapterError(
                "unsupported order side"
            )

        quantity = Decimal(str(order.requested_quantity))
        executed_quantity = Decimal(
            str(order.executed_quantity)
        )
        price = Decimal(
            str(order.average_fill_price)
        )
        fee = Decimal(str(order.fee))

        if quantity <= 0:
            raise ExchangeFillAdapterError(
                "quantity must be positive"
            )

        if executed_quantity <= 0:
            raise ExchangeFillAdapterError(
                "executed quantity must be positive"
            )

        if price <= 0:
            raise ExchangeFillAdapterError(
                "average fill price must be positive"
            )

        if fee < 0:
            raise ExchangeFillAdapterError(
                "fee cannot be negative"
            )

        return Fill(
            client_order_id=order.client_order_id,
            symbol=order.symbol.upper(),
            side=side,
            quantity=quantity,
            executed_quantity=executed_quantity,
            price=price,
            fee=fee,
            status=(
                "FILLED"
                if order.status.value == "PARTIALLY_FILLED"
                and order.executed_quantity > 0
                else order.status.value
            ),
        )

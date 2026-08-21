from __future__ import annotations

from decimal import Decimal

from app.position.fill_reconciler import Fill


class BinanceFillAdapterError(ValueError):
    pass


class BinanceFillAdapter:
    def from_order(self, order: dict) -> Fill:
        if not isinstance(order, dict):
            raise BinanceFillAdapterError(
                "order must be a dictionary"
            )

        symbol = order.get("symbol")
        side = order.get("side")
        status = order.get("status")
        client_order_id = order.get("clientOrderId")

        if not all(
            isinstance(value, str) and value
            for value in (
                symbol,
                side,
                status,
                client_order_id,
            )
        ):
            raise BinanceFillAdapterError(
                "invalid order identity fields"
            )

        try:
            quantity = Decimal(str(order["origQty"]))
            executed_quantity = Decimal(
                str(order["executedQty"])
            )
            quote_quantity = Decimal(
                str(order["cummulativeQuoteQty"])
            )
        except (KeyError, ValueError) as exc:
            raise BinanceFillAdapterError(
                "invalid order quantity fields"
            ) from exc

        if executed_quantity <= 0:
            raise BinanceFillAdapterError(
                "executed quantity must be positive"
            )

        if quote_quantity <= 0:
            raise BinanceFillAdapterError(
                "quote quantity must be positive"
            )

        price = quote_quantity / executed_quantity

        fills = order.get("fills", [])

        if not isinstance(fills, list):
            raise BinanceFillAdapterError(
                "fills must be a list"
            )

        fee_quote = Decimal(0)

        for fill in fills:
            if not isinstance(fill, dict):
                raise BinanceFillAdapterError(
                    "invalid fill"
                )

            try:
                commission = Decimal(
                    str(fill["commission"])
                )
                fill_price = Decimal(
                    str(fill["price"])
                )
            except (KeyError, ValueError) as exc:
                raise BinanceFillAdapterError(
                    "invalid commission data"
                ) from exc

            if commission < 0 or fill_price <= 0:
                raise BinanceFillAdapterError(
                    "invalid commission value"
                )

            fee_quote += commission * fill_price

        return Fill(
            client_order_id=client_order_id,
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            executed_quantity=executed_quantity,
            price=price,
            fee=fee_quote,
            status=status,
        )

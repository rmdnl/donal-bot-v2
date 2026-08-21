from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.exchange.binance_orders import BinanceOrderClient
from app.exchange.order_validator import (
    OrderValidationError,
    OrderValidator,
    SymbolRules,
)


class SafeOrderError(RuntimeError):
    pass


@dataclass(frozen=True)
class SafeOrderResult:
    symbol: str
    quantity: Decimal
    notional: Decimal
    order: dict | None


class SafeOrderExecutor:
    def __init__(
        self,
        order_client: BinanceOrderClient,
        validator: OrderValidator | None = None,
        dry_run: bool = True,
    ) -> None:
        self.order_client = order_client
        self.validator = validator or OrderValidator()
        self.dry_run = dry_run

    def sell(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        rules: SymbolRules,
        client_order_id: str,
    ) -> SafeOrderResult:
        try:
            validated = self.validator.validate(
                quantity=quantity,
                price=price,
                rules=rules,
            )
        except OrderValidationError as exc:
            raise SafeOrderError(str(exc)) from exc

        if self.dry_run:
            return SafeOrderResult(
                symbol=symbol.upper(),
                quantity=validated.quantity,
                notional=validated.notional,
                order=None,
            )

        order = self.order_client.place_market_sell(
            symbol=symbol.upper(),
            quantity=str(validated.quantity),
            client_order_id=client_order_id,
        )

        return SafeOrderResult(
            symbol=symbol.upper(),
            quantity=validated.quantity,
            notional=validated.notional,
            order=order,
        )

    def buy(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        rules: SymbolRules,
        client_order_id: str,
    ) -> SafeOrderResult:
        try:
            validated = self.validator.validate(
                quantity=quantity,
                price=price,
                rules=rules,
            )
        except OrderValidationError as exc:
            raise SafeOrderError(str(exc)) from exc

        if self.dry_run:
            return SafeOrderResult(
                symbol=symbol.upper(),
                quantity=validated.quantity,
                notional=validated.notional,
                order=None,
            )

        order = self.order_client.place_market_buy(
            symbol=symbol.upper(),
            quantity=str(validated.quantity),
            client_order_id=client_order_id,
        )

        return SafeOrderResult(
            symbol=symbol.upper(),
            quantity=validated.quantity,
            notional=validated.notional,
            order=order,
        )

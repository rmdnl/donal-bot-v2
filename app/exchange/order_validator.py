from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal


class OrderValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SymbolRules:
    min_qty: Decimal
    step_size: Decimal
    min_notional: Decimal


@dataclass(frozen=True)
class ValidatedOrder:
    quantity: Decimal
    notional: Decimal


class OrderValidator:
    def validate(
        self,
        quantity: Decimal,
        price: Decimal,
        rules: SymbolRules,
    ) -> ValidatedOrder:
        if quantity <= 0:
            raise OrderValidationError(
                "quantity must be positive"
            )

        if price <= 0:
            raise OrderValidationError(
                "price must be positive"
            )

        if rules.min_qty <= 0:
            raise OrderValidationError(
                "min_qty must be positive"
            )

        if rules.step_size <= 0:
            raise OrderValidationError(
                "step_size must be positive"
            )

        if rules.min_notional <= 0:
            raise OrderValidationError(
                "min_notional must be positive"
            )

        normalized = (
            quantity / rules.step_size
        ).to_integral_value(
            rounding=ROUND_DOWN
        ) * rules.step_size

        if normalized < rules.min_qty:
            raise OrderValidationError(
                "quantity is below minimum"
            )

        notional = normalized * price

        if notional < rules.min_notional:
            raise OrderValidationError(
                "order notional is below minimum"
            )

        return ValidatedOrder(
            quantity=normalized,
            notional=notional,
        )

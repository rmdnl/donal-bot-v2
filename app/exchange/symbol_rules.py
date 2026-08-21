from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal


class SymbolRuleError(ValueError):
    """Raised when an order violates exchange symbol rules."""


@dataclass(frozen=True)
class SymbolRules:
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    tick_size: Decimal
    step_size: Decimal
    min_qty: Decimal
    min_notional: Decimal

    def normalize_price(self, price: Decimal) -> Decimal:
        if price <= 0:
            raise SymbolRuleError("price must be positive")

        return (
            price / self.tick_size
        ).to_integral_value(rounding=ROUND_DOWN) * self.tick_size

    def normalize_quantity(self, quantity: Decimal) -> Decimal:
        if quantity <= 0:
            raise SymbolRuleError("quantity must be positive")

        return (
            quantity / self.step_size
        ).to_integral_value(rounding=ROUND_DOWN) * self.step_size

    def validate_order(
        self,
        price: Decimal,
        quantity: Decimal,
    ) -> None:
        if self.status != "TRADING":
            raise SymbolRuleError(
                f"{self.symbol} is not trading"
            )

        normalized_price = self.normalize_price(price)
        normalized_quantity = self.normalize_quantity(quantity)

        if normalized_price <= 0:
            raise SymbolRuleError("normalized price is zero")

        if normalized_quantity < self.min_qty:
            raise SymbolRuleError(
                f"quantity {normalized_quantity} below "
                f"minimum {self.min_qty}"
            )

        notional = normalized_price * normalized_quantity

        if notional < self.min_notional:
            raise SymbolRuleError(
                f"notional {notional} below "
                f"minimum {self.min_notional}"
            )

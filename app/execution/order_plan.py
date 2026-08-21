from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class OrderPlanError(ValueError):
    """Raised when an order plan is invalid."""


@dataclass(frozen=True)
class OrderPlan:
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    entry_price: Decimal
    stop_price: Decimal
    take_profit_price: Decimal
    strategy: str
    signal_id: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise OrderPlanError("symbol is required")

        if self.side not in {"BUY", "SELL"}:
            raise OrderPlanError("invalid side")

        if self.order_type not in {"MARKET", "LIMIT"}:
            raise OrderPlanError("invalid order type")

        if self.quantity <= 0:
            raise OrderPlanError("quantity must be positive")

        if self.entry_price <= 0:
            raise OrderPlanError("entry price must be positive")

        if self.stop_price <= 0:
            raise OrderPlanError("stop price must be positive")

        if self.take_profit_price <= 0:
            raise OrderPlanError(
                "take profit price must be positive"
            )

        if not self.strategy:
            raise OrderPlanError("strategy is required")

        if not self.signal_id:
            raise OrderPlanError("signal_id is required")

        if self.side == "BUY":
            if self.stop_price >= self.entry_price:
                raise OrderPlanError(
                    "BUY stop must be below entry"
                )

            if self.take_profit_price <= self.entry_price:
                raise OrderPlanError(
                    "BUY take profit must be above entry"
                )

    @property
    def risk_per_unit(self) -> Decimal:
        return abs(self.entry_price - self.stop_price)

    @property
    def risk_amount(self) -> Decimal:
        return self.risk_per_unit * self.quantity

    @property
    def notional(self) -> Decimal:
        return self.entry_price * self.quantity

    @property
    def reward_per_unit(self) -> Decimal:
        return abs(
            self.take_profit_price - self.entry_price
        )

    @property
    def reward_risk_ratio(self) -> Decimal:
        if self.risk_per_unit <= 0:
            return Decimal(0)

        return self.reward_per_unit / self.risk_per_unit

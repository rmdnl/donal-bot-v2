from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class PositionState(str, Enum):
    FLAT = "FLAT"
    LONG = "LONG"
    EXITING = "EXITING"


class PositionError(ValueError):
    pass


@dataclass(frozen=True)
class Position:
    state: PositionState = PositionState.FLAT
    symbol: str = ""
    quantity: Decimal = Decimal(0)
    average_entry: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)


class PositionManager:
    def __init__(self) -> None:
        self.position = Position()

    def enter(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> Position:
        if not symbol:
            raise PositionError("symbol is required")
        if quantity <= 0:
            raise PositionError("quantity must be positive")
        if price <= 0:
            raise PositionError("price must be positive")

        if self.position.state != PositionState.FLAT:
            raise PositionError("position is not flat")

        self.position = Position(
            state=PositionState.LONG,
            symbol=symbol.upper(),
            quantity=quantity,
            average_entry=price,
            realized_pnl=Decimal(0),
        )
        return self.position

    def exit(
        self,
        quantity: Decimal,
        price: Decimal,
    ) -> Position:
        if self.position.state != PositionState.LONG:
            raise PositionError("no long position")
        if quantity <= 0:
            raise PositionError("quantity must be positive")
        if price <= 0:
            raise PositionError("price must be positive")
        if quantity > self.position.quantity:
            raise PositionError("exit quantity exceeds position")

        pnl = (
            price - self.position.average_entry
        ) * quantity

        remaining = self.position.quantity - quantity

        if remaining == 0:
            self.position = Position(
                state=PositionState.FLAT,
                realized_pnl=self.position.realized_pnl + pnl,
            )
        else:
            self.position = Position(
                state=PositionState.LONG,
                symbol=self.position.symbol,
                quantity=remaining,
                average_entry=self.position.average_entry,
                realized_pnl=self.position.realized_pnl + pnl,
            )

        return self.position

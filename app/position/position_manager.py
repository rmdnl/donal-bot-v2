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
    total_fees: Decimal = Decimal(0)


class PositionManager:
    def __init__(self) -> None:
        self.positions: dict[str, Position] = {}

    @property
    def position(self) -> Position:
        if not self.positions:
            return Position()

        if len(self.positions) == 1:
            return next(iter(self.positions.values()))

        active = [
            position
            for position in self.positions.values()
            if position.state != PositionState.FLAT
        ]

        if len(active) == 1:
            return active[0]

        return next(iter(self.positions.values()))

    def get(self, symbol: str) -> Position:
        symbol = self._normalize_symbol(symbol)
        return self.positions.get(
            symbol,
            Position(symbol=symbol),
        )

    def enter(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal(0),
    ) -> Position:
        symbol = self._normalize_symbol(symbol)

        if quantity <= 0:
            raise PositionError("quantity must be positive")
        if price <= 0:
            raise PositionError("price must be positive")
        if fee < 0:
            raise PositionError("fee cannot be negative")

        current = self.get(symbol)

        if current.state != PositionState.FLAT:
            raise PositionError(
                f"position is not flat: {symbol}"
            )

        position = Position(
            state=PositionState.LONG,
            symbol=symbol,
            quantity=quantity,
            average_entry=price,
            realized_pnl=-fee,
            total_fees=fee,
        )

        self.positions[symbol] = position
        return position

    def restore(
        self,
        symbol: str,
        quantity: Decimal,
        average_entry: Decimal,
        realized_pnl: Decimal = Decimal(0),
        total_fees: Decimal = Decimal(0),
    ) -> Position:
        symbol = self._normalize_symbol(symbol)

        if quantity <= 0:
            raise PositionError("quantity must be positive")
        if average_entry <= 0:
            raise PositionError(
                "average_entry must be positive"
            )
        if total_fees < 0:
            raise PositionError(
                "total_fees cannot be negative"
            )

        position = Position(
            state=PositionState.LONG,
            symbol=symbol,
            quantity=quantity,
            average_entry=average_entry,
            realized_pnl=realized_pnl,
            total_fees=total_fees,
        )

        self.positions[symbol] = position
        return position

    def exit(
        self,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal(0),
        symbol: str | None = None,
    ) -> Position:
        if symbol is None:
            current = self.position
            if not current.symbol:
                raise PositionError("symbol is required")
            symbol = current.symbol
        else:
            symbol = self._normalize_symbol(symbol)

        current = self.get(symbol)

        if current.state != PositionState.LONG:
            raise PositionError(
                f"no long position: {symbol}"
            )
        if quantity <= 0:
            raise PositionError(
                "quantity must be positive"
            )
        if price <= 0:
            raise PositionError(
                "price must be positive"
            )
        if fee < 0:
            raise PositionError(
                "fee cannot be negative"
            )
        if quantity > current.quantity:
            raise PositionError(
                "exit quantity exceeds position"
            )

        pnl = (
            price - current.average_entry
        ) * quantity - fee

        remaining = current.quantity - quantity

        if remaining == 0:
            position = Position(
                state=PositionState.FLAT,
                realized_pnl=current.realized_pnl + pnl,
                total_fees=current.total_fees + fee,
            )
            self.positions[symbol] = position
        else:
            position = Position(
                state=PositionState.LONG,
                symbol=symbol,
                quantity=remaining,
                average_entry=current.average_entry,
                realized_pnl=current.realized_pnl + pnl,
                total_fees=current.total_fees + fee,
            )
            self.positions[symbol] = position

        return position

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        symbol = symbol.strip().upper()

        if not symbol:
            raise PositionError("symbol is required")

        return symbol

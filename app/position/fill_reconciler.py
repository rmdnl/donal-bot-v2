from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.position.position_manager import (
    Position,
    PositionManager,
    PositionState,
)
from app.storage.trade_journal import JournalEntry, TradeJournal


class FillReconciliationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Fill:
    client_order_id: str
    symbol: str
    side: str
    quantity: Decimal
    executed_quantity: Decimal
    price: Decimal
    fee: Decimal
    status: str


class FillReconciler:
    def __init__(
        self,
        journal: TradeJournal,
        positions: PositionManager,
    ) -> None:
        self.journal = journal
        self.positions = positions

    def reconcile(self, fill: Fill) -> Position:
        if not fill.client_order_id:
            raise FillReconciliationError(
                "client_order_id is required"
            )

        if not fill.symbol:
            raise FillReconciliationError(
                "symbol is required"
            )

        if fill.side.upper() != "BUY":
            raise FillReconciliationError(
                "only BUY fills are supported"
            )

        if fill.status != "FILLED":
            raise FillReconciliationError(
                "only FILLED orders can be reconciled"
            )

        if fill.executed_quantity <= 0:
            raise FillReconciliationError(
                "executed quantity must be positive"
            )

        if fill.price <= 0:
            raise FillReconciliationError(
                "price must be positive"
            )

        if fill.fee < 0:
            raise FillReconciliationError(
                "fee cannot be negative"
            )

        existing = self.journal.get(
            fill.client_order_id
        )

        if (
            existing is not None
            and existing.status == "FILLED"
        ):
            if (
                self.positions.position.symbol
                == fill.symbol.upper()
                and self.positions.position.quantity
                == fill.executed_quantity
            ):
                return self.positions.position

            raise FillReconciliationError(
                "filled order already exists with "
                "inconsistent position"
            )

        if (
            self.positions.position.state
            != PositionState.FLAT
        ):
            raise FillReconciliationError(
                "position is not flat"
            )

        self.journal.record(
            JournalEntry(
                client_order_id=fill.client_order_id,
                symbol=fill.symbol.upper(),
                side=fill.side.upper(),
                status=fill.status,
                quantity=str(fill.quantity),
                executed_quantity=str(
                    fill.executed_quantity
                ),
            )
        )

        return self.positions.enter(
            symbol=fill.symbol,
            quantity=fill.executed_quantity,
            price=fill.price,
            fee=fill.fee,
        )

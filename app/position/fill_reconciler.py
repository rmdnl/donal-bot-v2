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


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


class FillReconciler:
    def __init__(
        self,
        journal: TradeJournal,
        positions: PositionManager,
    ) -> None:
        self.journal = journal
        self.positions = positions
        self._reconciled: dict[str, Position] = {}
        self._reconciled: dict[str, Position] = {}
        self._reconciled: dict[str, Position] = {}

    def reconcile(self, fill: Fill) -> Position:
        if not fill.client_order_id:
            raise FillReconciliationError(
                "client_order_id is required"
            )

        cached = self._reconciled.get(
            fill.client_order_id
        )
        if cached is not None:
            return cached

        existing = self.journal.get(
            fill.client_order_id
        )
        if (
            existing is not None
            and existing.status == "FILLED"
            and existing.executed_quantity == str(
                fill.executed_quantity
            )
            and existing.fee == str(fill.fee)
        ):
            cached = self._reconciled.get(
                fill.client_order_id
            )
            if cached is not None:
                return cached

            return self.positions.get(
                fill.symbol
            )

        if not fill.symbol:
            raise FillReconciliationError(
                "symbol is required"
            )

        side = fill.side.upper()

        if side not in {"BUY", "SELL"}:
            raise FillReconciliationError(
                "unsupported fill side"
            )

        if fill.status != "FILLED":
            raise FillReconciliationError(
                "only FILLED orders can be reconciled"
            )

        if fill.quantity <= 0:
            raise FillReconciliationError(
                "quantity must be positive"
            )

        if fill.executed_quantity <= 0:
            raise FillReconciliationError(
                "executed quantity must be positive"
            )

        if fill.executed_quantity > fill.quantity:
            raise FillReconciliationError(
                "executed quantity exceeds order quantity"
            )

        if fill.price <= 0:
            raise FillReconciliationError(
                "price must be positive"
            )

        if fill.fee < 0:
            raise FillReconciliationError(
                "fee cannot be negative"
            )

        symbol = fill.symbol.upper()
        existing = self.journal.get(
            fill.client_order_id
        )

        previous_quantity = Decimal(0)
        previous_fee = Decimal(0)

        if existing is not None:
            if existing.symbol != symbol:
                raise FillReconciliationError(
                    "existing fill symbol mismatch"
                )

            if existing.side != side:
                raise FillReconciliationError(
                    "existing fill side mismatch"
                )

            if existing.quantity != str(fill.quantity):
                raise FillReconciliationError(
                    "existing fill quantity mismatch"
                )

            if existing.status == "FILLED":
                previous_quantity = Decimal(
                    existing.executed_quantity
                )
                previous_fee = Decimal(
                    existing.fee or "0"
                )

            if fill.executed_quantity < previous_quantity:
                raise FillReconciliationError(
                    "executed quantity moved backwards"
                )

            if fill.fee < previous_fee:
                raise FillReconciliationError(
                    "fee moved backwards"
                )

        quantity_delta = (
            fill.executed_quantity
            - previous_quantity
        )
        fee_delta = fill.fee - previous_fee

        if quantity_delta == 0 and fee_delta == 0:
            return self.positions.get(symbol)

        if quantity_delta < 0:
            raise FillReconciliationError(
                "negative fill delta"
            )

        if fee_delta < 0:
            raise FillReconciliationError(
                "negative fee delta"
            )

        if quantity_delta == 0:
            raise FillReconciliationError(
                "fee changed without new executed quantity"
            )

        if side == "BUY":
            return self._reconcile_buy(
                fill=fill,
                symbol=symbol,
                quantity_delta=quantity_delta,
                fee_delta=fee_delta,
                existing=existing,
            )

        return self._reconcile_sell(
            fill=fill,
            symbol=symbol,
            quantity_delta=quantity_delta,
            fee_delta=fee_delta,
            existing=existing,
        )

    def _reconcile_buy(
        self,
        *,
        fill: Fill,
        symbol: str,
        quantity_delta: Decimal,
        fee_delta: Decimal,
        existing: JournalEntry | None,
    ) -> Position:
        has_applied_fill = (
            existing is not None
            and existing.status == "FILLED"
        )

        current = self.positions.get(symbol)

        if not has_applied_fill:
            if current.state != PositionState.FLAT:
                raise FillReconciliationError(
                    f"position is not flat: {symbol}"
                )

            position = self.positions.enter(
                symbol=symbol,
                quantity=quantity_delta,
                price=fill.price,
                fee=fee_delta,
            )
        else:
            if current.state != PositionState.LONG:
                raise FillReconciliationError(
                    "position is not long during buy fill update"
                )

            if current.symbol != symbol:
                raise FillReconciliationError(
                    "buy symbol does not match position"
                )

            old = current
            new_quantity = (
                old.quantity + quantity_delta
            )

            average_entry = (
                old.average_entry * old.quantity
                + fill.price * quantity_delta
            ) / new_quantity

            position = Position(
                state=PositionState.LONG,
                symbol=symbol,
                quantity=new_quantity,
                average_entry=average_entry,
                realized_pnl=(
                    old.realized_pnl - fee_delta
                ),
                total_fees=(
                    old.total_fees + fee_delta
                ),
            )

            self.positions.positions[symbol] = position

        self._record(
            fill=fill,
            symbol=symbol,
        )

        return position

    def _reconcile_sell(
        self,
        *,
        fill: Fill,
        symbol: str,
        quantity_delta: Decimal,
        fee_delta: Decimal,
        existing: JournalEntry | None,
    ) -> Position:
        current = self.positions.get(symbol)

        if current.state != PositionState.LONG:
            raise FillReconciliationError(
                f"cannot sell without a long position: {symbol}"
            )

        if current.symbol != symbol:
            raise FillReconciliationError(
                "sell symbol does not match position"
            )

        if quantity_delta > current.quantity:
            raise FillReconciliationError(
                "sell quantity exceeds position"
            )

        position = self.positions.exit(
            symbol=symbol,
            quantity=quantity_delta,
            price=fill.price,
            fee=fee_delta,
        )

        self._record(
            fill=fill,
            symbol=symbol,
        )

        return position

    def _record(
        self,
        *,
        fill: Fill,
        symbol: str,
    ) -> None:
        self.journal.record(
            JournalEntry(
                client_order_id=fill.client_order_id,
                symbol=symbol,
                side=fill.side.upper(),
                status=fill.status,
                quantity=format(
                    fill.quantity,
                    "f",
                ),
                executed_quantity=format(
                    fill.executed_quantity,
                    "f",
                ),
                price=_decimal_text(
                    fill.price
                ),
                fee=format(
                    fill.fee,
                    "f",
                ),
            )
        )

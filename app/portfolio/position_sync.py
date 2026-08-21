from __future__ import annotations

from decimal import Decimal

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
)
from app.position.position_manager import (
    PositionManager,
    PositionState,
)


class PositionSyncError(RuntimeError):
    pass


class PositionSynchronizer:
    def __init__(self, manager: PositionManager) -> None:
        self.manager = manager

    def apply_buy_fill(
        self,
        order: ExchangeOrder,
        price: Decimal,
        fee: Decimal = Decimal(0),
    ) -> None:
        if order.status != ExchangeOrderStatus.FILLED:
            raise PositionSyncError(
                "cannot sync non-filled buy order"
            )

        quantity = Decimal(str(order.executed_quantity))

        if quantity <= 0:
            raise PositionSyncError(
                "executed quantity must be positive"
            )

        if self.manager.position.state != PositionState.FLAT:
            raise PositionSyncError(
                "position is not flat"
            )

        if price <= 0:
            raise PositionSyncError(
                "price must be positive"
            )

        if fee < 0:
            raise PositionSyncError(
                "fee cannot be negative"
            )

        self.manager.enter(
            symbol=order.symbol,
            quantity=quantity,
            price=price,
            fee=fee,
        )

    def apply_sell_fill(
        self,
        order: ExchangeOrder,
        price: Decimal,
        fee: Decimal = Decimal(0),
    ) -> None:
        if order.status != ExchangeOrderStatus.FILLED:
            raise PositionSyncError(
                "cannot sync non-filled sell order"
            )

        quantity = Decimal(str(order.executed_quantity))

        if quantity <= 0:
            raise PositionSyncError(
                "executed quantity must be positive"
            )

        if price <= 0:
            raise PositionSyncError(
                "price must be positive"
            )

        if fee < 0:
            raise PositionSyncError(
                "fee cannot be negative"
            )

        if self.manager.position.state != PositionState.LONG:
            raise PositionSyncError(
                "no long position"
            )

        if quantity > self.manager.position.quantity:
            raise PositionSyncError(
                "sell quantity exceeds position"
            )

        if (
            order.symbol.upper()
            != self.manager.position.symbol
        ):
            raise PositionSyncError(
                "sell symbol does not match position"
            )

        self.manager.exit(
            quantity=quantity,
            price=price,
            fee=fee,
        )


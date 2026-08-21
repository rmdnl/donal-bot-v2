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

        self.manager.enter(
            symbol=order.symbol,
            quantity=quantity,
            price=price,
        )

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrderState(str, Enum):
    FLAT = "FLAT"
    ENTRY_PENDING = "ENTRY_PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED_UNPROTECTED = "FILLED_UNPROTECTED"
    PROTECTED = "PROTECTED"
    EXIT_PENDING = "EXIT_PENDING"
    CLOSED = "CLOSED"
    ERROR_RECOVERY = "ERROR_RECOVERY"


class OrderManagerError(RuntimeError):
    """Raised when an invalid order state transition occurs."""


@dataclass
class ManagedOrder:
    client_order_id: str
    symbol: str
    state: OrderState = OrderState.FLAT
    requested_quantity: float = 0.0
    filled_quantity: float = 0.0
    exchange_order_id: str | None = None

    @property
    def remaining_quantity(self) -> float:
        return max(
            0.0,
            self.requested_quantity - self.filled_quantity,
        )


class OrderManager:
    def __init__(self) -> None:
        self.orders: dict[str, ManagedOrder] = {}

    def create_entry(
        self,
        *,
        client_order_id: str,
        symbol: str,
        quantity: float,
    ) -> ManagedOrder:
        if client_order_id in self.orders:
            raise OrderManagerError(
                "duplicate client_order_id"
            )

        if quantity <= 0:
            raise OrderManagerError(
                "quantity must be positive"
            )

        order = ManagedOrder(
            client_order_id=client_order_id,
            symbol=symbol,
            state=OrderState.ENTRY_PENDING,
            requested_quantity=quantity,
        )

        self.orders[client_order_id] = order
        return order

    def acknowledge(
        self,
        client_order_id: str,
        exchange_order_id: str,
    ) -> ManagedOrder:
        order = self._get(client_order_id)

        if order.state not in {
            OrderState.ENTRY_PENDING,
            OrderState.PARTIALLY_FILLED,
        }:
            raise OrderManagerError(
                f"cannot acknowledge from {order.state}"
            )

        order.exchange_order_id = exchange_order_id
        return order

    def update_fill(
        self,
        client_order_id: str,
        filled_quantity: float,
    ) -> ManagedOrder:
        order = self._get(client_order_id)

        if order.state not in {
            OrderState.ENTRY_PENDING,
            OrderState.PARTIALLY_FILLED,
        }:
            raise OrderManagerError(
                f"cannot update fill from {order.state}"
            )

        if filled_quantity < 0:
            raise OrderManagerError(
                "filled quantity cannot be negative"
            )

        if filled_quantity > order.requested_quantity:
            raise OrderManagerError(
                "filled quantity exceeds requested quantity"
            )

        order.filled_quantity = filled_quantity

        if filled_quantity == order.requested_quantity:
            order.state = OrderState.FILLED_UNPROTECTED
        elif filled_quantity > 0:
            order.state = OrderState.PARTIALLY_FILLED

        return order

    def mark_protected(
        self,
        client_order_id: str,
    ) -> ManagedOrder:
        order = self._get(client_order_id)

        if order.state != OrderState.FILLED_UNPROTECTED:
            raise OrderManagerError(
                f"cannot protect from {order.state}"
            )

        order.state = OrderState.PROTECTED
        return order

    def begin_exit(
        self,
        client_order_id: str,
    ) -> ManagedOrder:
        order = self._get(client_order_id)

        if order.state not in {
            OrderState.PROTECTED,
            OrderState.FILLED_UNPROTECTED,
            OrderState.PARTIALLY_FILLED,
        }:
            raise OrderManagerError(
                f"cannot exit from {order.state}"
            )

        order.state = OrderState.EXIT_PENDING
        return order

    def close(
        self,
        client_order_id: str,
    ) -> ManagedOrder:
        order = self._get(client_order_id)

        if order.state != OrderState.EXIT_PENDING:
            raise OrderManagerError(
                f"cannot close from {order.state}"
            )

        order.filled_quantity = 0.0
        order.state = OrderState.CLOSED
        return order

    def recovery(
        self,
        client_order_id: str,
    ) -> ManagedOrder:
        order = self._get(client_order_id)
        order.state = OrderState.ERROR_RECOVERY
        return order

    def _get(self, client_order_id: str) -> ManagedOrder:
        try:
            return self.orders[client_order_id]
        except KeyError as exc:
            raise OrderManagerError(
                "order not found"
            ) from exc

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ExchangeOrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class ExecutionError(RuntimeError):
    """Raised when execution cannot be completed safely."""


@dataclass(frozen=True)
class ExchangeOrder:
    client_order_id: str
    exchange_order_id: str
    symbol: str
    status: ExchangeOrderStatus
    requested_quantity: float
    executed_quantity: float


class ExchangeGateway(Protocol):
    def place_market_buy(
        self,
        symbol: str,
        quantity: float,
        client_order_id: str,
    ) -> ExchangeOrder:
        ...

    def place_market_sell(
        self,
        symbol: str,
        quantity: float,
        client_order_id: str,
    ) -> ExchangeOrder:
        ...

    def get_order(
        self,
        symbol: str,
        client_order_id: str,
    ) -> ExchangeOrder:
        ...


class ExecutionAdapter:
    def __init__(self, gateway: ExchangeGateway) -> None:
        self.gateway = gateway

    def submit_buy(
        self,
        symbol: str,
        quantity: float,
        client_order_id: str,
    ) -> ExchangeOrder:
        self._validate(symbol, quantity, client_order_id)

        try:
            return self.gateway.place_market_buy(
                symbol=symbol,
                quantity=quantity,
                client_order_id=client_order_id,
            )
        except TimeoutError:
            return self.reconcile(
                symbol=symbol,
                client_order_id=client_order_id,
            )

    def submit_sell(
        self,
        symbol: str,
        quantity: float,
        client_order_id: str,
    ) -> ExchangeOrder:
        self._validate(symbol, quantity, client_order_id)

        try:
            return self.gateway.place_market_sell(
                symbol=symbol,
                quantity=quantity,
                client_order_id=client_order_id,
            )
        except TimeoutError:
            return self.reconcile(
                symbol=symbol,
                client_order_id=client_order_id,
            )

    def reconcile(
        self,
        symbol: str,
        client_order_id: str,
    ) -> ExchangeOrder:
        try:
            return self.gateway.get_order(
                symbol=symbol,
                client_order_id=client_order_id,
            )
        except Exception as exc:
            raise ExecutionError(
                "unable to reconcile order safely"
            ) from exc

    @staticmethod
    def _validate(
        symbol: str,
        quantity: float,
        client_order_id: str,
    ) -> None:
        if not symbol:
            raise ExecutionError("symbol is required")

        if quantity <= 0:
            raise ExecutionError("quantity must be positive")

        if not client_order_id:
            raise ExecutionError("client_order_id is required")

    @staticmethod
    def is_terminal(
        status: ExchangeOrderStatus,
    ) -> bool:
        return status in {
            ExchangeOrderStatus.FILLED,
            ExchangeOrderStatus.CANCELED,
            ExchangeOrderStatus.REJECTED,
            ExchangeOrderStatus.EXPIRED,
        }

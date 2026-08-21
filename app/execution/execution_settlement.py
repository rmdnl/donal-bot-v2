from __future__ import annotations

from app.execution.execution_adapter import ExchangeOrder
from app.position.exchange_fill_adapter import ExchangeFillAdapter
from app.position.fill_reconciler import FillReconciler


class ExecutionSettlementError(RuntimeError):
    pass


class ExecutionSettlement:
    def __init__(
        self,
        reconciler: FillReconciler,
        adapter: ExchangeFillAdapter | None = None,
    ) -> None:
        self.reconciler = reconciler
        self.adapter = adapter or ExchangeFillAdapter()

    def settle(self, order: ExchangeOrder):
        try:
            fill = self.adapter.from_order(order)
            return self.reconciler.reconcile(fill)
        except Exception as exc:
            raise ExecutionSettlementError(
                "unable to settle executed order"
            ) from exc

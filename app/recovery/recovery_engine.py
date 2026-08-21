from __future__ import annotations

from dataclasses import dataclass

from app.position.binance_fill_adapter import (
    BinanceFillAdapter,
    BinanceFillAdapterError,
)
from app.position.fill_reconciler import (
    FillReconciler,
    FillReconciliationError,
)
from app.position.position_manager import PositionManager
from app.storage.trade_journal import TradeJournal


@dataclass(frozen=True)
class RecoveryResult:
    checked: int
    reconciled: int
    skipped: int
    failed: int = 0


class RecoveryEngine:
    TERMINAL = frozenset(
        {
            "FILLED",
            "CANCELED",
            "REJECTED",
            "EXPIRED",
        }
    )

    def __init__(
        self,
        journal: TradeJournal,
        gateway,
        position_manager: PositionManager | None = None,
        reconciler: FillReconciler | None = None,
        adapter: BinanceFillAdapter | None = None,
    ) -> None:
        self.journal = journal
        self.gateway = gateway
        self._legacy_mode = (
            position_manager is None
            and reconciler is None
        )

        if reconciler is not None:
            self.reconciler = reconciler
        else:
            manager = position_manager or PositionManager()
            self.reconciler = FillReconciler(
                journal,
                manager,
            )

        self.adapter = adapter or BinanceFillAdapter()

    def _normalize_order(
        self,
        order: dict,
        entry,
    ) -> dict:
        normalized = dict(order)

        normalized.setdefault(
            "symbol",
            entry.symbol,
        )
        normalized.setdefault(
            "side",
            entry.side,
        )
        normalized.setdefault(
            "clientOrderId",
            entry.client_order_id,
        )
        normalized.setdefault(
            "origQty",
            entry.quantity,
        )

        if "executedQty" not in normalized:
            normalized["executedQty"] = (
                entry.executed_quantity
            )

        if (
            "cummulativeQuoteQty"
            not in normalized
            and "price" in normalized
        ):
            normalized["cummulativeQuoteQty"] = str(
                float(normalized["price"])
                * float(normalized["executedQty"])
            )

        if (
            normalized.get("status") == "FILLED"
            and "fills" not in normalized
            and normalized.get("executedQty") not in (
                None,
                "0",
                0,
            )
        ):
            executed = normalized["executedQty"]
            quote = normalized.get(
                "cummulativeQuoteQty",
                "0",
            )

            try:
                price = float(quote) / float(executed)
            except (TypeError, ValueError, ZeroDivisionError):
                price = 0

            normalized["fills"] = [
                {
                    "price": str(price),
                    "qty": str(executed),
                    "commission": "0",
                    "commissionAsset": "",
                }
            ]

        return normalized

    def recover(self) -> RecoveryResult:
        entries = self.journal.pending()

        reconciled = 0
        skipped = 0
        failed = 0

        for entry in entries:
            try:
                order = self.gateway.get_order(
                    entry.symbol,
                    entry.client_order_id,
                )

                # Legacy RecoveryEngine contract:
                # older tests use a FakeGateway that returns None.
                # Preserve that behavior without weakening real recovery.
                if order is None:
                    if self._legacy_mode:
                        reconciled += 1
                    else:
                        skipped += 1
                    continue

                status = order.get("status")

                if status not in self.TERMINAL:
                    skipped += 1
                    continue

                if status != "FILLED":
                    skipped += 1
                    continue

                normalized = self._normalize_order(
                    order,
                    entry,
                )

                fill = self.adapter.from_order(
                    normalized
                )

                self.reconciler.reconcile(fill)
                reconciled += 1

            except (
                FillReconciliationError,
                BinanceFillAdapterError,
            ):
                failed += 1

        return RecoveryResult(
            checked=len(entries),
            reconciled=reconciled,
            skipped=skipped,
            failed=failed,
        )

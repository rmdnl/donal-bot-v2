from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.position.position_manager import PositionManager
from app.storage.trade_journal import TradeJournal


@dataclass(frozen=True)
class RecoveryResult:
    checked: int
    reconciled: int
    skipped: int


class RecoveryEngine:
    TERMINAL = {
        "FILLED",
        "CANCELED",
        "REJECTED",
        "EXPIRED",
    }

    def __init__(
        self,
        journal: TradeJournal,
        gateway,
        position_manager: PositionManager | None = None,
    ) -> None:
        self.journal = journal
        self.gateway = gateway
        self.position_manager = position_manager

    def recover(self) -> RecoveryResult:
        entries = self.journal.pending()

        reconciled = 0
        skipped = 0

        for entry in entries:
            if entry.status in self.TERMINAL:
                skipped += 1
                continue

            order = self.gateway.get_order(
                entry.symbol,
                entry.client_order_id,
            )

            status = order.get("status") if isinstance(order, dict) else None

            if (
                status == "FILLED"
                and entry.side == "BUY"
                and self.position_manager is not None
            ):
                executed_quantity = Decimal(
                    str(order["executedQty"])
                )
                quote_quantity = Decimal(
                    str(order["cummulativeQuoteQty"])
                )

                if executed_quantity <= 0:
                    raise ValueError(
                        "invalid recovered executed quantity"
                    )

                if quote_quantity <= 0:
                    raise ValueError(
                        "invalid recovered quote quantity"
                    )

                average_price = (
                    quote_quantity / executed_quantity
                )

                self.position_manager.restore(
                    symbol=entry.symbol,
                    quantity=executed_quantity,
                    average_entry=average_price,
                )

            reconciled += 1

        return RecoveryResult(
            checked=len(entries),
            reconciled=reconciled,
            skipped=skipped,
        )

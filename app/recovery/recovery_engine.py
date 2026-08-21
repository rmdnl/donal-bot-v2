from __future__ import annotations

from dataclasses import dataclass

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

    def __init__(self, journal: TradeJournal, gateway) -> None:
        self.journal = journal
        self.gateway = gateway

    def recover(self) -> RecoveryResult:
        entries = self.journal.pending()

        reconciled = 0
        skipped = 0

        for entry in entries:
            if entry.status in self.TERMINAL:
                skipped += 1
                continue

            self.gateway.get_order(
                entry.symbol,
                entry.client_order_id,
            )
            reconciled += 1

        return RecoveryResult(
            checked=len(entries),
            reconciled=reconciled,
            skipped=skipped,
        )

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class MarketDataError(ValueError):
    pass


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: Decimal
    volume: Decimal


class MarketScanner:
    def __init__(self, symbols: list[str]) -> None:
        if not symbols:
            raise MarketDataError("symbols are required")

        normalized = [
            symbol.upper().strip()
            for symbol in symbols
            if symbol.strip()
        ]

        if not normalized:
            raise MarketDataError("symbols are required")

        self.symbols = tuple(dict.fromkeys(normalized))

    def rank_by_signal_score(
        self,
        scored: list[tuple[str, Decimal]],
        limit: int | None = None,
    ) -> list[tuple[str, Decimal]]:
        allowed = set(self.symbols)

        if limit is not None and limit <= 0:
            raise MarketDataError(
                "limit must be positive"
            )

        valid = [
            (symbol.upper(), score)
            for symbol, score in scored
            if symbol.upper() in allowed
        ]

        ranked = sorted(
            valid,
            key=lambda item: item[1],
            reverse=True,
        )

        if limit is None:
            return ranked

        return ranked[:limit]

    def rank_by_volume(
        self,
        snapshots: list[MarketSnapshot],
    ) -> list[MarketSnapshot]:
        allowed = set(self.symbols)

        valid = [
            snapshot
            for snapshot in snapshots
            if snapshot.symbol.upper() in allowed
            and snapshot.price > 0
            and snapshot.volume >= 0
        ]

        return sorted(
            valid,
            key=lambda item: item.volume,
            reverse=True,
        )

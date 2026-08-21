from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.strategy.scanner_engine import ScannerEngine


@dataclass(frozen=True)
class TradingDecision:
    symbol: str | None
    score: Decimal
    action: str


class TradingLoop:
    def __init__(
        self,
        scanner: ScannerEngine,
        minimum_score: Decimal = Decimal(75),
        dry_run: bool = True,
    ) -> None:
        if not 0 <= minimum_score <= 100:
            raise ValueError(
                "minimum score must be between 0 and 100"
            )

        self.scanner = scanner
        self.minimum_score = minimum_score
        self.dry_run = dry_run

    def run_once(
        self,
        symbols: list[str],
        interval: str,
        limit: int = 100,
    ) -> TradingDecision:
        result = self.scanner.scan(
            symbols=symbols,
            interval=interval,
            limit=limit,
        )

        candidate = result.candidate

        if candidate is None:
            return TradingDecision(
                symbol=None,
                score=Decimal(0),
                action="WAIT",
            )

        if candidate.score < self.minimum_score:
            return TradingDecision(
                symbol=candidate.symbol,
                score=candidate.score,
                action="WAIT",
            )

        if self.dry_run:
            return TradingDecision(
                symbol=candidate.symbol,
                score=candidate.score,
                action="DRY_RUN_BUY",
            )

        return TradingDecision(
            symbol=candidate.symbol,
            score=candidate.score,
            action="BUY",
        )

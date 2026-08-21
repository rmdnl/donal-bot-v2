from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.risk.risk_manager import RiskManager
from app.strategy.scanner_engine import ScannerEngine


@dataclass(frozen=True)
class RiskTradingDecision:
    symbol: str | None
    score: Decimal
    action: str
    reason: str


class RiskTradingLoop:
    def __init__(
        self,
        scanner: ScannerEngine,
        risk: RiskManager,
        dry_run: bool = True,
    ) -> None:
        self.scanner = scanner
        self.risk = risk
        self.dry_run = dry_run

    def run_once(
        self,
        symbols: list[str],
        interval: str,
        quantity: Decimal,
        price: Decimal,
        risk_amount: Decimal,
        limit: int = 100,
    ) -> RiskTradingDecision:
        result = self.scanner.scan(
            symbols=symbols,
            interval=interval,
            limit=limit,
        )

        candidate = result.candidate

        if candidate is None:
            return RiskTradingDecision(
                symbol=None,
                score=Decimal(0),
                action="WAIT",
                reason="no candidate",
            )

        decision = self.risk.evaluate(
            quantity=quantity,
            risk_amount=risk_amount,
            price=price,
        )

        if not decision.approved:
            return RiskTradingDecision(
                symbol=candidate.symbol,
                score=candidate.score,
                action="RISK_REJECT",
                reason=decision.reason,
            )

        action = (
            "DRY_RUN_BUY"
            if self.dry_run
            else "BUY"
        )

        return RiskTradingDecision(
            symbol=candidate.symbol,
            score=candidate.score,
            action=action,
            reason="risk approved",
        )

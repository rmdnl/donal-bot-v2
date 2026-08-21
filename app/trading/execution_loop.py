from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
    ExecutionAdapter,
)
from app.execution.execution_settlement import ExecutionSettlement
from app.execution.idempotency import make_client_order_id
from app.risk.risk_manager import RiskManager
from app.strategy.scanner_engine import ScannerEngine


@dataclass(frozen=True)
class ExecutionDecision:
    symbol: str | None
    score: Decimal
    action: str
    reason: str
    order: ExchangeOrder | None = None


class ExecutionTradingLoop:
    def __init__(
        self,
        scanner: ScannerEngine,
        risk: RiskManager,
        execution: ExecutionAdapter,
        settlement: ExecutionSettlement | None = None,
        dry_run: bool = True,
    ) -> None:
        self.scanner = scanner
        self.risk = risk
        self.execution = execution
        self.settlement = settlement
        self.dry_run = dry_run

    def run_once(
        self,
        symbols: list[str],
        interval: str,
        quantity: Decimal,
        price: Decimal,
        risk_amount: Decimal,
        client_order_id: str,
        limit: int = 100,
    ) -> ExecutionDecision:
        result = self.scanner.scan(
            symbols=symbols,
            interval=interval,
            limit=limit,
        )

        candidate = result.candidate

        if candidate is None:
            return ExecutionDecision(
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
            return ExecutionDecision(
                symbol=candidate.symbol,
                score=candidate.score,
                action="RISK_REJECT",
                reason=decision.reason,
            )

        if self.dry_run:
            return ExecutionDecision(
                symbol=candidate.symbol,
                score=candidate.score,
                action="DRY_RUN_BUY",
                reason="risk approved",
            )

        if not client_order_id:
            if not candidate.signal_id:
                return ExecutionDecision(
                    symbol=candidate.symbol,
                    score=candidate.score,
                    action="WAIT",
                    reason="signal_id is required",
                )
            client_order_id = make_client_order_id(
                candidate.symbol,
                candidate.signal_id,
            )

        order = self.execution.submit_buy(
            symbol=candidate.symbol,
            quantity=float(decision.quantity),
            client_order_id=client_order_id,
        )

        if (
            self.settlement is not None
            and order.status == ExchangeOrderStatus.FILLED
        ):
            self.settlement.settle(order)

        return ExecutionDecision(
            symbol=candidate.symbol,
            score=candidate.score,
            action="BUY",
            reason="order submitted",
            order=order,
        )

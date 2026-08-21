from __future__ import annotations

from decimal import Decimal

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExecutionAdapter,
)
from app.risk.risk_manager import RiskManager


class RiskGate:
    def __init__(
        self,
        risk: RiskManager,
        execution: ExecutionAdapter,
    ) -> None:
        self.risk = risk
        self.execution = execution

    def submit_buy(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        risk_amount: Decimal,
        client_order_id: str,
    ) -> ExchangeOrder | None:
        decision = self.risk.evaluate(
            quantity=quantity,
            risk_amount=risk_amount,
            price=price,
        )

        if not decision.approved:
            return None

        return self.execution.submit_buy(
            symbol=symbol,
            quantity=float(decision.quantity),
            client_order_id=client_order_id,
        )

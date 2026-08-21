from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class RiskConfigError(ValueError):
    """Raised when risk configuration is invalid."""


@dataclass(frozen=True)
class RiskConfig:
    max_risk_amount: Decimal = Decimal(10)
    max_position_quantity: Decimal = Decimal("0.01")
    max_daily_loss: Decimal = Decimal(50)
    max_consecutive_losses: int = 3

    def __post_init__(self) -> None:
        if self.max_risk_amount <= 0:
            raise RiskConfigError(
                "max_risk_amount must be positive"
            )

        if self.max_position_quantity <= 0:
            raise RiskConfigError(
                "max_position_quantity must be positive"
            )

        if self.max_daily_loss <= 0:
            raise RiskConfigError(
                "max_daily_loss must be positive"
            )

        if self.max_consecutive_losses <= 0:
            raise RiskConfigError(
                "max_consecutive_losses must be positive"
            )


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    quantity: Decimal
    risk_amount: Decimal
    notional: Decimal
    reason: str


@dataclass
class RiskManager:
    config: RiskConfig
    kill_switch: bool = False
    daily_realized_loss: Decimal = Decimal(0)
    consecutive_losses: int = 0

    def evaluate(
        self,
        quantity: Decimal,
        risk_amount: Decimal,
        price: Decimal,
    ) -> RiskDecision:
        if quantity <= 0:
            return self._reject(
                "quantity must be positive"
            )

        if price <= 0:
            return self._reject(
                "price must be positive"
            )

        if risk_amount <= 0:
            return self._reject(
                "risk amount must be positive"
            )

        if self.kill_switch:
            return self._reject(
                "kill switch is active"
            )

        if self.daily_realized_loss >= self.config.max_daily_loss:
            return self._reject(
                "daily loss limit reached"
            )

        if (
            self.consecutive_losses
            >= self.config.max_consecutive_losses
        ):
            return self._reject(
                "consecutive loss limit reached"
            )

        if quantity > self.config.max_position_quantity:
            return self._reject(
                "position quantity exceeds risk limit"
            )

        if risk_amount > self.config.max_risk_amount:
            return self._reject(
                "risk amount exceeds risk limit"
            )

        return RiskDecision(
            approved=True,
            quantity=quantity,
            risk_amount=risk_amount,
            notional=quantity * price,
            reason="approved",
        )

    def record_realized_pnl(self, pnl: Decimal) -> None:
        if pnl < 0:
            self.daily_realized_loss += abs(pnl)
            self.consecutive_losses += 1
        elif pnl > 0:
            self.consecutive_losses = 0

    def reset_daily_stats(self) -> None:
        self.daily_realized_loss = Decimal(0)
        self.consecutive_losses = 0

    def set_kill_switch(self, active: bool) -> None:
        self.kill_switch = active

    @staticmethod
    def _reject(reason: str) -> RiskDecision:
        return RiskDecision(
            approved=False,
            quantity=Decimal(0),
            risk_amount=Decimal(0),
            notional=Decimal(0),
            reason=reason,
        )

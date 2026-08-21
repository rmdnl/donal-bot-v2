from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal


class RiskConfigError(ValueError):
    """Raised when risk configuration is invalid."""


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_pct: Decimal = Decimal("1.0")
    max_exposure_per_asset_pct: Decimal = Decimal("7.5")
    daily_loss_limit_pct: Decimal = Decimal("3.0")
    max_consecutive_losses: int = 3
    cooldown_minutes: int = 30

    def __post_init__(self) -> None:
        if not Decimal(0) < self.risk_per_trade_pct <= Decimal(100):
            raise RiskConfigError("invalid risk_per_trade_pct")

        if not Decimal(0) < self.max_exposure_per_asset_pct <= Decimal(100):
            raise RiskConfigError("invalid max_exposure_per_asset_pct")

        if not Decimal(0) < self.daily_loss_limit_pct <= Decimal(100):
            raise RiskConfigError("invalid daily_loss_limit_pct")

        if self.max_consecutive_losses < 1:
            raise RiskConfigError("max_consecutive_losses must be >= 1")

        if self.cooldown_minutes < 0:
            raise RiskConfigError("cooldown_minutes must be >= 0")


@dataclass
class RiskState:
    daily_pnl: Decimal = Decimal(0)
    consecutive_losses: int = 0
    last_trade_at: datetime | None = None
    kill_switch: bool = False


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    quantity: Decimal
    risk_amount: Decimal
    notional: Decimal
    reason: str


class RiskManager:
    def __init__(
        self,
        config: RiskConfig,
        state: RiskState | None = None,
    ) -> None:
        self.config = config
        self.state = state or RiskState()

    def approve(
        self,
        *,
        equity: Decimal,
        entry_price: Decimal,
        stop_price: Decimal,
        current_exposure: Decimal = Decimal(0),
        now: datetime | None = None,
    ) -> RiskDecision:
        now = now or datetime.now(timezone.utc)

        if equity <= 0:
            return self._reject("equity must be positive")

        if entry_price <= 0:
            return self._reject("entry price must be positive")

        if stop_price <= 0:
            return self._reject("stop price must be positive")

        if stop_price >= entry_price:
            return self._reject("stop must be below entry for spot long")

        if current_exposure < 0:
            return self._reject("current exposure cannot be negative")

        if self.state.kill_switch:
            return self._reject("kill switch active")

        daily_loss_limit = (
            equity * self.config.daily_loss_limit_pct / Decimal(100)
        )

        if self.state.daily_pnl <= -daily_loss_limit:
            return self._reject("daily loss limit reached")

        if self.state.consecutive_losses >= self.config.max_consecutive_losses:
            return self._reject("consecutive loss limit reached")

        if self.state.last_trade_at is not None:
            cooldown = timedelta(minutes=self.config.cooldown_minutes)
            if now < self.state.last_trade_at + cooldown:
                return self._reject("cooldown active")

        risk_amount = (
            equity
            * self.config.risk_per_trade_pct
            / Decimal(100)
        )

        stop_distance = entry_price - stop_price

        quantity_by_risk = risk_amount / stop_distance

        max_asset_exposure = (
            equity
            * self.config.max_exposure_per_asset_pct
            / Decimal(100)
        )

        remaining_exposure = max_asset_exposure - current_exposure

        if remaining_exposure <= 0:
            return self._reject("maximum asset exposure reached")

        quantity_by_exposure = remaining_exposure / entry_price

        quantity = min(
            quantity_by_risk,
            quantity_by_exposure,
        )

        if quantity <= 0:
            return self._reject("calculated quantity is zero")

        notional = quantity * entry_price

        return RiskDecision(
            approved=True,
            quantity=quantity,
            risk_amount=risk_amount,
            notional=notional,
            reason="risk checks passed",
        )

    def record_trade(
        self,
        pnl: Decimal,
        *,
        trade_time: datetime | None = None,
    ) -> None:
        trade_time = trade_time or datetime.now(timezone.utc)

        self.state.daily_pnl += pnl
        self.state.last_trade_at = trade_time

        if pnl < 0:
            self.state.consecutive_losses += 1
        elif pnl > 0:
            self.state.consecutive_losses = 0

    def set_kill_switch(self, active: bool) -> None:
        self.state.kill_switch = active

    @staticmethod
    def _reject(reason: str) -> RiskDecision:
        return RiskDecision(
            approved=False,
            quantity=Decimal(0),
            risk_amount=Decimal(0),
            notional=Decimal(0),
            reason=reason,
        )

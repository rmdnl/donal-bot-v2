from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Signal:
    symbol: str
    action: str
    score: Decimal


class SignalEngine:
    def score_setup(
        self,
        symbol: str,
        ema_fast: Decimal,
        ema_slow: Decimal,
        rsi: Decimal,
        volume_ratio: Decimal,
    ) -> Signal:
        if not symbol:
            raise ValueError("symbol is required")

        if not 0 <= rsi <= 100:
            raise ValueError("rsi must be between 0 and 100")

        if volume_ratio < 0:
            raise ValueError(
                "volume ratio cannot be negative"
            )

        score = Decimal(0)

        if ema_fast > ema_slow:
            score += Decimal(40)

        if Decimal(55) <= rsi <= Decimal(65):
            score += Decimal(30)
        elif Decimal(50) <= rsi < Decimal(55):
            score += Decimal(15)

        if volume_ratio >= Decimal("1.5"):
            score += Decimal(30)
        elif volume_ratio >= Decimal(1):
            score += Decimal(20)
        elif volume_ratio >= Decimal("0.75"):
            score += Decimal(10)

        if score >= Decimal(75):
            action = "BUY"
        elif score >= Decimal(50):
            action = "WATCH"
        else:
            action = "WAIT"

        return Signal(
            symbol=symbol.upper(),
            action=action,
            score=score,
        )

    def evaluate(
        self,
        symbol: str,
        ema_fast: Decimal,
        ema_slow: Decimal,
        rsi: Decimal,
        volume_ratio: Decimal,
    ) -> Signal:
        if not symbol:
            raise ValueError("symbol is required")

        if not 0 <= rsi <= 100:
            raise ValueError("rsi must be between 0 and 100")

        if volume_ratio < 0:
            raise ValueError("volume ratio cannot be negative")

        if (
            ema_fast > ema_slow
            and Decimal(50) <= rsi <= Decimal(70)
            and volume_ratio >= Decimal(1)
        ):
            return Signal(
                symbol=symbol.upper(),
                action="BUY",
                score=Decimal(1),
            )

        return Signal(
            symbol=symbol.upper(),
            action="WAIT",
            score=Decimal(0),
        )

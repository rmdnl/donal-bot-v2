from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Signal:
    symbol: str
    action: str
    score: Decimal


class SignalEngine:
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

        if ema_fast > ema_slow and 50 <= rsi <= 70 and volume_ratio >= Decimal(1):
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

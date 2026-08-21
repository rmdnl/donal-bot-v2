from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.market.scanner import MarketSnapshot
from app.strategy.signal_engine import SignalEngine
from app.strategy.top_coin_selector import (
    Candidate,
    TopCoinSelector,
)


@dataclass(frozen=True)
class MarketIndicators:
    ema_fast: Decimal
    ema_slow: Decimal
    rsi: Decimal
    volume_ratio: Decimal


class MarketPipeline:
    def __init__(
        self,
        signal_engine: SignalEngine | None = None,
        selector: TopCoinSelector | None = None,
    ) -> None:
        self.signal_engine = signal_engine or SignalEngine()
        self.selector = selector or TopCoinSelector()

    def select(
        self,
        snapshots: list[MarketSnapshot],
        indicators: dict[str, MarketIndicators],
    ) -> Candidate | None:
        candidates: list[Candidate] = []

        for snapshot in snapshots:
            symbol = snapshot.symbol.upper()
            data = indicators.get(symbol)

            if data is None:
                continue

            signal = self.signal_engine.score_setup(
                symbol=symbol,
                ema_fast=data.ema_fast,
                ema_slow=data.ema_slow,
                rsi=data.rsi,
                volume_ratio=data.volume_ratio,
            )

            if signal.action == "BUY":
                candidates.append(
                    Candidate(
                        symbol=signal.symbol,
                        score=signal.score,
                    )
                )

        return self.selector.select(candidates)

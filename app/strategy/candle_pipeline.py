from __future__ import annotations

from dataclasses import dataclass

from app.indicators.indicator_engine import (
    Candle,
    IndicatorEngine,
)
from app.strategy.market_pipeline import MarketPipeline
from app.strategy.top_coin_selector import Candidate


@dataclass(frozen=True)
class CandleSet:
    symbol: str
    candles: list[Candle]


class CandleSignalPipeline:
    def __init__(
        self,
        indicator_engine: IndicatorEngine | None = None,
        market_pipeline: MarketPipeline | None = None,
    ) -> None:
        self.indicators = (
            indicator_engine or IndicatorEngine()
        )
        self.pipeline = (
            market_pipeline or MarketPipeline()
        )

    def select(
        self,
        candle_sets: list[CandleSet],
    ) -> Candidate | None:
        snapshots = []
        indicators = {}

        for candle_set in candle_sets:
            if not candle_set.candles:
                continue

            snapshot = self.indicators.calculate(
                candle_set.candles
            )

            last = candle_set.candles[-1]

            snapshots.append(
                {
                    "symbol": candle_set.symbol,
                    "price": last.close,
                    "volume": last.volume,
                }
            )

            indicators[
                candle_set.symbol.upper()
            ] = snapshot

        market_snapshots = [
            __import__(
                "app.market.scanner",
                fromlist=["MarketSnapshot"],
            ).MarketSnapshot(
                symbol=item["symbol"],
                price=item["price"],
                volume=item["volume"],
            )
            for item in snapshots
        ]

        return self.pipeline.select(
            market_snapshots,
            indicators,
        )

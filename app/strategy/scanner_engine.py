from __future__ import annotations

from dataclasses import dataclass

from app.exchange.candle_feed import CandleFeed
from app.strategy.candle_pipeline import CandleSet
from app.strategy.market_pipeline import MarketPipeline
from app.strategy.top_coin_selector import Candidate


@dataclass(frozen=True)
class ScanResult:
    candidate: Candidate | None
    scanned: int


class ScannerEngine:
    def __init__(
        self,
        candle_feed: CandleFeed,
        pipeline: MarketPipeline | None = None,
    ) -> None:
        self.candle_feed = candle_feed
        self.pipeline = pipeline or MarketPipeline()

    def scan(
        self,
        symbols: list[str],
        interval: str,
        limit: int = 100,
    ) -> ScanResult:
        candle_sets: list[CandleSet] = []
        scanned = 0

        for symbol in symbols:
            candles = self.candle_feed.fetch(
                symbol=symbol,
                interval=interval,
                limit=limit,
            )

            scanned += 1

            if not candles:
                continue

            candle_sets.append(
                CandleSet(
                    symbol=symbol.upper(),
                    candles=candles,
                )
            )

        candidate = self._select(candle_sets)

        return ScanResult(
            candidate=candidate,
            scanned=scanned,
        )

    def _select(
        self,
        candle_sets: list[CandleSet],
    ) -> Candidate | None:
        return self.pipeline.select(candle_sets)

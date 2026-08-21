from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.exchange.market_data import MarketData
from app.indicators.indicator_engine import Candle


class CandleFeedError(ValueError):
    pass


@dataclass(frozen=True)
class CandleFeed:
    market_data: MarketData

    def fetch(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
    ) -> list[Candle]:
        if not symbol.strip():
            raise CandleFeedError(
                "symbol cannot be empty"
            )

        if not interval.strip():
            raise CandleFeedError(
                "interval cannot be empty"
            )

        frame = self.market_data.closed_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        if frame.empty:
            return []

        return [
            Candle(
                close=Decimal(str(row["close"])),
                volume=Decimal(str(row["volume"])),
                open_time=(
                    int(row["open_time"].timestamp() * 1000)
                    if "open_time" in row.index
                    else 0
                ),
            )
            for _, row in frame.iterrows()
        ]

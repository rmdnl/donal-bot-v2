from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.exchange.binance_client import BinanceClient

KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]


@dataclass(frozen=True)
class MarketData:
    client: BinanceClient

    def klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
    ) -> pd.DataFrame:
        symbol = symbol.upper().strip()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")

        rows = self.client.get(
            "/api/v3/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            },
        )

        if not isinstance(rows, list):
            raise TypeError("Invalid kline response")

        frame = pd.DataFrame(rows, columns=KLINE_COLUMNS)

        if frame.empty:
            return frame

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "taker_buy_base",
            "taker_buy_quote",
        ]

        for column in numeric_columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

        frame["open_time"] = pd.to_datetime(
            frame["open_time"],
            unit="ms",
            utc=True,
        )

        frame["close_time"] = pd.to_datetime(
            frame["close_time"],
            unit="ms",
            utc=True,
        )

        frame["trades"] = pd.to_numeric(
            frame["trades"],
            errors="coerce",
        ).astype("Int64")

        frame = frame.dropna(
            subset=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

        frame = frame.drop_duplicates(
            subset=["open_time"],
            keep="last",
        )

        frame = frame.sort_values("open_time").reset_index(drop=True)

        return frame

    def closed_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        now: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        frame = self.klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )

        if frame.empty:
            return frame

        current_time = now or pd.Timestamp.now(tz="UTC")

        return frame.loc[
            frame["close_time"] <= current_time
        ].reset_index(drop=True)

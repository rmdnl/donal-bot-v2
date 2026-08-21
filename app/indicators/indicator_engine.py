from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class IndicatorError(ValueError):
    pass


@dataclass(frozen=True)
class Candle:
    close: Decimal
    volume: Decimal
    open_time: int = 0


@dataclass(frozen=True)
class IndicatorSnapshot:
    ema_fast: Decimal
    ema_slow: Decimal
    rsi: Decimal
    volume_ratio: Decimal


class IndicatorEngine:
    def __init__(
        self,
        ema_fast_period: int = 9,
        ema_slow_period: int = 21,
        rsi_period: int = 14,
        volume_period: int = 20,
    ) -> None:
        if ema_fast_period <= 0:
            raise IndicatorError("fast EMA period must be positive")

        if ema_slow_period <= 0:
            raise IndicatorError("slow EMA period must be positive")

        if rsi_period <= 0:
            raise IndicatorError("RSI period must be positive")

        if volume_period <= 0:
            raise IndicatorError("volume period must be positive")

        if ema_fast_period >= ema_slow_period:
            raise IndicatorError(
                "fast EMA period must be smaller than slow EMA period"
            )

        self.ema_fast_period = ema_fast_period
        self.ema_slow_period = ema_slow_period
        self.rsi_period = rsi_period
        self.volume_period = volume_period

    @staticmethod
    def ema(
        values: list[Decimal],
        period: int,
    ) -> Decimal:
        if len(values) < period:
            raise IndicatorError("not enough data for EMA")

        multiplier = Decimal(2) / Decimal(period + 1)

        value = sum(
            values[:period],
            Decimal(0),
        ) / Decimal(period)

        for price in values[period:]:
            value = (
                (price - value) * multiplier
            ) + value

        return value

    @staticmethod
    def rsi(
        values: list[Decimal],
        period: int,
    ) -> Decimal:
        if len(values) < period + 1:
            raise IndicatorError("not enough data for RSI")

        gains = Decimal(0)
        losses = Decimal(0)

        for index in range(1, period + 1):
            change = values[index] - values[index - 1]

            if change > 0:
                gains += change
            elif change < 0:
                losses += abs(change)

        average_gain = gains / Decimal(period)
        average_loss = losses / Decimal(period)

        for index in range(period + 1, len(values)):
            change = values[index] - values[index - 1]

            gain = max(change, Decimal(0))
            loss = max(-change, Decimal(0))

            average_gain = (
                (average_gain * Decimal(period - 1)) + gain
            ) / Decimal(period)

            average_loss = (
                (average_loss * Decimal(period - 1)) + loss
            ) / Decimal(period)

        if average_loss == 0:
            return Decimal(100)

        if average_gain == 0:
            return Decimal(0)

        rs = average_gain / average_loss

        return Decimal(100) - (
            Decimal(100) / (Decimal(1) + rs)
        )

    @staticmethod
    def volume_ratio(
        volumes: list[Decimal],
        period: int,
    ) -> Decimal:
        if len(volumes) < period + 1:
            raise IndicatorError(
                "not enough data for volume ratio"
            )

        average = sum(
            volumes[-period - 1:-1],
            Decimal(0),
        ) / Decimal(period)

        if average <= 0:
            return Decimal(0)

        return volumes[-1] / average

    def calculate(
        self,
        candles: list[Candle],
    ) -> IndicatorSnapshot:
        if not candles:
            raise IndicatorError("candles are required")

        closes = [candle.close for candle in candles]
        volumes = [candle.volume for candle in candles]

        if any(value <= 0 for value in closes):
            raise IndicatorError("close must be positive")

        if any(value < 0 for value in volumes):
            raise IndicatorError("volume cannot be negative")

        required = max(
            self.ema_slow_period,
            self.rsi_period + 1,
            self.volume_period + 1,
        )

        if len(candles) < required:
            raise IndicatorError("not enough candle data")

        return IndicatorSnapshot(
            ema_fast=self.ema(
                closes,
                self.ema_fast_period,
            ),
            ema_slow=self.ema(
                closes,
                self.ema_slow_period,
            ),
            rsi=self.rsi(
                closes,
                self.rsi_period,
            ),
            volume_ratio=self.volume_ratio(
                volumes,
                self.volume_period,
            ),
        )

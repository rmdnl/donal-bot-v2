from decimal import Decimal

from app.indicators.indicator_engine import (
    Candle,
    IndicatorSnapshot,
)
from app.strategy.candle_pipeline import (
    CandleSet,
    CandleSignalPipeline,
)


class FakeIndicatorEngine:
    def __init__(self, snapshots):
        self.snapshots = snapshots

    def calculate(self, candles):
        return self.snapshots


def test_candle_pipeline_selects_buy_candidate():
    engine = FakeIndicatorEngine(
        IndicatorSnapshot(
            ema_fast=Decimal(101),
            ema_slow=Decimal(100),
            rsi=Decimal(60),
            volume_ratio=Decimal("1.5"),
        )
    )

    pipeline = CandleSignalPipeline(
        indicator_engine=engine,
    )

    result = pipeline.select(
        [
            CandleSet(
                "BTCUSDT",
                [
                    Candle(
                        Decimal(100),
                        Decimal(100),
                    )
                ],
            )
        ]
    )

    assert result is not None
    assert result.symbol == "BTCUSDT"
    assert result.score == Decimal(100)


def test_candle_pipeline_skips_empty_candles():
    pipeline = CandleSignalPipeline()

    result = pipeline.select(
        [
            CandleSet("BTCUSDT", []),
        ]
    )

    assert result is None


def test_candle_pipeline_selects_best_coin():
    btc_engine = FakeIndicatorEngine(
        IndicatorSnapshot(
            ema_fast=Decimal(101),
            ema_slow=Decimal(100),
            rsi=Decimal(60),
            volume_ratio=Decimal("1.5"),
        )
    )

    pipeline = CandleSignalPipeline(
        indicator_engine=btc_engine,
    )

    result = pipeline.select(
        [
            CandleSet(
                "BTCUSDT",
                [
                    Candle(
                        Decimal(100),
                        Decimal(100),
                    )
                ],
            ),
        ]
    )

    assert result is not None
    assert result.symbol == "BTCUSDT"
    assert result.score == Decimal(100)

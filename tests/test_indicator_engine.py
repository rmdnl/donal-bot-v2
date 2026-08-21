from decimal import Decimal

import pytest

from app.indicators.indicator_engine import (
    Candle,
    IndicatorEngine,
    IndicatorError,
)


def candles(prices, volumes=None):
    if volumes is None:
        volumes = [Decimal(100)] * len(prices)

    return [
        Candle(
            Decimal(str(price)),
            Decimal(str(volume)),
        )
        for price, volume in zip(prices, volumes)
    ]


def test_ema():
    result = IndicatorEngine.ema(
        [
            Decimal(1),
            Decimal(2),
            Decimal(3),
        ],
        3,
    )

    assert result == Decimal(2)


def test_ema_rejects_insufficient_data():
    with pytest.raises(IndicatorError):
        IndicatorEngine.ema(
            [Decimal(1), Decimal(2)],
            3,
        )


def test_rsi_strong_uptrend():
    result = IndicatorEngine.rsi(
        [Decimal(str(x)) for x in range(1, 20)],
        14,
    )

    assert result == Decimal(100)


def test_rsi_rejects_insufficient_data():
    with pytest.raises(IndicatorError):
        IndicatorEngine.rsi(
            [Decimal(1)] * 14,
            14,
        )


def test_volume_ratio():
    result = IndicatorEngine.volume_ratio(
        [Decimal(100)] * 20 + [Decimal(200)],
        20,
    )

    assert result == Decimal(2)


def test_calculate():
    engine = IndicatorEngine()

    prices = [
        Decimal(str(100 + x))
        for x in range(30)
    ]

    volumes = [Decimal(100)] * 29 + [Decimal(200)]

    result = engine.calculate(
        candles(prices, volumes)
    )

    assert result.ema_fast > result.ema_slow
    assert result.rsi == Decimal(100)
    assert result.volume_ratio == Decimal(2)


def test_invalid_periods():
    with pytest.raises(IndicatorError):
        IndicatorEngine(
            ema_fast_period=21,
            ema_slow_period=9,
        )


def test_negative_volume_rejected():
    engine = IndicatorEngine()

    data = candles(
        [100 + x for x in range(30)],
        [100] * 29 + [-1],
    )

    with pytest.raises(IndicatorError):
        engine.calculate(data)

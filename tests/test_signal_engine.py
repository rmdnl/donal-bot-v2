from decimal import Decimal

import pytest

from app.strategy.signal_engine import SignalEngine


def test_buy_signal():
    signal = SignalEngine().evaluate(
        "btcusdt",
        Decimal(101),
        Decimal(100),
        Decimal(60),
        Decimal("1.5"),
    )

    assert signal.symbol == "BTCUSDT"
    assert signal.action == "BUY"
    assert signal.score == Decimal(1)


def test_wait_when_trend_is_bearish():
    signal = SignalEngine().evaluate(
        "BTCUSDT",
        Decimal(99),
        Decimal(100),
        Decimal(60),
        Decimal("1.5"),
    )

    assert signal.action == "WAIT"


def test_wait_when_rsi_is_weak():
    signal = SignalEngine().evaluate(
        "BTCUSDT",
        Decimal(101),
        Decimal(100),
        Decimal(45),
        Decimal("1.5"),
    )

    assert signal.action == "WAIT"


def test_wait_when_volume_is_low():
    signal = SignalEngine().evaluate(
        "BTCUSDT",
        Decimal(101),
        Decimal(100),
        Decimal(60),
        Decimal("0.5"),
    )

    assert signal.action == "WAIT"


def test_invalid_rsi_rejected():
    with pytest.raises(ValueError):
        SignalEngine().evaluate(
            "BTCUSDT",
            Decimal(101),
            Decimal(100),
            Decimal(101),
            Decimal(1),
        )


def test_signal_scoring_strong_setup():
    engine = SignalEngine()

    signal = engine.score_setup(
        symbol="BTCUSDT",
        ema_fast=Decimal(101),
        ema_slow=Decimal(100),
        rsi=Decimal(60),
        volume_ratio=Decimal("1.5"),
    )

    assert signal.action == "BUY"
    assert signal.score >= Decimal(75)


def test_signal_scoring_watch_setup():
    engine = SignalEngine()

    signal = engine.score_setup(
        symbol="BTCUSDT",
        ema_fast=Decimal(101),
        ema_slow=Decimal(100),
        rsi=Decimal(52),
        volume_ratio=Decimal("0.8"),
    )

    assert signal.action == "WATCH"
    assert Decimal(50) <= signal.score < Decimal(75)


def test_signal_scoring_weak_setup():
    engine = SignalEngine()

    signal = engine.score_setup(
        symbol="BTCUSDT",
        ema_fast=Decimal(99),
        ema_slow=Decimal(100),
        rsi=Decimal(45),
        volume_ratio=Decimal("0.5"),
    )

    assert signal.action == "WAIT"
    assert signal.score < Decimal(50)

from decimal import Decimal

from app.market.scanner import MarketSnapshot
from app.strategy.market_pipeline import (
    MarketIndicators,
    MarketPipeline,
)


def test_pipeline_selects_best_buy_candidate():
    snapshots = [
        MarketSnapshot(
            "BTCUSDT",
            Decimal(100000),
            Decimal(100),
        ),
        MarketSnapshot(
            "ETHUSDT",
            Decimal(4000),
            Decimal(200),
        ),
    ]

    indicators = {
        "BTCUSDT": MarketIndicators(
            Decimal(101),
            Decimal(100),
            Decimal(52),
            Decimal("1.5"),
        ),
        "ETHUSDT": MarketIndicators(
            Decimal(4010),
            Decimal(4000),
            Decimal(58),
            Decimal(2),
        ),
    }

    result = MarketPipeline().select(
        snapshots,
        indicators,
    )

    assert result is not None
    assert result.symbol == "ETHUSDT"
    assert result.score == Decimal(100)


def test_pipeline_ignores_watch_and_wait():
    snapshots = [
        MarketSnapshot(
            "BTCUSDT",
            Decimal(100000),
            Decimal(100),
        ),
        MarketSnapshot(
            "ETHUSDT",
            Decimal(4000),
            Decimal(200),
        ),
    ]

    indicators = {
        "BTCUSDT": MarketIndicators(
            Decimal(101),
            Decimal(100),
            Decimal(52),
            Decimal("0.8"),
        ),
        "ETHUSDT": MarketIndicators(
            Decimal(3990),
            Decimal(4000),
            Decimal(45),
            Decimal("0.5"),
        ),
    }

    assert MarketPipeline().select(
        snapshots,
        indicators,
    ) is None


def test_pipeline_skips_missing_indicators():
    snapshots = [
        MarketSnapshot(
            "BTCUSDT",
            Decimal(100000),
            Decimal(100),
        ),
    ]

    assert MarketPipeline().select(
        snapshots,
        {},
    ) is None

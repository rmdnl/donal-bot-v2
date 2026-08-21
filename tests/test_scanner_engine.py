from decimal import Decimal
from unittest.mock import Mock

from app.exchange.candle_feed import CandleFeed
from app.indicators.indicator_engine import Candle
from app.strategy.scanner_engine import ScannerEngine


def test_scanner_scans_multiple_symbols():
    feed = Mock(spec=CandleFeed)

    feed.fetch.side_effect = [
        [
            Candle(
                Decimal(100),
                Decimal(100),
            )
        ],
        [
            Candle(
                Decimal(200),
                Decimal(200),
            )
        ],
    ]

    pipeline = Mock()
    pipeline.select.return_value = None

    engine = ScannerEngine(
        candle_feed=feed,
        pipeline=pipeline,
    )

    result = engine.scan(
        ["BTCUSDT", "ETHUSDT"],
        "15m",
    )

    assert result.candidate is None
    assert result.scanned == 2

    assert feed.fetch.call_count == 2

    pipeline.select.assert_called_once()


def test_scanner_skips_symbol_without_candles():
    feed = Mock(spec=CandleFeed)

    feed.fetch.side_effect = [
        [],
        [
            Candle(
                Decimal(200),
                Decimal(200),
            )
        ],
    ]

    pipeline = Mock()
    pipeline.select.return_value = None

    result = ScannerEngine(
        feed,
        pipeline,
    ).scan(
        ["BTCUSDT", "ETHUSDT"],
        "15m",
    )

    assert result.scanned == 2

    candle_sets = pipeline.select.call_args.args[0]

    assert len(candle_sets) == 1
    assert candle_sets[0].symbol == "ETHUSDT"


def test_scanner_returns_pipeline_candidate():
    feed = Mock(spec=CandleFeed)

    feed.fetch.return_value = [
        Candle(
            Decimal(100),
            Decimal(100),
        )
    ]

    candidate = object()

    pipeline = Mock()
    pipeline.select.return_value = candidate

    result = ScannerEngine(
        feed,
        pipeline,
    ).scan(
        ["BTCUSDT"],
        "15m",
    )

    assert result.candidate is candidate
    assert result.scanned == 1

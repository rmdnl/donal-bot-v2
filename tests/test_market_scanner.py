from decimal import Decimal

import pytest

from app.market.scanner import (
    MarketDataError,
    MarketScanner,
    MarketSnapshot,
)


def test_symbols_are_normalized():
    scanner = MarketScanner(
        ["btcusdt", "ETHUSDT", "btcusdt"]
    )

    assert scanner.symbols == (
        "BTCUSDT",
        "ETHUSDT",
    )


def test_empty_symbols_rejected():
    with pytest.raises(MarketDataError):
        MarketScanner([])


def test_rank_by_volume():
    scanner = MarketScanner(
        ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    )

    snapshots = [
        MarketSnapshot(
            "BTCUSDT",
            Decimal(100000),
            Decimal(100),
        ),
        MarketSnapshot(
            "ETHUSDT",
            Decimal(4000),
            Decimal(500),
        ),
        MarketSnapshot(
            "BNBUSDT",
            Decimal(800),
            Decimal(250),
        ),
    ]

    result = scanner.rank_by_volume(snapshots)

    assert [x.symbol for x in result] == [
        "ETHUSDT",
        "BNBUSDT",
        "BTCUSDT",
    ]


def test_unknown_symbol_is_ignored():
    scanner = MarketScanner(["BTCUSDT"])

    result = scanner.rank_by_volume(
        [
            MarketSnapshot(
                "ETHUSDT",
                Decimal(4000),
                Decimal(999),
            ),
        ]
    )

    assert result == []


def test_invalid_price_is_ignored():
    scanner = MarketScanner(["BTCUSDT"])

    result = scanner.rank_by_volume(
        [
            MarketSnapshot(
                "BTCUSDT",
                Decimal(0),
                Decimal(999),
            ),
        ]
    )

    assert result == []

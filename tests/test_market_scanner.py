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


def test_rank_by_signal_score():
    scanner = MarketScanner(
        ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    )

    scored = [
        ("BTCUSDT", Decimal(65)),
        ("ETHUSDT", Decimal(85)),
        ("BNBUSDT", Decimal(75)),
    ]

    result = scanner.rank_by_signal_score(scored)

    assert result == [
        ("ETHUSDT", Decimal(85)),
        ("BNBUSDT", Decimal(75)),
        ("BTCUSDT", Decimal(65)),
    ]


def test_rank_by_signal_score_has_limit():
    scanner = MarketScanner(
        ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    )

    scored = [
        ("BTCUSDT", Decimal(65)),
        ("ETHUSDT", Decimal(85)),
        ("BNBUSDT", Decimal(75)),
    ]

    result = scanner.rank_by_signal_score(
        scored,
        limit=2,
    )

    assert result == [
        ("ETHUSDT", Decimal(85)),
        ("BNBUSDT", Decimal(75)),
    ]

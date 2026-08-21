from decimal import Decimal
from unittest.mock import Mock

import pandas as pd
import pytest

from app.exchange.candle_feed import (
    CandleFeed,
    CandleFeedError,
)
from app.indicators.indicator_engine import Candle


def test_fetch_converts_closed_klines_to_candles():
    market_data = Mock()

    market_data.closed_klines.return_value = pd.DataFrame(
        {
            "close": [100.5, 101.25],
            "volume": [10.0, 20.0],
        }
    )

    feed = CandleFeed(market_data)

    result = feed.fetch(
        "BTCUSDT",
        "15m",
    )

    assert result == [
        Candle(
            close=Decimal("100.5"),
            volume=Decimal("10.0"),
        ),
        Candle(
            close=Decimal("101.25"),
            volume=Decimal("20.0"),
        ),
    ]

    market_data.closed_klines.assert_called_once_with(
        symbol="BTCUSDT",
        interval="15m",
        limit=100,
    )


def test_empty_market_data_returns_empty_list():
    market_data = Mock()
    market_data.closed_klines.return_value = pd.DataFrame()

    result = CandleFeed(
        market_data
    ).fetch("BTCUSDT", "15m")

    assert result == []


def test_empty_symbol_rejected():
    with pytest.raises(CandleFeedError):
        CandleFeed(Mock()).fetch("", "15m")


def test_empty_interval_rejected():
    with pytest.raises(CandleFeedError):
        CandleFeed(Mock()).fetch("BTCUSDT", "")


def test_decimal_precision_is_preserved():
    market_data = Mock()

    market_data.closed_klines.return_value = pd.DataFrame(
        {
            "close": ["123.45678901"],
            "volume": ["987.65432109"],
        }
    )

    result = CandleFeed(
        market_data
    ).fetch("BTCUSDT", "15m")

    assert result[0].close == Decimal(
        "123.45678901"
    )

    assert result[0].volume == Decimal(
        "987.65432109"
    )

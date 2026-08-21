from decimal import Decimal

import pytest

from app.strategy.top_coin_selector import (
    Candidate,
    SelectionError,
    TopCoinSelector,
)


def test_selects_highest_score():
    selector = TopCoinSelector()

    result = selector.select(
        [
            Candidate("BTCUSDT", Decimal(78)),
            Candidate("ETHUSDT", Decimal(91)),
            Candidate("BNBUSDT", Decimal(84)),
        ]
    )

    assert result == Candidate(
        "ETHUSDT",
        Decimal(91),
    )


def test_ignores_below_threshold():
    selector = TopCoinSelector(
        minimum_score=Decimal(80)
    )

    result = selector.select(
        [
            Candidate("BTCUSDT", Decimal(79)),
            Candidate("ETHUSDT", Decimal(85)),
        ]
    )

    assert result == Candidate(
        "ETHUSDT",
        Decimal(85),
    )


def test_returns_none_when_no_candidate_qualifies():
    selector = TopCoinSelector()

    result = selector.select(
        [
            Candidate("BTCUSDT", Decimal(60)),
            Candidate("ETHUSDT", Decimal(74)),
        ]
    )

    assert result is None


def test_invalid_threshold_rejected():
    with pytest.raises(SelectionError):
        TopCoinSelector(
            minimum_score=Decimal(101)
        )

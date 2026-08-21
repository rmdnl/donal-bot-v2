from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.strategy.scanner_engine import (
    ScannerEngine,
    ScanResult,
)
from app.strategy.top_coin_selector import Candidate
from app.trading.trading_loop import TradingLoop


def test_dry_run_buy():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "BTCUSDT",
            Decimal(90),
        ),
        scanned=3,
    )

    loop = TradingLoop(
        scanner,
        dry_run=True,
    )

    decision = loop.run_once(
        ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        "15m",
    )

    assert decision.symbol == "BTCUSDT"
    assert decision.score == Decimal(90)
    assert decision.action == "DRY_RUN_BUY"


def test_no_candidate_waits():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=None,
        scanned=3,
    )

    loop = TradingLoop(scanner)

    decision = loop.run_once(
        ["BTCUSDT"],
        "15m",
    )

    assert decision.symbol is None
    assert decision.action == "WAIT"


def test_below_threshold_waits():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "BTCUSDT",
            Decimal(70),
        ),
        scanned=1,
    )

    loop = TradingLoop(
        scanner,
        minimum_score=Decimal(75),
    )

    decision = loop.run_once(
        ["BTCUSDT"],
        "15m",
    )

    assert decision.action == "WAIT"


def test_live_mode_returns_buy_decision():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "ETHUSDT",
            Decimal(85),
        ),
        scanned=2,
    )

    loop = TradingLoop(
        scanner,
        dry_run=False,
    )

    decision = loop.run_once(
        ["ETHUSDT"],
        "15m",
    )

    assert decision.action == "BUY"


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        TradingLoop(
            Mock(spec=ScannerEngine),
            minimum_score=Decimal(101),
        )

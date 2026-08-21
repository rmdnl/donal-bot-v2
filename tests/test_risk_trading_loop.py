from decimal import Decimal
from unittest.mock import Mock

from app.risk.risk_manager import RiskConfig, RiskManager
from app.strategy.scanner_engine import (
    ScannerEngine,
    ScanResult,
)
from app.strategy.top_coin_selector import Candidate
from app.trading.risk_trading_loop import RiskTradingLoop


def test_approved_candidate_reaches_dry_run_buy():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "BTCUSDT",
            Decimal(90),
        ),
        scanned=3,
    )

    risk = RiskManager(RiskConfig())

    loop = RiskTradingLoop(
        scanner,
        risk,
        dry_run=True,
    )

    result = loop.run_once(
        ["BTCUSDT"],
        "15m",
        quantity=Decimal("0.005"),
        price=Decimal(100000),
        risk_amount=Decimal(5),
    )

    assert result.action == "DRY_RUN_BUY"
    assert result.symbol == "BTCUSDT"
    assert result.reason == "risk approved"


def test_excessive_quantity_is_rejected():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "BTCUSDT",
            Decimal(90),
        ),
        scanned=1,
    )

    risk = RiskManager(RiskConfig())

    loop = RiskTradingLoop(scanner, risk)

    result = loop.run_once(
        ["BTCUSDT"],
        "15m",
        quantity=Decimal("0.02"),
        price=Decimal(100000),
        risk_amount=Decimal(5),
    )

    assert result.action == "RISK_REJECT"
    assert "quantity" in result.reason


def test_kill_switch_blocks_buy():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "ETHUSDT",
            Decimal(95),
        ),
        scanned=1,
    )

    risk = RiskManager(RiskConfig())
    risk.set_kill_switch(True)

    loop = RiskTradingLoop(scanner, risk)

    result = loop.run_once(
        ["ETHUSDT"],
        "15m",
        quantity=Decimal("0.001"),
        price=Decimal(4000),
        risk_amount=Decimal(2),
    )

    assert result.action == "RISK_REJECT"
    assert "kill switch" in result.reason


def test_no_candidate_does_not_call_risk():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=None,
        scanned=3,
    )

    risk = Mock(spec=RiskManager)

    loop = RiskTradingLoop(scanner, risk)

    result = loop.run_once(
        ["BTCUSDT"],
        "15m",
        quantity=Decimal("0.001"),
        price=Decimal(100000),
        risk_amount=Decimal(1),
    )

    assert result.action == "WAIT"
    risk.evaluate.assert_not_called()

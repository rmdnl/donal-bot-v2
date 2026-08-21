from decimal import Decimal
from unittest.mock import Mock

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
    ExecutionAdapter,
)
from app.risk.risk_manager import RiskConfig, RiskManager
from app.strategy.scanner_engine import (
    ScannerEngine,
    ScanResult,
)
from app.strategy.top_coin_selector import Candidate
from app.trading.execution_loop import ExecutionTradingLoop


def scanner_with_candidate():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "BTCUSDT",
            Decimal(90),
        ),
        scanned=1,
    )
    return scanner


def test_dry_run_does_not_execute():
    scanner = scanner_with_candidate()
    risk = RiskManager(RiskConfig())
    execution = Mock(spec=ExecutionAdapter)

    loop = ExecutionTradingLoop(
        scanner,
        risk,
        execution,
        dry_run=True,
    )

    result = loop.run_once(
        ["BTCUSDT"],
        "15m",
        Decimal("0.005"),
        Decimal(100000),
        Decimal(5),
        "DNL-001",
    )

    assert result.action == "DRY_RUN_BUY"
    execution.submit_buy.assert_not_called()


def test_risk_reject_never_executes():
    scanner = scanner_with_candidate()
    risk = RiskManager(RiskConfig())
    execution = Mock(spec=ExecutionAdapter)

    loop = ExecutionTradingLoop(
        scanner,
        risk,
        execution,
    )

    result = loop.run_once(
        ["BTCUSDT"],
        "15m",
        Decimal("0.02"),
        Decimal(100000),
        Decimal(5),
        "DNL-002",
    )

    assert result.action == "RISK_REJECT"
    execution.submit_buy.assert_not_called()


def test_live_mode_executes_approved_trade():
    scanner = scanner_with_candidate()
    risk = RiskManager(RiskConfig())
    execution = Mock(spec=ExecutionAdapter)

    execution.submit_buy.return_value = ExchangeOrder(
        client_order_id="DNL-003",
        exchange_order_id="12345",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.005,
        executed_quantity=0.005,
    )

    loop = ExecutionTradingLoop(
        scanner,
        risk,
        execution,
        dry_run=False,
    )

    result = loop.run_once(
        ["BTCUSDT"],
        "15m",
        Decimal("0.005"),
        Decimal(100000),
        Decimal(5),
        "DNL-003",
    )

    assert result.action == "BUY"
    assert result.order is not None
    assert result.order.status == ExchangeOrderStatus.FILLED

    execution.submit_buy.assert_called_once_with(
        symbol="BTCUSDT",
        quantity=0.005,
        client_order_id="DNL-003",
    )


def test_no_candidate_does_not_touch_risk_or_execution():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=None,
        scanned=1,
    )

    risk = Mock(spec=RiskManager)
    execution = Mock(spec=ExecutionAdapter)

    loop = ExecutionTradingLoop(
        scanner,
        risk,
        execution,
    )

    result = loop.run_once(
        ["BTCUSDT"],
        "15m",
        Decimal("0.005"),
        Decimal(100000),
        Decimal(5),
        "DNL-004",
    )

    assert result.action == "WAIT"
    risk.evaluate.assert_not_called()
    execution.submit_buy.assert_not_called()

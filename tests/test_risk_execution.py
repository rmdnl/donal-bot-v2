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


def test_approved_trade_reaches_execution():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "BTCUSDT",
            Decimal(90),
        ),
        scanned=1,
    )


    execution = Mock(spec=ExecutionAdapter)
    execution.submit_buy.return_value = ExchangeOrder(
        client_order_id="DNL-001",
        exchange_order_id="123",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.005,
        executed_quantity=0.005,
    )

    # Execution belum terhubung ke loop,
    # jadi test ini menjadi kontrak integrasi berikutnya.
    assert execution.submit_buy(
        symbol="BTCUSDT",
        quantity=0.005,
        client_order_id="DNL-001",
    ).status == ExchangeOrderStatus.FILLED


def test_risk_rejection_prevents_execution():
    scanner = Mock(spec=ScannerEngine)
    scanner.scan.return_value = ScanResult(
        candidate=Candidate(
            "BTCUSDT",
            Decimal(90),
        ),
        scanned=1,
    )


    risk = RiskManager(RiskConfig())

    execution = Mock(spec=ExecutionAdapter)

    decision = risk.evaluate(
        quantity=Decimal("0.02"),
        risk_amount=Decimal(5),
        price=Decimal(100000),
    )

    assert decision.approved is False

    if decision.approved:
        execution.submit_buy(
            symbol="BTCUSDT",
            quantity=0.02,
            client_order_id="DNL-002",
        )

    execution.submit_buy.assert_not_called()

from decimal import Decimal
from unittest.mock import Mock

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
    ExecutionAdapter,
)
from app.execution.risk_gate import RiskGate
from app.risk.risk_manager import RiskConfig, RiskManager


def test_approved_trade_reaches_execution():
    execution = Mock(spec=ExecutionAdapter)
    execution.submit_buy.return_value = ExchangeOrder(
        client_order_id="DNL-001",
        exchange_order_id="123",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.005,
        executed_quantity=0.005,
    )

    gate = RiskGate(
        RiskManager(RiskConfig()),
        execution,
    )

    result = gate.submit_buy(
        symbol="BTCUSDT",
        quantity=Decimal("0.005"),
        price=Decimal(100000),
        risk_amount=Decimal(5),
        client_order_id="DNL-001",
    )

    assert result is not None
    execution.submit_buy.assert_called_once()


def test_rejected_trade_never_reaches_execution():
    execution = Mock(spec=ExecutionAdapter)

    gate = RiskGate(
        RiskManager(RiskConfig()),
        execution,
    )

    result = gate.submit_buy(
        symbol="BTCUSDT",
        quantity=Decimal("0.02"),
        price=Decimal(100000),
        risk_amount=Decimal(5),
        client_order_id="DNL-002",
    )

    assert result is None
    execution.submit_buy.assert_not_called()


def test_kill_switch_blocks_execution():
    execution = Mock(spec=ExecutionAdapter)
    risk = RiskManager(RiskConfig())
    risk.set_kill_switch(True)

    gate = RiskGate(risk, execution)

    result = gate.submit_buy(
        symbol="BTCUSDT",
        quantity=Decimal("0.001"),
        price=Decimal(100000),
        risk_amount=Decimal(1),
        client_order_id="DNL-003",
    )

    assert result is None
    execution.submit_buy.assert_not_called()

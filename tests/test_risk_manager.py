from decimal import Decimal

from app.risk.risk_manager import (
    RiskConfig,
    RiskConfigError,
    RiskManager,
)


def test_approve_valid_trade() -> None:
    manager = RiskManager(RiskConfig())

    decision = manager.evaluate(
        quantity=Decimal("0.005"),
        risk_amount=Decimal(5),
        price=Decimal(100000),
    )

    assert decision.approved is True
    assert decision.quantity == Decimal("0.005")
    assert decision.risk_amount == Decimal(5)
    assert decision.notional == Decimal(500)
    assert decision.reason == "approved"


def test_reject_excessive_quantity() -> None:
    manager = RiskManager(RiskConfig())

    decision = manager.evaluate(
        quantity=Decimal("0.02"),
        risk_amount=Decimal(5),
        price=Decimal(100000),
    )

    assert decision.approved is False
    assert "quantity" in decision.reason


def test_reject_excessive_risk() -> None:
    manager = RiskManager(RiskConfig())

    decision = manager.evaluate(
        quantity=Decimal("0.005"),
        risk_amount=Decimal(11),
        price=Decimal(100000),
    )

    assert decision.approved is False
    assert "risk" in decision.reason


def test_kill_switch_rejects_trade() -> None:
    manager = RiskManager(RiskConfig())
    manager.set_kill_switch(True)

    decision = manager.evaluate(
        quantity=Decimal("0.001"),
        risk_amount=Decimal(1),
        price=Decimal(100000),
    )

    assert decision.approved is False
    assert "kill switch" in decision.reason


def test_invalid_risk_config() -> None:
    try:
        RiskConfig(
            max_risk_amount=Decimal(0),
        )
    except RiskConfigError:
        pass
    else:
        raise AssertionError(
            "Expected invalid risk configuration"
        )

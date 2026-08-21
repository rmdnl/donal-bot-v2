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


def test_daily_loss_limit() -> None:
    manager = RiskManager(
        RiskConfig(max_daily_loss=Decimal(10))
    )

    manager.record_realized_pnl(Decimal(-10))

    decision = manager.evaluate(
        Decimal("0.001"),
        Decimal(1),
        Decimal(100000),
    )

    assert decision.approved is False
    assert "daily loss" in decision.reason


def test_consecutive_loss_limit() -> None:
    manager = RiskManager(
        RiskConfig(max_consecutive_losses=2)
    )

    manager.record_realized_pnl(Decimal(-1))
    manager.record_realized_pnl(Decimal(-1))

    decision = manager.evaluate(
        Decimal("0.001"),
        Decimal(1),
        Decimal(100000),
    )

    assert decision.approved is False
    assert "consecutive" in decision.reason


def test_profit_resets_consecutive_losses() -> None:
    manager = RiskManager(
        RiskConfig(max_consecutive_losses=2)
    )

    manager.record_realized_pnl(Decimal(-1))
    manager.record_realized_pnl(Decimal(2))

    decision = manager.evaluate(
        Decimal("0.001"),
        Decimal(1),
        Decimal(100000),
    )

    assert decision.approved is True


def test_daily_stats_reset() -> None:
    manager = RiskManager(RiskConfig())

    manager.record_realized_pnl(Decimal(-5))
    manager.reset_daily_stats()

    assert manager.daily_realized_loss == Decimal(0)
    assert manager.consecutive_losses == 0

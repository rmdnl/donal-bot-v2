from decimal import Decimal

import pytest

from app.execution.order_plan import (
    OrderPlan,
    OrderPlanError,
)


def make_plan(**overrides):
    values = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": Decimal("0.01"),
        "entry_price": Decimal(100),
        "stop_price": Decimal(98),
        "take_profit_price": Decimal(104),
        "strategy": "trend_pullback",
        "signal_id": "sig-001",
    }

    values.update(overrides)
    return OrderPlan(**values)


def test_valid_plan():
    plan = make_plan()

    assert plan.symbol == "BTCUSDT"
    assert plan.risk_per_unit == Decimal(2)
    assert plan.risk_amount == Decimal("0.02")
    assert plan.notional == Decimal(1)
    assert plan.reward_per_unit == Decimal(4)
    assert plan.reward_risk_ratio == Decimal(2)


def test_rejects_invalid_side():
    with pytest.raises(OrderPlanError):
        make_plan(side="HOLD")


def test_rejects_zero_quantity():
    with pytest.raises(OrderPlanError):
        make_plan(quantity=Decimal(0))


def test_rejects_buy_stop_above_entry():
    with pytest.raises(OrderPlanError):
        make_plan(stop_price=Decimal(101))


def test_rejects_buy_target_below_entry():
    with pytest.raises(OrderPlanError):
        make_plan(take_profit_price=Decimal(99))


def test_requires_signal_id():
    with pytest.raises(OrderPlanError):
        make_plan(signal_id="")


def test_requires_strategy():
    with pytest.raises(OrderPlanError):
        make_plan(strategy="")


def test_reward_risk_ratio():
    plan = make_plan(
        entry_price=Decimal(200),
        stop_price=Decimal(195),
        take_profit_price=Decimal(215),
    )

    assert plan.reward_risk_ratio == Decimal(3)

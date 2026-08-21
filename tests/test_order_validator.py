from decimal import Decimal

import pytest

from app.exchange.order_validator import (
    OrderValidationError,
    OrderValidator,
    SymbolRules,
)

RULES = SymbolRules(
    min_qty=Decimal("0.00001"),
    step_size=Decimal("0.00001"),
    min_notional=Decimal(5),
)


def test_valid_order():
    result = OrderValidator().validate(
        quantity=Decimal("0.00123"),
        price=Decimal(100000),
        rules=RULES,
    )

    assert result.quantity == Decimal("0.00123")
    assert result.notional == Decimal(123)


def test_quantity_is_normalized_to_step_size():
    result = OrderValidator().validate(
        quantity=Decimal("0.001239"),
        price=Decimal(100000),
        rules=RULES,
    )

    assert result.quantity == Decimal("0.00123")


def test_min_quantity_rejected():
    with pytest.raises(OrderValidationError):
        OrderValidator().validate(
            quantity=Decimal("0.000001"),
            price=Decimal(100000),
            rules=RULES,
        )


def test_min_notional_rejected():
    with pytest.raises(OrderValidationError):
        OrderValidator().validate(
            quantity=Decimal("0.00001"),
            price=Decimal(100000),
            rules=RULES,
        )


def test_zero_price_rejected():
    with pytest.raises(OrderValidationError):
        OrderValidator().validate(
            quantity=Decimal("0.001"),
            price=Decimal(0),
            rules=RULES,
        )

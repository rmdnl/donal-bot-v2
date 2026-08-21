import pytest

from app.execution.execution_adapter import (
    ExchangeOrder,
    ExchangeOrderStatus,
    ExecutionAdapter,
    ExecutionError,
)


class FakeGateway:
    def __init__(
        self,
        order=None,
        timeout_on_submit=False,
        reconciliation_error=False,
    ):
        self.order = order
        self.timeout_on_submit = timeout_on_submit
        self.reconciliation_error = reconciliation_error
        self.submit_calls = 0
        self.get_calls = 0

    def place_market_buy(
        self,
        symbol,
        quantity,
        client_order_id,
    ):
        self.submit_calls += 1

        if self.timeout_on_submit:
            raise TimeoutError("network timeout")

        return self.order

    def place_market_sell(
        self,
        symbol,
        quantity,
        client_order_id,
    ):
        self.submit_calls += 1
        if self.timeout_on_submit:
            raise TimeoutError("network timeout")
        return self.order

    def get_order(
        self,
        symbol,
        client_order_id,
    ):
        self.get_calls += 1

        if self.reconciliation_error:
            raise RuntimeError("exchange unavailable")

        return self.order


def make_order(
    status=ExchangeOrderStatus.FILLED,
):
    return ExchangeOrder(
        client_order_id="donal-BTCUSDT-001",
        exchange_order_id="12345",
        symbol="BTCUSDT",
        status=status,
        requested_quantity=0.01,
        executed_quantity=0.01,
    )


def test_successful_submission():
    gateway = FakeGateway(
        order=make_order(),
    )

    adapter = ExecutionAdapter(gateway)

    result = adapter.submit_buy(
        symbol="BTCUSDT",
        quantity=0.01,
        client_order_id="donal-BTCUSDT-001",
    )

    assert result.status == ExchangeOrderStatus.FILLED
    assert gateway.submit_calls == 1
    assert gateway.get_calls == 0


def test_timeout_reconciles_instead_of_resubmitting():
    gateway = FakeGateway(
        order=make_order(),
        timeout_on_submit=True,
    )

    adapter = ExecutionAdapter(gateway)

    result = adapter.submit_buy(
        symbol="BTCUSDT",
        quantity=0.01,
        client_order_id="donal-BTCUSDT-001",
    )

    assert result.status == ExchangeOrderStatus.FILLED
    assert gateway.submit_calls == 1
    assert gateway.get_calls == 1


def test_partial_fill_is_returned():
    gateway = FakeGateway(
        order=make_order(
            ExchangeOrderStatus.PARTIALLY_FILLED,
        ),
    )

    adapter = ExecutionAdapter(gateway)

    result = adapter.submit_buy(
        symbol="BTCUSDT",
        quantity=0.01,
        client_order_id="donal-BTCUSDT-001",
    )

    assert result.status == ExchangeOrderStatus.PARTIALLY_FILLED
    assert result.executed_quantity == 0.01


def test_reconciliation_failure_is_safe():
    gateway = FakeGateway(
        reconciliation_error=True,
        timeout_on_submit=True,
    )

    adapter = ExecutionAdapter(gateway)

    with pytest.raises(ExecutionError):
        adapter.submit_buy(
            symbol="BTCUSDT",
            quantity=0.01,
            client_order_id="donal-BTCUSDT-001",
        )


def test_invalid_quantity_rejected():
    gateway = FakeGateway()
    adapter = ExecutionAdapter(gateway)

    with pytest.raises(ExecutionError):
        adapter.submit_buy(
            symbol="BTCUSDT",
            quantity=0,
            client_order_id="donal-BTCUSDT-001",
        )


def test_invalid_client_order_id_rejected():
    gateway = FakeGateway()
    adapter = ExecutionAdapter(gateway)

    with pytest.raises(ExecutionError):
        adapter.submit_buy(
            symbol="BTCUSDT",
            quantity=0.01,
            client_order_id="",
        )


def test_terminal_status():
    assert ExecutionAdapter.is_terminal(
        ExchangeOrderStatus.FILLED
    )

    assert ExecutionAdapter.is_terminal(
        ExchangeOrderStatus.REJECTED
    )

    assert not ExecutionAdapter.is_terminal(
        ExchangeOrderStatus.NEW
    )


def test_non_terminal_status():
    assert not ExecutionAdapter.is_terminal(
        ExchangeOrderStatus.PARTIALLY_FILLED
    )


def test_successful_sell_submission():
    gateway = FakeGateway(order=make_order())
    adapter = ExecutionAdapter(gateway)

    result = adapter.submit_sell(
        symbol="BTCUSDT",
        quantity=0.01,
        client_order_id="donal-BTCUSDT-exit-001",
    )

    assert result.status == ExchangeOrderStatus.FILLED
    assert gateway.submit_calls == 1


def test_sell_rejects_invalid_quantity():
    gateway = FakeGateway()
    adapter = ExecutionAdapter(gateway)

    with pytest.raises(ExecutionError):
        adapter.submit_sell(
            symbol="BTCUSDT",
            quantity=0,
            client_order_id="donal-exit-001",
        )


def test_sell_rejects_empty_client_order_id():
    gateway = FakeGateway()
    adapter = ExecutionAdapter(gateway)

    with pytest.raises(ExecutionError):
        adapter.submit_sell(
            symbol="BTCUSDT",
            quantity=0.01,
            client_order_id="",
        )


def test_average_fill_price_uses_actual_execution():
    order = ExchangeOrder(
        client_order_id="donal-BTCUSDT-002",
        exchange_order_id="12346",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.01,
        executed_quantity=0.008,
        executed_quote_quantity=800.0,
    )

    assert order.average_fill_price == 100000.0


def test_zero_execution_price_is_safe():
    order = ExchangeOrder(
        client_order_id="donal-BTCUSDT-003",
        exchange_order_id="12347",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.NEW,
        requested_quantity=0.01,
        executed_quantity=0,
    )

    assert order.average_fill_price == 0.0


def test_sell_timeout_reconciles_without_resubmitting():
    gateway = FakeGateway(
        order=make_order(),
        timeout_on_submit=True,
    )
    adapter = ExecutionAdapter(gateway)

    result = adapter.submit_sell(
        symbol="BTCUSDT",
        quantity=0.01,
        client_order_id="DNL-SELL-TIMEOUT-001",
    )

    assert result.status == ExchangeOrderStatus.FILLED
    assert gateway.submit_calls == 1
    assert gateway.get_calls == 1


def test_buy_timeout_reconciles_without_resubmitting():
    gateway = FakeGateway(
        order=make_order(),
        timeout_on_submit=True,
    )
    adapter = ExecutionAdapter(gateway)

    result = adapter.submit_buy(
        symbol="BTCUSDT",
        quantity=0.01,
        client_order_id="DNL-BUY-TIMEOUT-001",
    )

    assert result.status == ExchangeOrderStatus.FILLED
    assert gateway.submit_calls == 1
    assert gateway.get_calls == 1


def test_sell_timeout_and_reconciliation_failure_is_safe():
    gateway = FakeGateway(
        order=make_order(),
        timeout_on_submit=True,
        reconciliation_error=True,
    )
    adapter = ExecutionAdapter(gateway)

    with pytest.raises(ExecutionError):
        adapter.submit_sell(
            symbol="BTCUSDT",
            quantity=0.01,
            client_order_id="DNL-SELL-UNKNOWN-001",
        )

    assert gateway.submit_calls == 1
    assert gateway.get_calls == 1


def test_buy_timeout_and_reconciliation_failure_is_safe():
    gateway = FakeGateway(
        order=make_order(),
        timeout_on_submit=True,
        reconciliation_error=True,
    )
    adapter = ExecutionAdapter(gateway)

    with pytest.raises(ExecutionError):
        adapter.submit_buy(
            symbol="BTCUSDT",
            quantity=0.01,
            client_order_id="DNL-BUY-UNKNOWN-001",
        )

    assert gateway.submit_calls == 1
    assert gateway.get_calls == 1


def test_exchange_order_supports_fill_metadata():
    order = ExchangeOrder(
        client_order_id="DNL-META-001",
        exchange_order_id="123",
        symbol="BTCUSDT",
        status=ExchangeOrderStatus.FILLED,
        requested_quantity=0.001,
        executed_quantity=0.001,
        executed_quote_quantity=100.0,
        side="BUY",
        fee=0.000001,
    )

    assert order.side == "BUY"
    assert order.fee == 0.000001
    assert order.average_fill_price == 100000.0


def test_timeout_filled_order_is_reconciled_without_resubmit():
    class TimeoutThenReconcileGateway:
        def __init__(self):
            self.buy_calls = 0
            self.get_order_calls = 0

        def place_market_buy(
            self,
            symbol,
            quantity,
            client_order_id,
        ):
            self.buy_calls += 1
            raise TimeoutError("timed out")

        def place_market_sell(
            self,
            symbol,
            quantity,
            client_order_id,
        ):
            raise AssertionError(
                "SELL must not be called"
            )

        def get_order(
            self,
            symbol,
            client_order_id,
        ):
            self.get_order_calls += 1
            return ExchangeOrder(
                client_order_id=client_order_id,
                exchange_order_id="99999",
                symbol=symbol,
                status=ExchangeOrderStatus.FILLED,
                requested_quantity=0.005,
                executed_quantity=0.005,
                executed_quote_quantity=500,
            )

    gateway = TimeoutThenReconcileGateway()
    adapter = ExecutionAdapter(gateway)

    result = adapter.submit_buy(
        symbol="BTCUSDT",
        quantity=0.005,
        client_order_id="DNL-TIMEOUT-FILLED",
    )

    assert result.status == ExchangeOrderStatus.FILLED
    assert result.exchange_order_id == "99999"
    assert result.executed_quantity == 0.005

    # PENTING: timeout tidak boleh menyebabkan BUY kedua.
    assert gateway.buy_calls == 1

    # Order harus ditemukan melalui reconciliation.
    assert gateway.get_order_calls == 1

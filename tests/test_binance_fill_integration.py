from decimal import Decimal

from app.position.binance_fill_adapter import BinanceFillAdapter
from app.position.fill_reconciler import FillReconciler
from app.position.position_manager import PositionManager, PositionState
from app.storage.trade_journal import TradeJournal

BINANCE_FILLED_ORDER = {
    "symbol": "BTCUSDT",
    "orderId": 5567361,
    "clientOrderId": "DNL-TEST-121566739C0A",
    "origQty": "0.00007000",
    "executedQty": "0.00007000",
    "cummulativeQuoteQty": "5.45004110",
    "status": "FILLED",
    "side": "BUY",
    "fills": [
        {
            "price": "77857.73000000",
            "qty": "0.00007000",
            "commission": "0.00000007",
            "commissionAsset": "BTC",
        }
    ],
}


def test_binance_filled_order_reaches_position(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    fill = BinanceFillAdapter().from_order(
        BINANCE_FILLED_ORDER
    )

    result = FillReconciler(
        journal,
        positions,
    ).reconcile(fill)

    assert result.symbol == "BTCUSDT"
    assert result.quantity == Decimal("0.00007000")
    assert result.average_entry == Decimal(
        "77857.73000000"
    )
    assert result.total_fees == Decimal(
        "0.0054500411"
    )
    assert result.realized_pnl == -Decimal(
        "0.0054500411"
    )


def test_binance_fill_recovery_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    reconciler = FillReconciler(
        journal,
        positions,
    )

    fill = BinanceFillAdapter().from_order(
        BINANCE_FILLED_ORDER
    )

    first = reconciler.reconcile(fill)
    second = reconciler.reconcile(fill)

    assert first == second
    assert positions.position.quantity == Decimal(
        "0.00007000"
    )

    entry = journal.get(
        "DNL-TEST-121566739C0A"
    )

    assert entry is not None
    assert entry.status == "FILLED"


def test_journal_contains_executed_quantity(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()

    fill = BinanceFillAdapter().from_order(
        BINANCE_FILLED_ORDER
    )

    FillReconciler(
        journal,
        positions,
    ).reconcile(fill)

    entry = journal.get(
        "DNL-TEST-121566739C0A"
    )

    assert entry is not None
    assert entry.symbol == "BTCUSDT"
    assert entry.side == "BUY"
    assert entry.quantity == "0.00007000"
    assert entry.executed_quantity == "0.00007000"


def test_binance_sell_fill_reaches_flat_position(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    buy = BINANCE_FILLED_ORDER
    reconciler.reconcile(
        BinanceFillAdapter().from_order(buy)
    )

    sell_order = {
        "symbol": "BTCUSDT",
        "orderId": 5600922,
        "clientOrderId": "DNL-TEST-SELL-5600922",
        "origQty": "0.00007000",
        "executedQty": "0.00007000",
        "cummulativeQuoteQty": "5.44700310",
        "status": "FILLED",
        "side": "SELL",
        "fills": [
            {
                "price": "77814.33",
                "qty": "0.00007000",
                "commission": "0.00544700",
                "commissionAsset": "USDT",
            }
        ],
    }

    fill = BinanceFillAdapter().from_order(
        sell_order
    )

    assert fill.side == "SELL"
    assert fill.executed_quantity == Decimal(
        "0.00007000"
    )
    assert fill.price == Decimal(
        "5.44700310"
    ) / Decimal("0.00007000")

    result = reconciler.reconcile(fill)

    assert result.state == PositionState.FLAT
    assert result.quantity == Decimal(0)
    expected_buy_fee = (
        Decimal("0.00000007")
        * Decimal("77857.73")
    )

    expected_sell_fee = Decimal("0.00544700")

    assert result.total_fees == (
        expected_buy_fee
        + expected_sell_fee
    )

    entry = journal.get(
        "DNL-TEST-SELL-5600922"
    )

    assert entry is not None
    assert entry.side == "SELL"
    assert entry.status == "FILLED"
    assert entry.executed_quantity == "0.00007000"


def test_binance_sell_fee_in_base_asset_is_converted_to_quote(
    tmp_path,
):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    buy = BINANCE_FILLED_ORDER

    reconciler.reconcile(
        BinanceFillAdapter().from_order(buy)
    )

    sell_order = {
        "symbol": "BTCUSDT",
        "orderId": 5600999,
        "clientOrderId": "DNL-TEST-SELL-BTC-FEE",
        "origQty": "0.00007000",
        "executedQty": "0.00007000",
        "cummulativeQuoteQty": "5.44700310",
        "status": "FILLED",
        "side": "SELL",
        "fills": [
            {
                "price": "77814.33",
                "qty": "0.00007000",
                "commission": "0.00000001",
                "commissionAsset": "BTC",
            }
        ],
    }

    fill = BinanceFillAdapter().from_order(
        sell_order
    )

    expected_sell_fee = (
        Decimal("0.00000001")
        * fill.price
    )

    expected_buy_fee = (
        Decimal("0.00000007")
        * Decimal("77857.73")
    )

    assert fill.side == "SELL"
    assert fill.fee == expected_sell_fee

    result = reconciler.reconcile(fill)

    assert result.state == PositionState.FLAT
    assert result.quantity == Decimal(0)
    assert result.total_fees == (
        expected_buy_fee
        + expected_sell_fee
    )

def test_binance_sell_fill_recovery_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )
    positions = PositionManager()
    reconciler = FillReconciler(
        journal,
        positions,
    )

    buy_fill = BinanceFillAdapter().from_order(
        BINANCE_FILLED_ORDER
    )
    reconciler.reconcile(buy_fill)

    sell_order = {
        "symbol": "BTCUSDT",
        "orderId": 5600922,
        "clientOrderId": "DNL-E2E-SELL-001",
        "origQty": "0.00007000",
        "executedQty": "0.00007000",
        "cummulativeQuoteQty": "5.44700310",
        "status": "FILLED",
        "side": "SELL",
        "fills": [
            {
                "price": "77814.33",
                "qty": "0.00007000",
                "commission": "0.00544700",
                "commissionAsset": "USDT",
            }
        ],
    }

    sell_fill = BinanceFillAdapter().from_order(
        sell_order
    )

    first = reconciler.reconcile(sell_fill)

    second = reconciler.reconcile(sell_fill)

    assert first == second
    assert second.state == PositionState.FLAT
    assert second.quantity == Decimal(0)

    sell_entry = journal.get(
        "DNL-E2E-SELL-001"
    )

    assert sell_entry is not None
    assert sell_entry.status == "FILLED"
    assert sell_entry.executed_quantity == "0.00007000"

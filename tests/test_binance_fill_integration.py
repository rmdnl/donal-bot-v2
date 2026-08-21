from decimal import Decimal

from app.position.binance_fill_adapter import BinanceFillAdapter
from app.position.fill_reconciler import FillReconciler
from app.position.position_manager import PositionManager
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

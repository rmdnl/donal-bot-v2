from app.storage.trade_journal import (
    JournalEntry,
    TradeJournal,
)


def test_record_and_get(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    entry = JournalEntry(
        client_order_id="DNL-001",
        symbol="BTCUSDT",
        side="BUY",
        status="FILLED",
        quantity="0.01",
        executed_quantity="0.008",
    )

    journal.record(entry)

    result = journal.get("DNL-001")

    assert result == entry


def test_record_is_idempotent(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    entry = JournalEntry(
        client_order_id="DNL-001",
        symbol="BTCUSDT",
        side="BUY",
        status="NEW",
        quantity="0.01",
        executed_quantity="0",
    )

    journal.record(entry)

    updated = JournalEntry(
        client_order_id="DNL-001",
        symbol="BTCUSDT",
        side="BUY",
        status="FILLED",
        quantity="0.01",
        executed_quantity="0.01",
    )

    journal.record(updated)

    assert journal.get("DNL-001") == updated


def test_missing_order_returns_none(tmp_path):
    journal = TradeJournal(
        str(tmp_path / "trades.db")
    )

    assert journal.get("DNL-MISSING") is None

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class JournalEntry:
    client_order_id: str
    symbol: str
    side: str
    status: str
    quantity: str
    executed_quantity: str
    price: str = "0"
    fee: str = "0"


class TradeJournal:
    def __init__(self, path: str = "data/trades.db") -> None:
        self.path = path
        connection = sqlite3.connect(self.path)

        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    client_order_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    executed_quantity TEXT NOT NULL,
                    price TEXT NOT NULL DEFAULT '0',
                    fee TEXT NOT NULL DEFAULT '0'
                )
                """
            )

            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(trades)"
                ).fetchall()
            }

            if "price" not in columns:
                connection.execute(
                    """
                    ALTER TABLE trades
                    ADD COLUMN price TEXT NOT NULL DEFAULT '0'
                    """
                )

            if "fee" not in columns:
                connection.execute(
                    """
                    ALTER TABLE trades
                    ADD COLUMN fee TEXT NOT NULL DEFAULT '0'
                    """
                )

            connection.commit()

        finally:
            connection.close()

    def record(self, entry: JournalEntry) -> None:
        connection = sqlite3.connect(self.path)

        try:
            connection.execute(
                """
                INSERT INTO trades (
                    client_order_id,
                    symbol,
                    side,
                    status,
                    quantity,
                    executed_quantity,
                    price,
                    fee
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_order_id)
                DO UPDATE SET
                    status = excluded.status,
                    executed_quantity = excluded.executed_quantity,
                    price = excluded.price,
                    fee = excluded.fee
                """,
                (
                    entry.client_order_id,
                    entry.symbol,
                    entry.side,
                    entry.status,
                    entry.quantity,
                    entry.executed_quantity,
                    entry.price,
                    entry.fee,
                ),
            )
            connection.commit()

        finally:
            connection.close()

    def pending(self) -> list[JournalEntry]:
        connection = sqlite3.connect(self.path)

        try:
            rows = connection.execute(
                """
                SELECT
                    client_order_id,
                    symbol,
                    side,
                    status,
                    quantity,
                    executed_quantity,
                    price,
                    fee
                FROM trades
                WHERE status NOT IN (
                    'FILLED',
                    'CANCELED',
                    'REJECTED',
                    'EXPIRED'
                )
                """
            ).fetchall()

        finally:
            connection.close()

        return [JournalEntry(*row) for row in rows]

    def get(
        self,
        client_order_id: str,
    ) -> JournalEntry | None:
        connection = sqlite3.connect(self.path)

        try:
            row = connection.execute(
                """
                SELECT
                    client_order_id,
                    symbol,
                    side,
                    status,
                    quantity,
                    executed_quantity,
                    price,
                    fee
                FROM trades
                WHERE client_order_id = ?
                """,
                (client_order_id,),
            ).fetchone()

        finally:
            connection.close()

        if row is None:
            return None

        return JournalEntry(*row)

    def entries(self) -> list[JournalEntry]:
        connection = sqlite3.connect(self.path)

        try:
            rows = connection.execute(
                """
                SELECT
                    client_order_id,
                    symbol,
                    side,
                    status,
                    quantity,
                    executed_quantity,
                    price,
                    fee
                FROM trades
                ORDER BY rowid ASC
                """
            ).fetchall()

        finally:
            connection.close()

        return [JournalEntry(*row) for row in rows]

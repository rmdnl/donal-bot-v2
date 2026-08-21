from __future__ import annotations

from decimal import Decimal

from app.exchange.binance_client import BinanceClient
from app.exchange.symbol_rules import SymbolRules


class ExchangeInfo:
    def __init__(self, client: BinanceClient):
        self.client = client

    def symbol_rules(self, symbol: str) -> SymbolRules:
        symbol = symbol.upper().strip()

        payload = self.client.get(
            "/api/v3/exchangeInfo",
            {"symbol": symbol},
        )

        symbols = payload.get("symbols", [])

        if not symbols:
            raise ValueError(
                f"Symbol not found: {symbol}"
            )

        item = symbols[0]
        filters = {
            entry["filterType"]: entry
            for entry in item.get("filters", [])
        }

        price_filter = filters["PRICE_FILTER"]
        lot_filter = filters["LOT_SIZE"]

        notional_filter = filters.get("NOTIONAL")
        if notional_filter is None:
            notional_filter = filters["MIN_NOTIONAL"]

        return SymbolRules(
            symbol=item["symbol"],
            base_asset=item["baseAsset"],
            quote_asset=item["quoteAsset"],
            status=item["status"],
            tick_size=Decimal(price_filter["tickSize"]),
            step_size=Decimal(lot_filter["stepSize"]),
            min_qty=Decimal(lot_filter["minQty"]),
            min_notional=Decimal(
                notional_filter["minNotional"]
            ),
        )

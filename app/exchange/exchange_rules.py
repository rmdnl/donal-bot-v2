from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.exchange.binance_client import BinanceClient


class ExchangeRulesError(ValueError):
    pass


@dataclass(frozen=True)
class ExchangeRules:
    symbol: str
    min_qty: Decimal
    step_size: Decimal
    min_notional: Decimal


class ExchangeRulesLoader:
    def __init__(self, client: BinanceClient) -> None:
        self.client = client

    def load(self, symbol: str) -> ExchangeRules:
        normalized = symbol.upper().strip()

        if not normalized:
            raise ExchangeRulesError(
                "symbol is required"
            )

        payload = self.client.get(
            "/api/v3/exchangeInfo",
            {"symbol": normalized},
        )

        if not isinstance(payload, dict):
            raise ExchangeRulesError(
                "invalid exchange info response"
            )

        symbols = payload.get("symbols")

        if not isinstance(symbols, list) or not symbols:
            raise ExchangeRulesError(
                f"symbol not found: {normalized}"
            )

        info = symbols[0]

        if not isinstance(info, dict):
            raise ExchangeRulesError(
                "invalid symbol information"
            )

        filters = info.get("filters")

        if not isinstance(filters, list):
            raise ExchangeRulesError(
                "missing symbol filters"
            )

        lot_size = next(
            (
                item
                for item in filters
                if isinstance(item, dict)
                and item.get("filterType") == "LOT_SIZE"
            ),
            None,
        )

        notional = next(
            (
                item
                for item in filters
                if isinstance(item, dict)
                and item.get("filterType") in {
                    "NOTIONAL",
                    "MIN_NOTIONAL",
                }
            ),
            None,
        )

        if lot_size is None:
            raise ExchangeRulesError(
                "LOT_SIZE filter is missing"
            )

        if notional is None:
            raise ExchangeRulesError(
                "NOTIONAL filter is missing"
            )

        try:
            min_qty = Decimal(str(lot_size["minQty"]))
            step_size = Decimal(str(lot_size["stepSize"]))
            min_notional = Decimal(
                str(
                    notional.get(
                        "minNotional",
                        notional.get("minNotional"),
                    )
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExchangeRulesError(
                "invalid exchange filter values"
            ) from exc

        return ExchangeRules(
            symbol=normalized,
            min_qty=min_qty,
            step_size=step_size,
            min_notional=min_notional,
        )

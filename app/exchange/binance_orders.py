from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config.settings import Settings
from app.exchange.binance_signed import BinanceSignedClient


class BinanceOrderError(RuntimeError):
    """Raised when Binance order operations fail."""


@dataclass(frozen=True)
class OrderReconciliation:
    status: Literal["FOUND", "NOT_FOUND"]
    order_id: int | None
    raw: dict | None = None


@dataclass
class BinanceOrderClient:
    settings: Settings
    timeout: float = 10.0

    def __post_init__(self) -> None:
        self.signed = BinanceSignedClient(
            settings=self.settings,
            timeout=self.timeout,
        )

    def place_market_buy(
        self,
        symbol: str,
        quantity: str,
        client_order_id: str,
    ) -> dict:
        if not symbol:
            raise BinanceOrderError("symbol is required")

        if not quantity:
            raise BinanceOrderError("quantity is required")

        try:
            value = float(quantity)
        except ValueError as exc:
            raise ValueError(
                "quantity must be numeric"
            ) from exc

        if value <= 0:
            raise ValueError("quantity must be positive")

        if not client_order_id:
            raise BinanceOrderError(
                "client_order_id is required"
            )

        return self._request(
            "POST",
            "/api/v3/order",
            {
                "symbol": symbol.upper(),
                "side": "BUY",
                "type": "MARKET",
                "quantity": quantity,
                "newClientOrderId": client_order_id,
            },
        )

    def place_market_sell(
        self,
        symbol: str,
        quantity: str,
        client_order_id: str,
    ) -> dict:
        if not symbol:
            raise BinanceOrderError(
                "symbol is required"
            )
        if not quantity:
            raise BinanceOrderError(
                "quantity is required"
            )
        try:
            value = float(quantity)
        except ValueError as exc:
            raise ValueError(
                "quantity must be numeric"
            ) from exc
        if value <= 0:
            raise ValueError(
                "quantity must be positive"
            )
        if not client_order_id:
            raise BinanceOrderError(
                "client_order_id is required"
            )

        return self._request(
            "POST",
            "/api/v3/order",
            {
                "symbol": symbol.upper(),
                "side": "SELL",
                "type": "MARKET",
                "quantity": quantity,
                "newClientOrderId": client_order_id,
            },
        )

    def get_order(
        self,
        symbol: str,
        client_order_id: str,
    ) -> dict:
        if not symbol:
            raise BinanceOrderError("symbol is required")

        if not client_order_id:
            raise BinanceOrderError(
                "client_order_id is required"
            )

        return self._request(
            "GET",
            "/api/v3/order",
            {
                "symbol": symbol.upper(),
                "origClientOrderId": client_order_id,
            },
        )

    def reconcile_order(
        self,
        symbol: str,
        client_order_id: str,
    ) -> OrderReconciliation:
        try:
            order = self.get_order(
                symbol,
                client_order_id,
            )
        except BinanceOrderError as exc:
            if "(code -2013)" in str(exc):
                return OrderReconciliation(
                    status="NOT_FOUND",
                    order_id=None,
                )
            raise

        order_id = order.get("orderId")

        if not isinstance(order_id, int):
            raise BinanceOrderError(
                "Invalid Binance order response: "
                "missing orderId"
            )

        return OrderReconciliation(
            status="FOUND",
            order_id=order_id,
            raw=order,
        )

    def cancel_order(
        self,
        symbol: str,
        client_order_id: str,
    ) -> dict:
        if not symbol:
            raise BinanceOrderError("symbol is required")

        if not client_order_id:
            raise BinanceOrderError(
                "client_order_id is required"
            )

        return self._request(
            "DELETE",
            "/api/v3/order",
            {
                "symbol": symbol.upper(),
                "origClientOrderId": client_order_id,
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str],
    ) -> dict:
        self.settings.validate_credentials()

        url, signed = self.signed.build_signed_request(
            path,
            params,
        )

        encoded = urlencode(signed)

        if method == "GET" or method == "DELETE":
            request_url = f"{url}?{encoded}"
            data = None
        elif method == "POST":
            request_url = url
            data = encoded.encode("utf-8")
        else:
            raise BinanceOrderError(
                f"Unsupported HTTP method: {method}"
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": "donal-bot-v2/1.0",
            "X-MBX-APIKEY": self.settings.binance_api_key,
        }

        if method == "POST":
            headers["Content-Type"] = (
                "application/x-www-form-urlencoded"
            )

        request = Request(
            request_url,
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
                payload = json.loads(body)
                message = payload.get("msg", body)
                code = payload.get("code")
            except (TypeError, ValueError):
                message = str(exc)
                code = None

            detail = (
                f"Binance order HTTP {exc.code}: {message}"
            )

            if code is not None:
                detail = f"{detail} (code {code})"

            raise BinanceOrderError(detail) from exc

        except (URLError, TimeoutError, OSError) as exc:
            raise BinanceOrderError(
                f"Binance order transport error: {exc}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise BinanceOrderError(
                "Binance returned invalid order JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise BinanceOrderError(
                "Invalid Binance order response"
            )

        return payload

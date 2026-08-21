from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config.settings import Settings
from app.exchange.binance_client import BinanceAPIError, BinanceClient
from app.exchange.binance_signed import BinanceSignedClient


@dataclass
class BinanceGateway:
    settings: Settings
    timeout: float = 10.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        self.public = BinanceClient(
            base_url=self.settings.binance_base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        self.signed = BinanceSignedClient(
            settings=self.settings,
            timeout=self.timeout,
        )

    def server_time(self) -> int:
        payload = self.public.get("/api/v3/time")

        if not isinstance(payload, dict):
            raise BinanceAPIError("Invalid server time response")

        server_time = payload.get("serverTime")

        if not isinstance(server_time, int):
            raise BinanceAPIError("Missing serverTime in Binance response")

        return server_time

    def sync_time(self) -> int:
        local_before = int(time.time() * 1000)
        server_time = self.server_time()
        local_after = int(time.time() * 1000)

        midpoint = (local_before + local_after) // 2
        self.signed.time_offset_ms = server_time - midpoint

        return self.signed.time_offset_ms

    def account(self) -> dict:
        self.settings.validate_credentials()

        if self.signed.time_offset_ms == 0:
            self.sync_time()

        url, params = self.signed.build_signed_request(
            "/api/v3/account",
        )

        return self._signed_get(url, params)

    def _signed_get(
        self,
        url: str,
        params: dict[str, str],
    ) -> dict:
        query = urlencode(params)
        request = Request(
            f"{url}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "donal-bot-v2/1.0",
                "X-MBX-APIKEY": self.settings.binance_api_key,
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body)

        except HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
                payload = json.loads(body)
                message = payload.get("msg", body)
                code = payload.get("code")
            except (TypeError, ValueError):
                message = str(exc)
                code = None

            detail = f"Binance HTTP {exc.code}: {message}"

            if code is not None:
                detail = f"{detail} (code {code})"

            raise BinanceAPIError(detail) from exc

        except (URLError, TimeoutError, OSError) as exc:
            raise BinanceAPIError(
                f"Binance transport error: {exc}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise BinanceAPIError(
                "Binance returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise BinanceAPIError("Invalid Binance account response")

        return payload

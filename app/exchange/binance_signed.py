from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from app.config.settings import Settings


@dataclass
class BinanceSignedClient:
    settings: Settings
    timeout: float = 10.0
    time_offset_ms: int = 0

    def _signature(self, params: dict[str, str]) -> str:
        query = urlencode(params)
        return hmac.new(
            self.settings.binance_api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _signed_params(
        self,
        params: dict[str, str] | None = None,
    ) -> dict[str, str]:
        result = dict(params or {})

        if "timestamp" not in result:
            timestamp = int(time.time() * 1000) + self.time_offset_ms
            result["timestamp"] = str(timestamp)

        result["recvWindow"] = str(self.settings.binance_recv_window)
        result["signature"] = self._signature(result)

        return result

    def build_signed_request(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> tuple[str, dict[str, str]]:
        self.settings.validate_credentials()

        signed = self._signed_params(params)
        url = f"{self.settings.binance_base_url}{path}"

        return url, signed

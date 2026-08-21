from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BinanceAPIError(RuntimeError):
    """Raised when Binance returns an API or transport error."""


@dataclass(frozen=True)
class BinanceClient:
    base_url: str = "https://api.binance.com"
    timeout: float = 10.0
    max_retries: int = 3
    backoff: float = 0.5

    def get(self, path: str, params: dict | None = None) -> dict | list:
        query = urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "donal-bot-v2/1.0",
                },
                method="GET",
            )

            try:
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    return json.loads(body)

            except HTTPError as exc:
                last_error = exc

                if exc.code in (418, 429) and attempt < self.max_retries:
                    retry_after = exc.headers.get("Retry-After")
                    delay = (
                        float(retry_after)
                        if retry_after
                        else self.backoff * (2**attempt)
                    )
                    time.sleep(min(delay, 10.0))
                    continue

                try:
                    body = exc.read().decode("utf-8")
                    payload = json.loads(body)
                    message = payload.get("msg", body)
                except (TypeError, ValueError):
                    message = str(exc)

                raise BinanceAPIError(
                    f"Binance HTTP {exc.code}: {message}"
                ) from exc

            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc

                if attempt < self.max_retries:
                    time.sleep(min(self.backoff * (2**attempt), 10.0))
                    continue

                raise BinanceAPIError(
                    f"Binance transport error: {exc}"
                ) from exc

            except json.JSONDecodeError as exc:
                raise BinanceAPIError(
                    "Binance returned invalid JSON"
                ) from exc

        raise BinanceAPIError(
            f"Binance request failed: {last_error}"
        )

from __future__ import annotations

import hashlib
import re


class IdempotencyError(ValueError):
    pass


def make_client_order_id(
    symbol: str,
    signal_id: str,
) -> str:
    symbol = symbol.upper().strip()
    signal_id = signal_id.strip()

    if not symbol:
        raise IdempotencyError("symbol is required")

    if not signal_id:
        raise IdempotencyError("signal_id is required")

    if not re.fullmatch(r"[A-Z0-9]+", symbol):
        raise IdempotencyError("invalid symbol")

    digest = hashlib.sha256(
        f"{symbol}:{signal_id}".encode()
    ).hexdigest()[:16]

    return f"DNL-{symbol}-{digest}"

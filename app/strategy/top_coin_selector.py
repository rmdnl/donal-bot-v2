from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class SelectionError(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    symbol: str
    score: Decimal


class TopCoinSelector:
    def __init__(self, minimum_score: Decimal = Decimal(75)):
        if not 0 <= minimum_score <= 100:
            raise SelectionError(
                "minimum score must be between 0 and 100"
            )

        self.minimum_score = minimum_score

    def select(
        self,
        candidates: list[Candidate],
    ) -> Candidate | None:
        eligible = [
            candidate
            for candidate in candidates
            if candidate.score >= self.minimum_score
        ]

        if not eligible:
            return None

        return max(
            eligible,
            key=lambda candidate: candidate.score,
        )

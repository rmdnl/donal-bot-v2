from dataclasses import dataclass


@dataclass(frozen=True)
class HealthStatus:
    ok: bool
    component: str
    message: str


def check() -> HealthStatus:
    return HealthStatus(
        ok=True,
        component="core",
        message="DONAL BOT V2 foundation OK",
    )

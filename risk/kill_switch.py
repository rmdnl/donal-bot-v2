"""Kill switch: deteksi flash crash pada candle 1m + cooldown."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass
class CrashResult:
    triggered: bool
    reason: str = ""

def check_flash_crash(df_1m, lookback_minutes=15, price_drop_pct=12.0,
                      volume_baseline_minutes=60, volume_multiplier=5.0):
    needed = lookback_minutes + volume_baseline_minutes
    if len(df_1m) < needed:
        return CrashResult(False, "data 1m kurang")
    recent = df_1m.iloc[-lookback_minutes:]
    baseline = df_1m.iloc[-needed:-lookback_minutes]
    start = float(recent["close"].iloc[0])
    if start == 0:
        return CrashResult(False)
    drop = (float(recent["low"].min()) - start) / start * 100
    med = baseline["volume"].median()
    vol_ratio = (recent["volume"].mean() / med) if med and med > 0 else 0
    if (drop <= -price_drop_pct and vol_ratio >= volume_multiplier) or drop <= -(price_drop_pct * 2):
        return CrashResult(True, f"drop {drop:.2f}% vol {vol_ratio:.1f}x")
    return CrashResult(False)

def new_cooldown(hours=6.0):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()

def is_in_cooldown(state):
    if not state.kill_switch_cooldown_until:
        return False
    try:
        until = datetime.fromisoformat(state.kill_switch_cooldown_until)
        if until.tzinfo is None: until = until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < until
    except ValueError:
        return False

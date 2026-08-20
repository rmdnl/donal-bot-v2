"""Macro guard: blokir entry sekitar event makro besar (FOMC/CPI/NFP)."""
import logging
from datetime import datetime, timedelta, timezone, date

logger = logging.getLogger("macro_guard")

class MacroGuard:
    def __init__(self, cfg=None):
        cfg = cfg or {}
        self.enabled = cfg.get("enabled", True)
        self.window = timedelta(hours=cfg.get("window_hours", 2))
        self.block_nfp = cfg.get("block_nfp", True)
        self.events = []
        for ev in cfg.get("events", []):
            try:
                dt = datetime.fromisoformat(ev)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                self.events.append(dt)
            except ValueError:
                logger.warning(f"macro_event_invalid {ev}")

    def _nfp_window(self, now):
        # Jumat pertama tiap bulan, 12:00-16:00 UTC (rilis NFP)
        first = date(now.year, now.month, 1)
        while first.weekday() != 4:
            first += timedelta(days=1)
        return now.date() == first and 12 <= now.hour < 16

    def is_blackout(self, now=None):
        if not self.enabled:
            return False, ""
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        for ev in self.events:
            if abs(now - ev) <= self.window:
                return True, f"macro event {ev.isoformat()}"
        if self.block_nfp and self._nfp_window(now):
            return True, "NFP window (Jumat pertama 12-16 UTC)"
        return False, ""

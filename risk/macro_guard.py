"""Macro guard v2: auto calendar (Finnhub) + manual events + NFP rule.

Prioritas proteksi:
1. Auto-sync kalender ekonomi US (CPI, NFP, FOMC, PPI, PCE) tiap 12 jam
2. Event manual di config.yaml (fallback / event khusus)
3. Aturan NFP otomatis (Jumat pertama 12-16 UTC)
"""
import logging, time
import requests
from datetime import datetime, timedelta, timezone, date

logger = logging.getLogger("macro_guard")

DEFAULT_KEYWORDS = ["CPI", "Nonfarm Payrolls", "FOMC", "Federal Funds Rate", "PPI", "Core PCE"]

class MacroGuard:
    def __init__(self, cfg=None, api_key=""):
        cfg = cfg or {}
        self.enabled = cfg.get("enabled", True)
        self.window = timedelta(hours=cfg.get("window_hours", 2))
        self.block_nfp = cfg.get("block_nfp", True)
        self.api_key = api_key
        self.auto = bool(cfg.get("auto_calendar", True)) and bool(api_key)
        self.keywords = cfg.get("keywords", DEFAULT_KEYWORDS)
        self.refresh_hours = cfg.get("refresh_hours", 12)
        self._last_sync = 0.0
        self._auto_events = []
        self.events = []
        for ev in cfg.get("events", []):
            dt = self._parse(ev)
            if dt: self.events.append(dt)
        if cfg.get("auto_calendar", True) and not api_key:
            logger.info("macro_guard manual mode (FINNHUB_API_KEY kosong)")

    @staticmethod
    def _parse(s):
        try:
            dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def sync_if_stale(self):
        if not self.auto: return
        now = time.monotonic()
        if now - self._last_sync < self.refresh_hours * 3600: return
        self._last_sync = now
        try:
            d1 = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
            d2 = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()
            r = requests.get("https://finnhub.io/api/v1/calendar/economic",
                             params={"from": d1, "to": d2, "token": self.api_key}, timeout=10)
            rows = r.json().get("economicCalendar", [])
            evs = []
            for ev in rows:
                if ev.get("country") != "US": continue
                name = ev.get("event") or ""
                if not any(k.lower() in name.lower() for k in self.keywords): continue
                dt = self._parse(ev.get("time", ""))
                if dt: evs.append((dt, name))
            self._auto_events = evs
            logger.info(f"macro_calendar_synced events={len(evs)}")
        except Exception as e:
            logger.warning(f"macro_calendar_sync_failed {e}")

    def _nfp_window(self, now):
        first = date(now.year, now.month, 1)
        while first.weekday() != 4:
            first += timedelta(days=1)
        return now.date() == first and 12 <= now.hour < 16

    def is_blackout(self, now=None):
        if not self.enabled: return False, ""
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None: now = now.replace(tzinfo=timezone.utc)
        self.sync_if_stale()
        for dt, name in self._auto_events:
            if abs(now - dt) <= self.window:
                return True, f"{name} @ {dt.isoformat()}"
        for ev in self.events:
            if abs(now - ev) <= self.window:
                return True, f"manual event {ev.isoformat()}"
        if self.block_nfp and self._nfp_window(now):
            return True, "NFP window"
        return False, ""

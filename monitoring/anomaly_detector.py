"""Anomaly detector: sistem imun bot (alert Telegram)."""
import time, logging
from datetime import datetime, timezone

logger = logging.getLogger("anomaly")

class AnomalyDetector:
    def __init__(self, notifier=None, balance_drop_pct=5.0, balance_interval=3600,
                 stuck_hours=48, api_error_threshold=5, api_error_window=600):
        self.notifier = notifier
        self.balance_drop_pct = balance_drop_pct
        self.balance_interval = balance_interval
        self.stuck_hours = stuck_hours
        self.api_threshold = api_error_threshold
        self.api_window = api_error_window
        self._api_errors = []
        self._base_balance = None
        self._base_ts = 0.0
        self._cooldowns = {}

    def _alert(self, key, msg, cooldown=1800):
        now = time.monotonic()
        if now - self._cooldowns.get(key, 0) < cooldown:
            return
        self._cooldowns[key] = now
        logger.warning(f"anomaly {key}: {msg}")
        if self.notifier:
            self.notifier.send(f"ANOMALY [{key}]\n{msg}")

    def record_api_error(self, error_msg=""):
        now = time.monotonic()
        self._api_errors.append(now)
        self._api_errors = [t for t in self._api_errors if t > now - self.api_window]
        if len(self._api_errors) >= self.api_threshold:
            self._alert("api_health",
                        f"{len(self._api_errors)} API errors dalam {self.api_window // 60} menit\nLast: {str(error_msg)[:100]}")

    def periodic_check(self, states, equity):
        now = time.monotonic()
        now_dt = datetime.now(timezone.utc)

        # Balance drop tak terjelaskan (per interval)
        if self._base_balance and self._base_balance > 0 and now - self._base_ts >= self.balance_interval:
            change = (equity - self._base_balance) / self._base_balance * 100
            if change <= -self.balance_drop_pct:
                self._alert("balance",
                            f"Equity turun {change:.2f}% dalam {self.balance_interval // 3600} jam\n"
                            f"{self._base_balance:.2f} -> {equity:.2f}\nCEK AKUN!")
            self._base_balance = equity
            self._base_ts = now
        elif self._base_balance is None:
            self._base_balance = equity
            self._base_ts = now

        # Stuck positions + OCO integrity
        for sym, st in states.items():
            if not st.in_position:
                continue
            if st.entry_ts:
                try:
                    entry = datetime.fromisoformat(st.entry_ts)
                    if entry.tzinfo is None:
                        entry = entry.replace(tzinfo=timezone.utc)
                    hours = (now_dt - entry).total_seconds() / 3600
                    if hours >= self.stuck_hours:
                        self._alert(f"stuck_{sym}", f"Posisi {sym} terbuka {hours:.0f} jam tanpa exit")
                except ValueError:
                    pass
            if not st.oco_order_list_id:
                self._alert(f"no_oco_{sym}", f"Posisi {sym} tanpa OCO (SL/TP)! Cek manual.")

"""Daily report scheduler ke Telegram (+ manual via /report)."""
import threading, time, logging
from datetime import datetime, timezone

logger = logging.getLogger("daily_report")

class DailyReport:
    def __init__(self, notifier, trade_history, send_time_utc="00:00"):
        self.notifier = notifier
        self.history = trade_history
        self.send_time = send_time_utc
        if notifier:
            threading.Thread(target=self._loop, daemon=True, name="daily-report").start()
            logger.info("daily_report_scheduler_started")

    def build_report(self):
        s = self.history.get_summary()
        lines = [
            "DAILY REPORT",
            f"Trades: {s['total']} (W:{s['wins']} L:{s['losses']})",
            f"Win rate: {s['win_rate']}% | PF: {s['profit_factor']}",
            f"Total PnL: {s['total_pnl']:+.4f} USDT",
        ]
        recent = self.history.get_closed_trades(5)
        if recent:
            lines.append("Trade terakhir:")
            for t in recent:
                lines.append(f"  {t['symbol']} {t['exit_type']} {t['pnl_usdt']:+.4f} ({t['pnl_pct']:+.2f}%)")
        return "\n".join(lines)

    def send_now(self, args=None):
        if self.notifier:
            self.notifier.send(self.build_report())

    def _loop(self):
        hh, mm = map(int, self.send_time.split(":"))
        last_sent = None
        while True:
            now = datetime.now(timezone.utc)
            if now.hour == hh and now.minute == mm and last_sent != now.date():
                self.send_now()
                last_sent = now.date()
            time.sleep(30)

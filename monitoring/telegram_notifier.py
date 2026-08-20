"""Telegram notifier + interactive commands (background polling thread)."""
import logging, threading, time
import requests

logger = logging.getLogger("telegram")

class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.enabled = bool(bot_token and chat_id)
        self.token, self.chat_id = bot_token, chat_id
        self._handlers = {}
        self._last_update = 0
        self._last_send = 0.0
        if self.enabled:
            threading.Thread(target=self._poll, daemon=True, name="tg-poll").start()
            logger.info("telegram_polling_started")

    def send(self, text):
        if not self.enabled: return False
        now = time.monotonic()
        wait = 1.0 - (now - self._last_send)
        if wait > 0: time.sleep(wait)
        self._last_send = time.monotonic()
        try:
            r = requests.post(f"https://api.telegram.org/bot{self.token}/sendMessage",
                              json={"chat_id": self.chat_id, "text": text}, timeout=10)
            return r.status_code == 200
        except Exception as e:
            logger.warning(f"tg_send_error {e}")
            return False

    def register(self, command, handler):
        key = command if command.startswith("/") else "/" + command
        self._handlers[key.lower()] = handler

    def _poll(self):
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        while True:
            try:
                r = requests.get(url, params={"offset": self._last_update + 1, "timeout": 30}, timeout=35)
                data = r.json()
                if data.get("ok"):
                    for u in data.get("result", []):
                        self._last_update = max(self._last_update, u["update_id"])
                        self._handle(u)
            except Exception:
                time.sleep(5)

    def _handle(self, update):
        msg = update.get("message", {})
        if str(msg.get("chat", {}).get("id", "")) != str(self.chat_id): return
        text = (msg.get("text") or "").strip()
        if not text.startswith("/"): return
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]
        args = parts[1] if len(parts) > 1 else ""
        
        h = self._handlers.get(cmd)
        if h:
            try:
                h(args)
            except Exception as e:
                self.send(f"Error {cmd}: {e}")
        else:
            self.send(self._help_text())

    def _help_text(self):
        return (
            "📋 Commands:\n\n"
            "/status - Bot + risk status\n"
            "/positions - Open positions\n"
            "/regime - Market regime semua symbol\n"
            "/pnl - Performance summary\n"
            "/recent [N] - N trade terakhir\n"
            "/config - Konfigurasi aktif\n"
            "/pause - Block new entries\n"
            "/resume - Allow entries\n"
            "/close SYMBOL - Close position\n"
            "/report - Daily report\n"
            "/help - This message"
        )

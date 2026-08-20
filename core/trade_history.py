"""SQLite trade history untuk reporting, analytics, dan dashboard."""
import os, sqlite3, logging
from datetime import datetime, timezone

logger = logging.getLogger("trade_history")

class TradeHistory:
    def __init__(self, db_path="data/trades.db"):
        self.db_path = db_path
        d = os.path.dirname(db_path)
        if d: os.makedirs(d, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, symbol TEXT, event TEXT, price REAL, qty REAL,
                pnl_pct REAL, pnl_usdt REAL, strategy TEXT, exit_type TEXT)""")
            conn.commit()

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def record_entry(self, symbol, price, qty, strategy):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO trades (ts,symbol,event,price,qty,strategy) VALUES (?,?,?,?,?,?)",
                         (self._now(), symbol, "ENTRY", price, qty, strategy))
            conn.commit()
        logger.info(f"trade_entry_logged {symbol} {price:.4f} {qty}")

    def record_exit(self, symbol, price, qty, entry_price, exit_type, strategy=""):
        pnl_pct = (price - entry_price) / entry_price * 100 if entry_price else 0
        pnl_usdt = (price - entry_price) * qty
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO trades (ts,symbol,event,price,qty,pnl_pct,pnl_usdt,strategy,exit_type) VALUES (?,?,?,?,?,?,?,?,?)",
                         (self._now(), symbol, "EXIT", price, qty, pnl_pct, pnl_usdt, strategy, exit_type))
            conn.commit()
        logger.info(f"trade_exit_logged {symbol} {exit_type} pnl={pnl_usdt:+.4f}")

    def get_closed_trades(self, limit=500):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT ts,symbol,price,qty,pnl_pct,pnl_usdt,strategy,exit_type "
                "FROM trades WHERE event='EXIT' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"ts": r[0], "symbol": r[1], "price": r[2], "qty": r[3], "pnl_pct": r[4],
                 "pnl_usdt": r[5], "strategy": r[6], "exit_type": r[7]} for r in rows]

    def get_summary(self):
        trades = self.get_closed_trades(10000)
        if not trades:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "profit_factor": 0, "total_pnl": 0}
        wins = [t for t in trades if (t["pnl_usdt"] or 0) > 0]
        losses = [t for t in trades if (t["pnl_usdt"] or 0) <= 0]
        gp = sum(t["pnl_usdt"] for t in wins)
        gl = abs(sum(t["pnl_usdt"] for t in losses))
        return {
            "total": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(trades) * 100, 1),
            "profit_factor": round(gp / gl, 2) if gl else float("inf"),
            "total_pnl": round(gp - gl, 4),
        }

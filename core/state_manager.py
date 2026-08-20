"""SQLite-backed state persistence (anti-corrupt, survives restart)."""
import os, sqlite3, logging
from dataclasses import dataclass
from typing import Optional

try:
    import structlog
    logger = structlog.get_logger("state_manager")
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("state_manager")

@dataclass
class BotState:
    symbol: str
    in_position: bool = False
    entry_price: float = 0.0
    entry_atr: float = 0.0
    quantity: float = 0.0
    sl_price: float = 0.0
    tp_price: float = 0.0
    oco_order_list_id: Optional[int] = None
    entry_ts: Optional[str] = None
    kill_switch_cooldown_until: Optional[str] = None
    strategy: str = ""
    breakeven_triggered: bool = False

class StateManager:
    def __init__(self, db_path="data/trades.db"):
        self.db_path = db_path
        d = os.path.dirname(db_path)
        if d: os.makedirs(d, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS state (
                symbol TEXT PRIMARY KEY, in_position INTEGER DEFAULT 0,
                entry_price REAL DEFAULT 0, entry_atr REAL DEFAULT 0,
                quantity REAL DEFAULT 0, sl_price REAL DEFAULT 0, tp_price REAL DEFAULT 0,
                oco_order_list_id INTEGER, entry_ts TEXT, kill_switch_cooldown_until TEXT,
                strategy TEXT DEFAULT '', breakeven_triggered INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.commit()

    def load_state(self, symbol):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT symbol,in_position,entry_price,entry_atr,quantity,sl_price,tp_price,oco_order_list_id,entry_ts,kill_switch_cooldown_until,strategy,breakeven_triggered FROM state WHERE symbol=?", (symbol,)).fetchone()
        if not row:
            return BotState(symbol=symbol)
        return BotState(symbol=row[0], in_position=bool(row[1]), entry_price=row[2],
            entry_atr=row[3], quantity=row[4], sl_price=row[5], tp_price=row[6],
            oco_order_list_id=row[7], entry_ts=row[8], kill_switch_cooldown_until=row[9],
            strategy=row[10] or "", breakeven_triggered=bool(row[11]))

    def save_state(self, state):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""INSERT OR REPLACE INTO state
                    (symbol,in_position,entry_price,entry_atr,quantity,sl_price,tp_price,
                     oco_order_list_id,entry_ts,kill_switch_cooldown_until,strategy,
                     breakeven_triggered,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (state.symbol, int(state.in_position), state.entry_price, state.entry_atr,
                     state.quantity, state.sl_price, state.tp_price, state.oco_order_list_id,
                     state.entry_ts, state.kill_switch_cooldown_until, state.strategy,
                     int(state.breakeven_triggered)))
                conn.commit()
            return True
        except Exception as e:
            logger.error("state_save_failed", symbol=state.symbol, error=str(e))
            return False

    def load_all_states(self, symbols):
        return {s: self.load_state(s) for s in symbols}

    def get_open_positions(self):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT symbol,entry_price,quantity,sl_price,tp_price,entry_ts,strategy FROM state WHERE in_position=1").fetchall()
        return [{"symbol": r[0], "entry_price": r[1], "quantity": r[2], "sl_price": r[3],
                 "tp_price": r[4], "entry_ts": r[5], "strategy": r[6]} for r in rows]

    def update_breakeven(self, symbol, new_sl):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE state SET sl_price=?, breakeven_triggered=1, updated_at=CURRENT_TIMESTAMP WHERE symbol=? AND in_position=1", (new_sl, symbol))
            conn.commit()
        logger.info("breakeven_updated", symbol=symbol, new_sl=new_sl)

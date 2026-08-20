"""RiskManager: hak veto entry + sizing dengan clamp exposure (v3 logic)."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import structlog
    logger = structlog.get_logger("risk_manager")
except ImportError:
    logger = logging.getLogger("risk_manager")

FEE_ROUND_TRIP = 0.002

@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""
    adjusted_quote: float = 0.0

class RiskManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self._daily_start = self._weekly_start = self._peak = None
        self._daily_date = self._weekly_week = None

    def initialize(self, equity):
        now = datetime.now(timezone.utc)
        self._daily_start = self._weekly_start = self._peak = equity
        self._daily_date = now.strftime("%Y-%m-%d")
        self._weekly_week = now.strftime("%G-W%V")
        logger.info(f"risk_initialized equity={equity:.2f}")

    def _resets(self, equity):
        now = datetime.now(timezone.utc)
        if self._daily_date != now.strftime("%Y-%m-%d"):
            self._daily_start = equity; self._daily_date = now.strftime("%Y-%m-%d")
        if self._weekly_week != now.strftime("%G-W%V"):
            self._weekly_start = equity; self._weekly_week = now.strftime("%G-W%V")
        if self._peak is None or equity > self._peak:
            self._peak = equity

    def _exposure(self, states, symbol):
        asset = total = 0.0
        for sym, st in states.items():
            if st.in_position and st.entry_price > 0:
                v = st.quantity * st.entry_price
                total += v
                if sym == symbol: asset += v
        return asset, total

    def evaluate_entry(self, symbol, equity, states, entry_price=0.0, sl_price=0.0):
        c = self.cfg
        if self._peak is None:
            self.initialize(equity)
        self._resets(equity)

        if self._daily_start and (equity - self._daily_start) / self._daily_start * 100 <= -c["daily_loss_limit_pct"]:
            return RiskDecision(False, "DAILY LOSS LIMIT")
        if self._weekly_start and (equity - self._weekly_start) / self._weekly_start * 100 <= -c["weekly_loss_limit_pct"]:
            return RiskDecision(False, "WEEKLY LOSS LIMIT")
        if self._peak and (self._peak - equity) / self._peak * 100 >= c["max_drawdown_pct"]:
            return RiskDecision(False, "MAX DRAWDOWN")

        open_count = sum(1 for s in states.values() if s.in_position)
        if open_count >= c["max_open_positions"]:
            return RiskDecision(False, f"MAX POSITIONS ({open_count}/{c['max_open_positions']})")

        ex_asset, ex_total = self._exposure(states, symbol)
        if equity > 0:
            if ex_asset / equity * 100 >= c["max_exposure_per_asset_pct"]:
                return RiskDecision(False, "ASSET EXPOSURE")
            if ex_total / equity * 100 >= c["max_total_exposure_pct"]:
                return RiskDecision(False, "TOTAL EXPOSURE")

        st = states.get(symbol)
        if st and st.kill_switch_cooldown_until:
            try:
                until = datetime.fromisoformat(st.kill_switch_cooldown_until)
                if until.tzinfo is None: until = until.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) < until:
                    return RiskDecision(False, "KILL SWITCH COOLDOWN")
            except ValueError:
                pass

        # Sizing risk-based + CLAMP exposure (anti-oversize)
        if entry_price > 0 and sl_price > 0 and entry_price > sl_price:
            risk_amount = equity * (c["risk_per_trade_pct"] / 100.0)
            total_risk = (entry_price - sl_price) + entry_price * FEE_ROUND_TRIP
            sized = (risk_amount / total_risk) * entry_price
        else:
            sized = equity * (c["risk_per_trade_pct"] / 100.0)

        cap_asset = equity * c["max_exposure_per_asset_pct"] / 100.0 - ex_asset
        cap_total = equity * c["max_total_exposure_pct"] / 100.0 - ex_total
        cap_spot = equity - ex_total
        quote = max(0.0, min(sized, cap_asset, cap_total, cap_spot))

        if quote < 10.0:
            return RiskDecision(False, f"QUOTE TOO SMALL ({quote:.2f})")
        logger.info(f"risk_approved symbol={symbol} quote={quote:.2f} sized={sized:.2f}")
        return RiskDecision(True, "OK", quote)

    def get_status(self, equity, states):
        self._resets(equity)
        d = (equity - self._daily_start) / self._daily_start * 100 if self._daily_start else 0
        w = (equity - self._weekly_start) / self._weekly_start * 100 if self._weekly_start else 0
        dd = (self._peak - equity) / self._peak * 100 if self._peak else 0
        _, ex = self._exposure(states, "")
        exp = ex / equity * 100 if equity else 0
        return (f"Equity: {equity:.2f} | Daily: {d:+.2f}% | Weekly: {w:+.2f}% | "
                f"DD: {dd:.2f}% | Exposure: {exp:.1f}%")

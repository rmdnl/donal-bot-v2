"""Breakeven: geser SL ke entry setelah profit >= N x ATR."""
import logging
logger = logging.getLogger("breakeven")

class BreakevenManager:
    def __init__(self, enabled=True, trigger_atr_multiplier=1.0):
        self.enabled = enabled
        self.trigger = trigger_atr_multiplier

    def check(self, state, current_price):
        if not self.enabled or not state.in_position or state.breakeven_triggered:
            return None
        if state.entry_atr <= 0 or state.entry_price <= 0:
            return None
        if (current_price - state.entry_price) >= state.entry_atr * self.trigger:
            logger.info(f"breakeven_trigger symbol={state.symbol} px={current_price:.4f}")
            return state.entry_price
        return None

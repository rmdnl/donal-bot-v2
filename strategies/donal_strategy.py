"""Strategi DONAL: filter tren 4H + breakout HH20 di 1H (pure signal)."""
from dataclasses import dataclass
from .indicators import ema, rsi, atr, highest

@dataclass
class DonalSignal:
    buy_signal: bool
    sell_signal: bool
    close: float
    atr_value: float

class DonalStrategy:
    def __init__(self, cfg):
        self.cfg = cfg

    def compute(self, df_1h, df_4h):
        c = self.cfg
        ef = ema(df_4h["close"], c["ema_fast_length"]).iloc[-1]
        es = ema(df_4h["close"], c["ema_slow_length"]).iloc[-1]
        hr = rsi(df_4h["close"], c["rsi_period"]).iloc[-1]
        bull = bool(ef > es and hr > 50)

        close = df_1h["close"]
        e20 = float(ema(close, c["ema_fast_length"]).iloc[-1])
        r = float(rsi(close, c["rsi_period"]).iloc[-1])
        hh20_prev = float(highest(df_1h["high"], c["highest_high_period"]).shift(1).iloc[-1])
        a = float(atr(df_1h, c["atr_period"]).iloc[-1])
        cl = float(close.iloc[-1])

        buy = bool(bull and cl > e20 and r > c["rsi_entry_level"] and cl > hh20_prev)
        sell = bool(cl < e20 or r < c["rsi_exit_level"])
        return DonalSignal(buy, sell, cl, a)

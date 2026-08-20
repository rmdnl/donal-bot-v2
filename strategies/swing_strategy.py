"""DONAL Swing: trend Daily + breakout 4H + trailing stop.

Logika biaya-sehat: trade jarang, move besar (4H ATR), fee jadi kecil
relatif terhadap target. Cocok jadi kandidat bot utama JIKA lulus backtest.
"""
from dataclasses import dataclass
from .indicators import ema, rsi, atr, highest

@dataclass
class SwingSignal:
    buy_signal: bool
    close: float
    atr_value: float
    hh_prev: float

class SwingStrategy:
    def __init__(self, cfg):
        self.cfg = cfg

    def trend_up(self, df_1d):
        c = self.cfg
        ef = ema(df_1d["close"], c["ema_fast"]).iloc[-1]
        es = ema(df_1d["close"], c["ema_slow"]).iloc[-1]
        r = rsi(df_1d["close"], c["rsi_period"]).iloc[-1]
        return bool(ef > es and r > 50)

    def compute(self, df_4h):
        c = self.cfg
        close = df_4h["close"]
        cl = float(close.iloc[-1])
        a = float(atr(df_4h, c["atr_period"]).iloc[-1])
        hh_prev = float(highest(df_4h["high"], c["hh_period"]).shift(1).iloc[-1])
        buy = bool(cl > hh_prev)
        return SwingSignal(buy, cl, a, hh_prev)

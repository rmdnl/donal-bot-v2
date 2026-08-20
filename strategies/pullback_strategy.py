"""Strategi Pullback 15m: filter trend 4H + entry pullback di 15m.

Logika:
- Filter 4H: EMA20 > EMA50 + RSI > 50 (trend naik)
- Entry 15m: harga pullback ke EMA20, close bullish
- Exit: SL 1.5 ATR, TP 4 ATR (RR 1:2.67) atau time stop
"""
from dataclasses import dataclass
from .indicators import ema, rsi, atr

@dataclass
class PullbackSignal:
    buy_signal: bool
    close: float
    atr_value: float

class PullbackStrategy:
    def __init__(self, cfg):
        self.cfg = cfg

    def trend_up_4h(self, df_4h):
        c = self.cfg
        ef = ema(df_4h["close"], c["ema_fast"]).iloc[-1]
        es = ema(df_4h["close"], c["ema_slow"]).iloc[-1]
        r = rsi(df_4h["close"], c["rsi_period"]).iloc[-1]
        return bool(ef > es and r > 50)

    def compute(self, df_15m):
        c = self.cfg
        close = df_15m["close"]
        e20 = ema(close, c["ema_entry"]).iloc[-1]
        e50 = ema(close, c["ema_trend"]).iloc[-1]
        r = rsi(close, c["rsi_period"]).iloc[-1]
        a = atr(df_15m, c["atr_period"]).iloc[-1]
        cl = float(close.iloc[-1])
        op = float(df_15m["open"].iloc[-1])
        
        # Pullback: close < EMA20 tapi close > EMA50 (pullback tapi masih uptrend)
        # Konfirmasi bullish: close > open
        pullback = cl < float(e20) and cl > float(e50)
        bullish = cl > op
        
        buy = bool(pullback and bullish and r > 40)
        return PullbackSignal(buy, cl, float(a))

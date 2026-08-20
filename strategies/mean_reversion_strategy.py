"""Mean Reversion: Bollinger Bands + RSI untuk market sideways."""
from dataclasses import dataclass
from .indicators import atr, rsi

@dataclass
class MRSignal:
    buy_signal: bool
    sell_signal: bool
    close: float
    atr_value: float

class MeanReversionStrategy:
    def __init__(self, cfg):
        self.cfg = cfg

    def compute(self, df_1h):
        c = self.cfg
        close = df_1h["close"]
        mid = close.rolling(c["bb_period"]).mean()
        std = close.rolling(c["bb_period"]).std()
        lower = mid - std * c["bb_std"]

        r = float(rsi(close, c["rsi_period"]).iloc[-1])
        cl = float(close.iloc[-1])
        buy = bool(cl < float(lower.iloc[-1]) and r < c["rsi_oversold"])
        sell = bool(cl > float(mid.iloc[-1]) or r > 50)
        return MRSignal(buy, sell, cl, float(atr(df_1h, 14).iloc[-1]))

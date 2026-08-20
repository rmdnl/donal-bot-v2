"""Strategi DONAL: filter tren 4H + breakout HH20 di 1H.

Perbaikan edge (anti false-breakout):
- Konfirmasi volume: breakout wajib disertai volume > rata-rata
- Slope EMA: EMA20 1H wajib menanjak (trend nyata, bukan sideways)
"""
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
        # Filter tren 4H
        ef = ema(df_4h["close"], c["ema_fast_length"]).iloc[-1]
        es = ema(df_4h["close"], c["ema_slow_length"]).iloc[-1]
        hr = rsi(df_4h["close"], c["rsi_period"]).iloc[-1]
        bull = bool(ef > es and hr > 50)

        close = df_1h["close"]
        e20_s = ema(close, c["ema_fast_length"])
        e20 = float(e20_s.iloc[-1])
        r = float(rsi(close, c["rsi_period"]).iloc[-1])
        hh20_prev = float(highest(df_1h["high"], c["highest_high_period"]).shift(1).iloc[-1])
        a = float(atr(df_1h, c["atr_period"]).iloc[-1])
        cl = float(close.iloc[-1])

        # Konfirmasi volume (saring false breakout)
        vol_ok = True
        if c.get("volume_confirm", True):
            vol = df_1h["volume"]
            avg_prev = float(vol.rolling(c.get("volume_period", 20)).mean().shift(1).iloc[-1])
            last_vol = float(vol.iloc[-1])
            vol_ok = last_vol > avg_prev * c.get("volume_multiplier", 1.5) if avg_prev > 0 else True

        # Slope EMA20 1H menanjak (trend nyata)
        slope_ok = True
        if c.get("require_ema_slope", True):
            slope_ok = e20_s.iloc[-1] > e20_s.iloc[-3]

        buy = bool(bull and cl > e20 and r > c["rsi_entry_level"]
                   and cl > hh20_prev and vol_ok and slope_ok)
        sell = bool(cl < e20 or r < c["rsi_exit_level"])
        return DonalSignal(buy, sell, cl, a)

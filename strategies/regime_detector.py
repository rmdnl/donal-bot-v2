"""Deteksi regime market: TREND / SIDEWAYS / BEAR / TRANSITION (ADX + EMA 4H)."""
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd

class Regime(Enum):
    TREND = "TREND"
    SIDEWAYS = "SIDEWAYS"
    BEAR = "BEAR"
    TRANSITION = "TRANSITION"

@dataclass
class RegimeResult:
    mode: Regime
    adx: float
    ema20: float
    ema60: float
    ema_slope: float
    reason: str

def compute_adx(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([high - low, (high - close.shift(1)).abs(),
                    (low - close.shift(1)).abs()], axis=1).max(axis=1)
    up = high - high.shift(1)
    down = low.shift(1) - low
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr_s = tr.ewm(alpha=1/period, adjust=False).mean()
    p_s = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    m_s = minus_dm.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * p_s / tr_s
    minus_di = 100 * m_s / tr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1/period, adjust=False).mean()

def detect_regime(df_4h, adx_period=14, adx_trend_threshold=25.0,
                  adx_sideways_threshold=20.0, ema_fast=20, ema_slow=60):
    if len(df_4h) < max(adx_period, ema_slow) + 10:
        return RegimeResult(Regime.TRANSITION, 0, 0, 0, 0, "data kurang")
    adx = float(compute_adx(df_4h, adx_period).iloc[-1])
    close = df_4h["close"]
    e20 = close.ewm(span=ema_fast, adjust=False).mean()
    e60 = close.ewm(span=ema_slow, adjust=False).mean()
    e20_v, e60_v = float(e20.iloc[-1]), float(e60.iloc[-1])
    slope = (e20_v - float(e20.iloc[-5])) / float(e20.iloc[-5]) * 100 if len(e20) >= 5 else 0.0
    if adx > adx_trend_threshold and e20_v > e60_v:
        return RegimeResult(Regime.TREND, adx, e20_v, e60_v, slope, f"bull trend ADX={adx:.1f}")
    if adx < adx_sideways_threshold:
        return RegimeResult(Regime.SIDEWAYS, adx, e20_v, e60_v, slope, f"sideways ADX={adx:.1f}")
    if e20_v < e60_v:
        return RegimeResult(Regime.BEAR, adx, e20_v, e60_v, slope, f"bear slope={slope:.1f}%")
    return RegimeResult(Regime.TRANSITION, adx, e20_v, e60_v, slope, "transisi")

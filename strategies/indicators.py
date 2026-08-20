"""Indikator teknikal - Wilder smoothing (sinkron dengan TradingView)."""
import pandas as pd

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    al = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    val = 100 - (100 / (1 + ag / al))
    return val.where(al != 0, 100.0)

def atr(df, length=14):
    high, low, prev = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

def highest(series, length):
    return series.rolling(window=length).max()

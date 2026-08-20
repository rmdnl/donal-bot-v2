import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.regime_detector import detect_regime, Regime

def _df(closes):
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame({"open": closes, "high": closes * 1.001,
                         "low": closes * 0.999, "close": closes,
                         "volume": np.ones(len(closes)) * 100})

def test_uptrend():
    assert detect_regime(_df(np.linspace(100, 150, 200))).mode == Regime.TREND

def test_downtrend():
    assert detect_regime(_df(np.linspace(150, 100, 200))).mode == Regime.BEAR

def test_sideways():
    rng = np.random.RandomState(42)
    assert detect_regime(_df(100 + rng.normal(0, 0.2, 200))).mode == Regime.SIDEWAYS

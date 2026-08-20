"""Smoke test Phase 2: fetch data publik, cetak regime + sinyal per symbol."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.binance_client import BinanceSpotBot
from core.config_loader import ConfigLoader
from strategies.regime_detector import detect_regime, Regime
from strategies.donal_strategy import DonalStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy

def main():
    cfg = ConfigLoader("config.yaml").load()
    client = BinanceSpotBot("", "", testnet=False)  # public data, tanpa key

    for sym in cfg["trading"]["symbols"]:
        df1 = client.get_closed_klines(sym, "1h", 200)
        df4 = client.get_closed_klines(sym, "4h", 100)
        reg = detect_regime(df4)
        print(f"{sym}: regime={reg.mode.value} ADX={reg.adx:.1f} | {reg.reason}")
        if reg.mode == Regime.SIDEWAYS:
            sig = MeanReversionStrategy(cfg["strategy"]["mean_reversion"]).compute(df1)
            print(f"   MR    : buy={sig.buy_signal} sell={sig.sell_signal} close={sig.close:.2f} atr={sig.atr_value:.4f}")
        else:
            sig = DonalStrategy(cfg["strategy"]["donal"]).compute(df1, df4)
            print(f"   DONAL : buy={sig.buy_signal} sell={sig.sell_signal} close={sig.close:.2f} atr={sig.atr_value:.4f}")
    print("=== SMOKE TEST OK ===")

if __name__ == "__main__":
    main()

"""Download data historis dari Binance (public API, tanpa key)."""
import argparse, os, sys, time
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.binance_client import BinanceSpotBot, KLINE_COLUMNS

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def fetch(symbol, interval, months):
    client = BinanceSpotBot("", "", testnet=False)
    end = int(time.time() * 1000)
    start = end - int(months * 30 * 24 * 3600 * 1000)
    rows, s = [], start
    while s < end:
        k = client.client.get_klines(symbol=symbol, interval=interval,
                                     startTime=s, endTime=end, limit=1000)
        if not k: break
        rows += k
        s = k[-1][0] + 1
        if len(k) < 1000: break
        time.sleep(0.2)
    df = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    for c in ["open","high","low","close","volume"]: df[c] = df[c].astype(float)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    return df.drop_duplicates("close_time").reset_index(drop=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", default="BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT")
    p.add_argument("--months", type=int, default=6)
    p.add_argument("--intervals", default="1h,4h,15m")
    a = p.parse_args()
    os.makedirs(DATA_DIR, exist_ok=True)
    for sym in [s.strip() for s in a.symbols.split(",")]:
        for iv in [x.strip() for x in a.intervals.split(",")]:
            df = fetch(sym, iv, a.months)
            f = os.path.join(DATA_DIR, f"{sym}_{iv}.csv")
            df.to_csv(f, index=False)
            print(f"  {sym} {iv}: {len(df)} candles -> {f}")

if __name__ == "__main__":
    main()

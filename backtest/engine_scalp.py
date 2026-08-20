"""Backtest scalping mean-reversion 5m (desain high-WR).

Desain: beli saat oversold ekstrem (close < lower BB + RSI rendah),
keluar cepat di mean (TP kecil => WR tinggi), SL ketat + time stop.
Yang diuji BUKAN cuma WR, tapi EXPECTANCY net biaya.
"""
import argparse, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.indicators import rsi, atr
from backtest.engine import FEE_PCT, SLIPPAGE_PCT, MIN_NOTIONAL

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SPREAD_PCT = 0.0002   # estimasi half-spread

def bb(close, period=20, std=2.0):
    mid = close.rolling(period).mean()
    sd = close.rolling(period).std()
    return mid, mid - std*sd, mid + std*sd

def load(symbol, iv):
    f = os.path.join(DATA_DIR, f"{symbol}_{iv}.csv")
    if not os.path.exists(f): raise FileNotFoundError(f"{f} tidak ada")
    return pd.read_csv(f, parse_dates=["close_time"])

def run_scalp(symbol, df, capital=1000.0, risk_pct=0.5, rsi_buy=30, sl_atr=1.5, max_bars=12):
    mid, lower, upper = bb(df["close"])
    r = rsi(df["close"], 14)
    a = atr(df, 14)
    cost = (FEE_PCT + SLIPPAGE_PCT + SPREAD_PCT)  # per side

    cap=capital; trades=[]; in_pos=False
    entry=0.0; qty=0.0; sl=0.0; ei=0

    for i in range(30, len(df)):
        c=float(df.iloc[i]["close"]); h=float(df.iloc[i]["high"]); l=float(df.iloc[i]["low"])
        if in_pos:
            bars=i-ei
            exit_px=None; et=None
            if l<=sl: exit_px,et=sl,"SL"
            elif c>=float(mid.iloc[i]): exit_px,et=c,"TP_MEAN"
            elif bars>=max_bars: exit_px,et=c,"TIME"
            if exit_px:
                ep=exit_px*(1-SLIPPAGE_PCT)
                fee=(entry+ep)*cost
                pnl=(ep-entry-fee)*qty
                cap+=pnl+entry*qty
                trades.append({"pnl_usdt":pnl,"exit_type":et,
                    "gross_pct":(ep-entry)/entry*100,"net_pct":pnl/(entry*qty)*100})
                in_pos=False
        else:
            if c<float(lower.iloc[i]) and float(r.iloc[i])<rsi_buy and float(a.iloc[i])>0:
                ep=c*(1+SLIPPAGE_PCT)
                risk=cap*(risk_pct/100.0)
                q=risk/(ep*sl_atr*float(a.iloc[i])/ep + ep*cost*2) if a.iloc[i]>0 else 0
                if q>0 and ep*q>=MIN_NOTIONAL:
                    cap-=ep*q; in_pos=True; entry=ep; qty=q
                    sl=ep-sl_atr*float(a.iloc[i]); ei=i

    if not trades: print("No trades"); return
    w=[t for t in trades if t["pnl_usdt"]>0]; lo=[t for t in trades if t["pnl_usdt"]<=0]
    wr=len(w)/len(trades)*100
    aw=sum(t["pnl_usdt"] for t in w)/len(w) if w else 0
    al=abs(sum(t["pnl_usdt"] for t in lo)/len(lo)) if lo else 0
    exp=sum(t["pnl_usdt"] for t in trades)/len(trades)
    gp=sum(t["pnl_usdt"] for t in w); gl=abs(sum(t["pnl_usdt"] for t in lo))
    print(f"\n=== {symbol} SCALP 5m | {len(trades)} trades ===")
    print(f"WinRate {wr:.1f}% | AvgWin ${aw:.3f} | AvgLoss ${al:.3f}")
    print(f"Expectancy/trade ${exp:+.4f} | PF {gp/gl if gl else float('inf'):.2f}")
    print(f"Total PnL ${sum(t['pnl_usdt'] for t in trades):+.2f}")
    from collections import Counter
    for k,v in Counter(t["exit_type"] for t in trades).items(): print(f"  {k}: {v}x")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",default="BTCUSDT")
    a=p.parse_args()
    df=load(a.symbol,"5m")
    run_scalp(a.symbol,df)

if __name__=="__main__":
    main()

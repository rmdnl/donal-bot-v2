"""Backtest Pullback 15m dengan filter trend 4H."""
import argparse, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import ConfigLoader
from strategies.pullback_strategy import PullbackStrategy
from strategies.indicators import ema, rsi, atr
from backtest.engine import calc, FEE_PCT, SLIPPAGE_PCT, MIN_NOTIONAL, RESULTS_DIR

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def load(symbol, iv):
    f = os.path.join(DATA_DIR, f"{symbol}_{iv}.csv")
    if not os.path.exists(f):
        raise FileNotFoundError(f"{f} tidak ada. Run download_data --intervals 15m,4h")
    return pd.read_csv(f, parse_dates=["close_time"])

def run_pullback(symbol, df15, df4h, cfg, capital=1000.0, risk_pct=0.5, max_exp=7.5, max_bars=288):
    sc = cfg["strategy"]["pullback"]
    strat = PullbackStrategy(sc)
    sl_atr = sc["sl_atr"]; tp_atr = sc["tp_atr"]

    e20_15 = ema(df15["close"], sc["ema_entry"])
    e50_15 = ema(df15["close"], sc["ema_trend"])
    atr15 = atr(df15, sc["atr_period"])
    e20_4h = ema(df4h["close"], sc["ema_fast"])
    e50_4h = ema(df4h["close"], sc["ema_slow"])
    rsi4h = rsi(df4h["close"], sc["rsi_period"])

    cap = capital; trades = []; equity = []
    in_pos=False; entry=0.0; qty=0.0; sl=0.0; tp=0.0; ei=0

    def close(px, etype, i, ts):
        nonlocal cap, in_pos, qty
        ep = px * (1 - SLIPPAGE_PCT)
        fee = (entry + ep) * FEE_PCT
        pnl = (ep - entry - fee) * qty
        cap += pnl + entry * qty
        trades.append({"entry_price":entry,"exit_price":ep,"exit_type":etype,
                       "strategy":"PULLBACK","pnl_pct":round((ep-entry)/entry*100,4),
                       "pnl_usdt":round(pnl,4),"hold_bars":i-ei})
        in_pos=False; qty=0.0
        equity.append({"time":ts,"equity":cap})

    qi = 0
    warm = max(60, sc["ema_trend"])
    for i in range(warm, len(df15)):
        t = df15.iloc[i]["close_time"]
        while qi + 1 < len(df4h) and df4h.iloc[qi+1]["close_time"] <= t:
            qi += 1
        hi=float(df15.iloc[i]["high"]); lo=float(df15.iloc[i]["low"])
        cl=float(df15.iloc[i]["close"]); op=float(df15.iloc[i]["open"])
        ts=str(t)

        if in_pos:
            bars = i - ei
            if lo <= sl: close(sl,"SL",i,ts); continue
            if hi >= tp: close(tp,"TP",i,ts); continue
            if bars >= max_bars: close(cl,"TIME",i,ts); continue

        trend_4h = bool(e20_4h.iloc[qi] > e50_4h.iloc[qi] and rsi4h.iloc[qi] > 50)

        if not in_pos and trend_4h:
            a = float(atr15.iloc[i])
            # Pullback + bullish confirmation
            if cl < float(e20_15.iloc[i]) and cl > float(e50_15.iloc[i]) and cl > op and a > 0:
                ep = cl * (1 + SLIPPAGE_PCT)
                risk = cap * (risk_pct/100.0)
                tr = (ep - (ep - sl_atr*a)) + ep*(FEE_PCT*2)
                q = risk/tr if tr>0 else 0.0
                mx = min(cap*(max_exp/100.0), cap)
                if ep*q > mx: q = mx/ep
                if q>0 and ep*q>=MIN_NOTIONAL:
                    cap -= ep*q; in_pos=True; entry=ep; qty=q
                    sl = ep - sl_atr*a; tp = ep + tp_atr*a; ei=i

        equity.append({"time":ts,"equity":cap + (cl*qty if in_pos else 0)})

    if in_pos: close(float(df15.iloc[-1]["close"]),"END",len(df15)-1,str(df15.iloc[-1]["close_time"]))
    return {"symbol":symbol,"trades":trades,"equity":equity,
            "metrics":calc(trades,capital,cap,equity,{})}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",default="BTCUSDT")
    p.add_argument("--capital",type=float,default=1000)
    p.add_argument("--risk_pct",type=float,default=0.5)
    a=p.parse_args()
    cfg=ConfigLoader("config.yaml").load()
    df15=load(a.symbol,"15m"); df4h=load(a.symbol,"4h")
    res=run_pullback(a.symbol,df15,df4h,cfg,a.capital,a.risk_pct,
                     cfg["risk"]["max_exposure_per_asset_pct"])
    m=res["metrics"]
    print(f"\n=== {a.symbol} | PULLBACK 15m (Filter 4H) ===")
    if m.get("total_trades",0)==0: print("No trades"); return
    print(f"Return {m['return_pct']:+.2f}% | WR {m['win_rate']}% | PF {m['profit_factor']} | MaxDD {m['max_dd']}% | {m['total_trades']} trades")
    for e,d in m.get("by_exit",{}).items(): print(f"  {e}: {d['count']}x ${d['pnl']:+.2f}")
    os.makedirs(RESULTS_DIR,exist_ok=True)
    with open(os.path.join(RESULTS_DIR,f"trades_{a.symbol}_pullback.jsonl"),"w") as f:
        for t in res["trades"]: f.write(json.dumps(t)+"\n")
    pd.DataFrame(res["equity"]).to_csv(os.path.join(RESULTS_DIR,f"equity_{a.symbol}_pullback.csv"),index=False)

if __name__=="__main__":
    main()

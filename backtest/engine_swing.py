"""Backtest DONAL Swing v2 (partial TP + tighter trail + hard SL).

Perbaikan mekanika exit:
- Hard SL: 1.5 ATR (lebih ketat)
- Partial TP: keluar 50% di +2 ATR (kunci profit)
- Trail sisanya: 2 ATR (kurangi give-back)
"""
import argparse, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import ConfigLoader
from strategies.swing_strategy import SwingStrategy
from strategies.indicators import ema, rsi, atr, highest
from backtest.engine import calc, FEE_PCT, SLIPPAGE_PCT, MIN_NOTIONAL, RESULTS_DIR

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def load(symbol, iv):
    f = os.path.join(DATA_DIR, f"{symbol}_{iv}.csv")
    if not os.path.exists(f):
        raise FileNotFoundError(f"{f} tidak ada")
    return pd.read_csv(f, parse_dates=["close_time"])

def run_swing(symbol, df4, df1d, cfg, capital=1000.0, risk_pct=0.5, max_exp=7.5):
    sc = cfg["strategy"]["swing"]
    strat = SwingStrategy(sc)
    sl_atr = sc["sl_atr"]; trail_atr = sc["trail_atr"]
    pt_atr = sc.get("partial_tp_atr", 2.0); pt_pct = sc.get("partial_tp_pct", 50)

    hh_prev = highest(df4["high"], sc["hh_period"]).shift(1)
    atr4 = atr(df4, sc["atr_period"])
    d_ef = ema(df1d["close"], sc["ema_fast"])
    d_es = ema(df1d["close"], sc["ema_slow"])
    d_rsi = rsi(df1d["close"], sc["rsi_period"])

    cap = capital; trades = []; equity = []
    in_pos=False; entry=0.0; qty=0.0; hard_sl=0.0; max_high=0.0; atr_e=0.0; ei=0
    tp1_price=0.0; tp1_taken=False; qty_rem=0.0

    def close(px, etype, i, ts, q=None):
        nonlocal cap, in_pos, qty, tp1_taken, qty_rem
        if q is None: q = qty
        ep = px * (1 - SLIPPAGE_PCT)
        fee = (entry + ep) * FEE_PCT
        pnl = (ep - entry - fee) * q
        cap += pnl + entry * q
        trades.append({"entry_price":entry,"exit_price":ep,"exit_type":etype,
                       "strategy":"SWING","pnl_pct":round((ep-entry)/entry*100,4),
                       "pnl_usdt":round(pnl,4),"hold_bars":i-ei})
        qty -= q
        if qty <= 0:
            in_pos=False; qty=0.0; tp1_taken=False; qty_rem=0.0
        equity.append({"time":ts,"equity":cap})

    di = 0
    warm = max(sc["hh_period"], 60)
    for i in range(warm, len(df4)):
        t = df4.iloc[i]["close_time"]
        while di + 1 < len(df1d) and df1d.iloc[di+1]["close_time"] <= t:
            di += 1
        hi=float(df4.iloc[i]["high"]); lo=float(df4.iloc[i]["low"])
        ts=str(t)

        if in_pos:
            max_high = max(max_high, hi)
            # Hard SL
            if lo <= hard_sl: close(hard_sl,"SL",i,ts); continue
            # Partial TP (50% di +2 ATR)
            if not tp1_taken and hi >= tp1_price:
                q_half = qty_rem
                close(tp1_price,"TP1",i,ts,q=q_half)
                tp1_taken = True
                if not in_pos: continue
            # Trail stop (2 ATR)
            trail_stop = max_high - trail_atr * atr_e
            if lo <= trail_stop: close(trail_stop,"TRAIL",i,ts); continue

        trend = bool(d_ef.iloc[di] > d_es.iloc[di] and d_rsi.iloc[di] > 50)

        if not in_pos and trend:
            cl=float(df4.iloc[i]["close"]); a=float(atr4.iloc[i]); hh=float(hh_prev.iloc[i])
            if cl > hh and a > 0:
                ep = cl * (1 + SLIPPAGE_PCT)
                risk = cap * (risk_pct/100.0)
                tr = (ep - (ep - sl_atr*a)) + ep*(FEE_PCT*2)
                q = risk/tr if tr>0 else 0.0
                mx = min(cap*(max_exp/100.0), cap)
                if ep*q > mx: q = mx/ep
                if q>0 and ep*q>=MIN_NOTIONAL:
                    cap -= ep*q; in_pos=True; entry=ep; qty=q; qty_rem=q
                    hard_sl = ep - sl_atr*a; tp1_price = ep + pt_atr*a
                    max_high=ep; atr_e=a; ei=i

        equity.append({"time":ts,"equity":cap + (df4.iloc[i]["close"]*qty if in_pos else 0)})

    if in_pos: close(float(df4.iloc[-1]["close"]),"END",len(df4)-1,str(df4.iloc[-1]["close_time"]))
    return {"symbol":symbol,"trades":trades,"equity":equity,
            "metrics":calc(trades,capital,cap,equity,{})}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",default="BTCUSDT")
    p.add_argument("--capital",type=float,default=1000)
    p.add_argument("--risk_pct",type=float,default=0.5)
    a=p.parse_args()
    cfg=ConfigLoader("config.yaml").load()
    df4=load(a.symbol,"4h"); df1d=load(a.symbol,"1d")
    res=run_swing(a.symbol,df4,df1d,cfg,a.capital,a.risk_pct,
                  cfg["risk"]["max_exposure_per_asset_pct"])
    m=res["metrics"]
    print(f"\n=== {a.symbol} | DONAL SWING v2 (Partial TP + Tight Trail) ===")
    if m.get("total_trades",0)==0: print("No trades"); return
    print(f"Return {m['return_pct']:+.2f}% | WR {m['win_rate']}% | PF {m['profit_factor']} | MaxDD {m['max_dd']}% | {m['total_trades']} trades")
    for e,d in m.get("by_exit",{}).items(): print(f"  {e}: {d['count']}x ${d['pnl']:+.2f}")
    os.makedirs(RESULTS_DIR,exist_ok=True)
    with open(os.path.join(RESULTS_DIR,f"trades_{a.symbol}_swing_v2.jsonl"),"w") as f:
        for t in res["trades"]: f.write(json.dumps(t)+"\n")
    pd.DataFrame(res["equity"]).to_csv(os.path.join(RESULTS_DIR,f"equity_{a.symbol}_swing_v2.csv"),index=False)

if __name__=="__main__":
    main()

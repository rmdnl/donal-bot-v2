"""Backtest engine multi-regime - identik dengan logika live bot.

Import strategies yang SAMA dengan bot live (no duplicate logic).
Usage:
    python -m backtest.engine --symbol BNBUSDT --months 6
    python -m backtest.engine --symbol BNBUSDT --no_regime   # A/B test
"""
import argparse, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import ConfigLoader
from strategies.regime_detector import detect_regime, Regime
from strategies.donal_strategy import DonalStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
FEE_PCT = 0.001
SLIPPAGE_PCT = 0.0005
MIN_NOTIONAL = 10.0

def load(symbol, iv):
    f = os.path.join(DATA_DIR, f"{symbol}_{iv}.csv")
    if not os.path.exists(f):
        raise FileNotFoundError(f"{f} tidak ada. Run: python -m backtest.download_data")
    return pd.read_csv(f, parse_dates=["close_time"])

def run_backtest(symbol, df1, df4, cfg, capital=1000.0, risk_pct=0.5,
                 max_exp=7.5, multi_regime=True):
    sc = cfg["strategy"]
    donal = DonalStrategy(sc["donal"])
    mr = MeanReversionStrategy(sc["mean_reversion"])
    sld, tpd = sc["donal"]["sl_multiplier"], sc["donal"]["tp_multiplier"]
    slm, tpm = sc["mean_reversion"]["sl_multiplier"], sc["mean_reversion"]["tp_multiplier"]

    cap = capital; trades = []; equity = []
    rc = {"TREND":0,"SIDEWAYS":0,"BEAR":0,"TRANSITION":0}
    in_pos=False; strat=""; entry=0.0; sl=0.0; tp=0.0; qty=0.0; ei=0
    cached=None; last4=-1

    def close(exit_raw, etype, i, ts):
        nonlocal cap, in_pos, qty, strat
        ep = exit_raw * (1 - SLIPPAGE_PCT)
        fee = (entry + ep) * FEE_PCT
        pnl = (ep - entry - fee) * qty
        cap += pnl + entry * qty
        trades.append({"entry_time":str(df1.iloc[ei]["close_time"]),"entry_price":entry,
                       "exit_time":ts,"exit_price":ep,"exit_type":etype,"strategy":strat,
                       "pnl_pct":round((ep-entry)/entry*100,4),"pnl_usdt":round(pnl,4),
                       "hold_bars":i-ei})
        in_pos=False; strat=""; qty=0.0
        equity.append({"time":ts,"equity":cap})

    def open_tr(ep, s, t, st, i):
        nonlocal cap, in_pos, qty, strat, entry, sl, tp, ei
        risk = cap * (risk_pct/100.0)
        tr = (ep - s) + ep*(FEE_PCT*2)
        q = risk/tr if tr>0 else 0.0
        mx = min(cap*(max_exp/100.0), cap)
        if ep*q > mx: q = mx/ep
        if q>0 and ep*q>=MIN_NOTIONAL:
            cap -= ep*q; in_pos=True; strat=st; entry=ep; sl=s; tp=t; qty=q; ei=i

    for i in range(80, len(df1)):
        t = df1.iloc[i]["close_time"]
        df4s = df4[df4["close_time"] <= t]
        if len(df4s) < 65: continue
        df1s = df1.iloc[:i+1]
        price=float(df1s.iloc[-1]["close"]); hi=float(df1s.iloc[-1]["high"]); lo=float(df1s.iloc[-1]["low"])
        ts=str(t)

        regime=None
        if multi_regime:
            n4=len(df4s)
            if n4!=last4: cached=detect_regime(df4s); last4=n4
            regime=cached.mode; rc[regime.value]+=1

        if regime==Regime.BEAR:
            if in_pos: close(price,"BEAR",i,ts)
            equity.append({"time":ts,"equity":cap}); continue

        if in_pos:
            if lo<=sl: close(sl,"SL",i,ts); continue
            if hi>=tp: close(tp,"TP",i,ts); continue

        if regime==Regime.SIDEWAYS:
            sig=mr.compute(df1s)
            if in_pos and sig.sell_signal: close(price,"MR",i,ts); continue
            if not in_pos and sig.buy_signal:
                ep=price*(1+SLIPPAGE_PCT)
                open_tr(ep, ep-sig.atr_value*slm, ep+sig.atr_value*tpm, "MEAN_REVERSION", i)
        else:
            sig=donal.compute(df1s, df4s)
            if in_pos and sig.sell_signal: close(price,"TREND",i,ts); continue
            if not in_pos and sig.buy_signal:
                ep=price*(1+SLIPPAGE_PCT)
                open_tr(ep, ep-sig.atr_value*sld, ep+sig.atr_value*tpd, "DONAL", i)

        equity.append({"time":ts,"equity":cap+price*qty if in_pos else cap})

    if in_pos: close(float(df1.iloc[-1]["close"]),"END",len(df1)-1,str(df1.iloc[-1]["close_time"]))
    tot=sum(rc.values()) or 1
    rd={k:round(v/tot*100,1) for k,v in rc.items()}
    return {"symbol":symbol,"trades":trades,"equity":equity,
            "metrics":calc(trades,capital,cap,equity,rd),"regime":rd}

def calc(trades,c0,c1,equity,rd):
    if not trades: return {"total_trades":0,"regime_distribution_pct":rd}
    w=[t for t in trades if t["pnl_usdt"]>0]; l=[t for t in trades if t["pnl_usdt"]<=0]
    gp=sum(t["pnl_usdt"] for t in w); gl=abs(sum(t["pnl_usdt"] for t in l))
    peak=0.0; mdd=0.0
    for p in equity:
        peak=max(peak,p["equity"])
        if peak>0: mdd=max(mdd,(peak-p["equity"])/peak*100)
    def bd(key):
        out={}
        for t in trades:
            d=out.setdefault(t[key],{"n":0,"w":0,"p":0.0})
            d["n"]+=1; d["p"]+=t["pnl_usdt"]
            if t["pnl_usdt"]>0: d["w"]+=1
        return {k:{"count":v["n"],"win_rate":round(v["w"]/v["n"]*100,1),"pnl":round(v["p"],4)} for k,v in out.items()}
    return {"initial":c0,"final":round(c1,2),"return_pct":round((c1-c0)/c0*100,2),
            "total_trades":len(trades),"wins":len(w),"losses":len(l),
            "win_rate":round(len(w)/len(trades)*100,1),
            "profit_factor":round(gp/gl,2) if gl else float("inf"),
            "max_dd":round(mdd,2),"by_strategy":bd("strategy"),"by_exit":bd("exit_type"),
            "regime_distribution_pct":rd}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",default="BNBUSDT")
    p.add_argument("--months",type=int,default=0)
    p.add_argument("--capital",type=float,default=1000)
    p.add_argument("--risk_pct",type=float,default=0.5)
    p.add_argument("--no_regime",action="store_true")
    a=p.parse_args()

    cfg=ConfigLoader("config.yaml").load()
    df1=load(a.symbol,"1h"); df4=load(a.symbol,"4h")
    res=run_backtest(a.symbol,df1,df4,cfg,a.capital,a.risk_pct,
                     cfg["risk"]["max_exposure_per_asset_pct"],not a.no_regime)
    m=res["metrics"]
    print(f"\n=== {a.symbol} | Multi-Regime {'OFF' if a.no_regime else 'ON'} ===")
    if m.get("total_trades",0)==0: print("No trades"); return
    rd=m.get("regime_distribution_pct",{})
    print(f"Regime: T {rd.get('TREND',0)}% | S {rd.get('SIDEWAYS',0)}% | B {rd.get('BEAR',0)}%")
    print(f"Return {m['return_pct']:+.2f}% | WR {m['win_rate']}% | PF {m['profit_factor']} | MaxDD {m['max_dd']}%")
    for s,d in m.get("by_strategy",{}).items(): print(f"  {s}: {d['count']}x WR {d['win_rate']}% ${d['pnl']:+.2f}")
    for e,d in m.get("by_exit",{}).items(): print(f"  {e}: {d['count']}x ${d['pnl']:+.2f}")

    os.makedirs(RESULTS_DIR,exist_ok=True)
    suf="noregime" if a.no_regime else "regime"
    with open(os.path.join(RESULTS_DIR,f"trades_{a.symbol}_{suf}.jsonl"),"w") as f:
        for t in res["trades"]: f.write(json.dumps(t)+"\n")
    pd.DataFrame(res["equity"]).to_csv(os.path.join(RESULTS_DIR,f"equity_{a.symbol}_{suf}.csv"),index=False)
    print(f"Saved to backtest/results/")

if __name__=="__main__":
    main()

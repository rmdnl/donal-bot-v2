"""Optimizer: grid search SL/TP multiplier untuk cari parameter terbaik.

Usage:
    python -m backtest.optimizer --symbol BNBUSDT --top 10
"""
import argparse, os, sys
import pandas as pd
from itertools import product
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import ConfigLoader
from backtest.engine import run_backtest, load

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BNBUSDT")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--sl_range", default="1.0,1.5,2.0,2.5")
    p.add_argument("--tp_range", default="2.0,2.5,3.0,3.5")
    a = p.parse_args()

    cfg = ConfigLoader("config.yaml").load()
    df1 = load(a.symbol, "1h")
    df4 = load(a.symbol, "4h")

    sls = [float(x) for x in a.sl_range.split(",")]
    tps = [float(x) for x in a.tp_range.split(",")]
    print(f"Grid: {len(sls)}x{len(tps)} = {len(sls)*len(tps)} combinations")

    results = []
    for sl, tp in product(sls, tps):
        cfg_copy = dict(cfg)
        cfg_copy["strategy"] = dict(cfg["strategy"])
        cfg_copy["strategy"]["donal"] = dict(cfg["strategy"]["donal"])
        cfg_copy["strategy"]["donal"]["sl_multiplier"] = sl
        cfg_copy["strategy"]["donal"]["tp_multiplier"] = tp

        res = run_backtest(a.symbol, df1, df4, cfg_copy, 1000.0, 0.5,
                          cfg["risk"]["max_exposure_per_asset_pct"], True)
        m = res["metrics"]
        if m.get("total_trades", 0) >= 10:
            results.append({
                "sl": sl, "tp": tp,
                "return": m["return_pct"],
                "wr": m["win_rate"],
                "pf": m["profit_factor"],
                "dd": m["max_dd"],
                "trades": m["total_trades"]
            })

    if not results:
        print("No valid configurations (all <10 trades)")
        return

    results.sort(key=lambda x: x["pf"], reverse=True)
    print(f"\nTop {a.top} Configurations (by Profit Factor):")
    print("-" * 80)
    for i, r in enumerate(results[:a.top], 1):
        print(f"{i:2d}. SL={r['sl']:.1f} TP={r['tp']:.1f} | "
              f"Return {r['return']:+6.1f}% | WR {r['wr']:5.1f}% | "
              f"PF {r['pf']:5.2f} | DD {r['dd']:5.1f}% | {r['trades']} trades")

    os.makedirs("backtest/results", exist_ok=True)
    out = os.path.join("backtest/results", f"optimizer_{a.symbol}.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\nSaved to {out}")

if __name__ == "__main__":
    main()

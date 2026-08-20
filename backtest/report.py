"""Report: generate chart equity curve + drawdown dari hasil backtest.

Usage:
    python -m backtest.report --symbol BNBUSDT
"""
import argparse, os, sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BNBUSDT")
    p.add_argument("--suffix", default="regime")
    a = p.parse_args()

    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    eq_file = os.path.join(results_dir, f"equity_{a.symbol}_{a.suffix}.csv")

    if not os.path.exists(eq_file):
        print(f"File not found: {eq_file}")
        print(f"Run backtest dulu: python -m backtest.engine --symbol {a.symbol}")
        return

    df = pd.read_csv(eq_file)
    df["time"] = pd.to_datetime(df["time"])

    # Equity curve
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax1.plot(df["time"], df["equity"], linewidth=2, color="#2E86AB")
    ax1.set_ylabel("Equity (USDT)", fontsize=12)
    ax1.set_title(f"{a.symbol} Equity Curve ({a.suffix})", fontsize=14, fontweight="bold")
    ax1.grid(True, alpha=0.3)

    # Drawdown
    peak = df["equity"].cummax()
    dd = (df["equity"] - peak) / peak * 100
    ax2.fill_between(df["time"], dd, 0, color="#A23B72", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)", fontsize=12)
    ax2.set_xlabel("Date", fontsize=12)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    chart_file = os.path.join(results_dir, f"chart_{a.symbol}_{a.suffix}.png")
    plt.savefig(chart_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Chart saved: {chart_file}")

    # Summary stats
    print(f"\n=== {a.symbol} Summary ===")
    print(f"Period: {df['time'].min().date()} → {df['time'].max().date()}")
    print(f"Start: {df['equity'].iloc[0]:.2f} USDT")
    print(f"End: {df['equity'].iloc[-1]:.2f} USDT")
    print(f"Return: {(df['equity'].iloc[-1] - df['equity'].iloc[0]) / df['equity'].iloc[0] * 100:+.2f}%")
    print(f"Max DD: {dd.min():.2f}%")
    print(f"Sharpe (daily): {df['equity'].pct_change().mean() / df['equity'].pct_change().std() * (252**0.5):.2f}")

if __name__ == "__main__":
    main()

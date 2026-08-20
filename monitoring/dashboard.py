"""Dashboard analitik donal-bot-pro (Streamlit, read-only).

Membaca data/trades.db (tabel trades + state).
Dijalankan sebagai service: donal-dashboard (port 8501).
"""
import os, sqlite3
import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "trades.db")

st.set_page_config(page_title="Donal Bot Pro", layout="wide")
st.title("📊 Donal Bot Pro — Analytics")

def col(df, *names):
    for n in names:
        if n in df.columns:
            return n
    return None

if not os.path.exists(DB):
    st.warning("Database belum ada — bot belum pernah berjalan.")
    st.stop()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
def q(sql):
    try:
        return pd.read_sql(sql, con)
    except Exception:
        return pd.DataFrame()

trades = q("SELECT * FROM trades")
state = q("SELECT * FROM state")

# ---------- Posisi terbuka ----------
st.header("🔓 Posisi Terbuka")
if state.empty:
    st.info("State kosong.")
else:
    ip = col(state, "in_position")
    if ip:
        open_pos = state[state[ip].astype(int) == 1]
        if open_pos.empty:
            st.info("Tidak ada posisi terbuka.")
        else:
            st.dataframe(open_pos, use_container_width=True)
    else:
        st.dataframe(state, use_container_width=True)

# ---------- Trades tertutup ----------
st.header("📈 Performa Trades")
if trades.empty:
    st.info("Belum ada trade tertutup. Data akan muncul setelah bot closing posisi.")
    st.stop()

tcol = col(trades, "exit_time", "close_time", "time")
pcol = col(trades, "pnl_usdt", "pnl", "pnl_pct")
scol = col(trades, "strategy")
ecol = col(trades, "exit_type", "exit_reason")

if tcol: trades[tcol] = pd.to_datetime(trades[tcol], errors="coerce")
if pcol: trades[pcol] = pd.to_numeric(trades[pcol], errors="coerce")
trades = trades.dropna(subset=[pcol]) if pcol else trades
trades = trades.sort_values(tcol) if tcol else trades

wins = trades[trades[pcol] > 0] if pcol else pd.DataFrame()
wr = len(wins) / len(trades) * 100 if len(trades) else 0
total = trades[pcol].sum() if pcol else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Trades", len(trades))
c2.metric("Win Rate", f"{wr:.1f}%")
c3.metric("Total PnL (USDT)", f"{total:+.2f}")
c4.metric("Avg PnL", f"{(total/len(trades)) if len(trades) else 0:+.3f}")

# ---------- Equity curve + drawdown ----------
st.header("💹 Equity Curve (cumulative PnL)")
if tcol and pcol:
    eq = trades[[tcol, pcol]].copy()
    eq["cum"] = eq[pcol].cumsum()
    eq["peak"] = eq["cum"].cummax()
    eq["dd"] = eq["cum"] - eq["peak"]
    st.line_chart(eq.set_index(tcol)["cum"], height=280)
    st.header("📉 Drawdown")
    st.area_chart(eq.set_index(tcol)["dd"], height=200, color="#A23B72")

# ---------- Breakdown ----------
st.header("🧮 Breakdown")
b1, b2 = st.columns(2)
if scol:
    g = trades.groupby(scol)[pcol].agg(["count", "sum"]).round(2)
    b1.subheader("Per Strategi")
    b1.dataframe(g, use_container_width=True)
if ecol:
    g2 = trades.groupby(ecol)[pcol].agg(["count", "sum"]).round(2)
    b2.subheader("Per Exit Type")
    b2.dataframe(g2, use_container_width=True)

# ---------- Recent trades ----------
st.header("🕒 20 Trade Terakhir")
st.dataframe(trades.tail(20).iloc[::-1], use_container_width=True)

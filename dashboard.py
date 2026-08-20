"""Streamlit dashboard: ringkasan performa + trade history.
Jalankan: streamlit run dashboard.py
"""
import os, sqlite3
import pandas as pd
import streamlit as st

DB = os.getenv("DB_PATH", "data/trades.db")

@st.cache_data(ttl=30)
def load_trades():
    if not os.path.exists(DB):
        return pd.DataFrame()
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM trades ORDER BY id", conn)
    conn.close()
    return df

st.set_page_config(page_title="DONAL Bot Pro", layout="wide")
st.title("DONAL Bot Pro Dashboard")

df = load_trades()
if df.empty:
    st.info("Belum ada trade tercatat. Jalankan bot dulu.")
    st.stop()

exits = df[df["event"] == "EXIT"].copy()

st.subheader("Ringkasan")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Trades", len(exits))
wins = exits[exits["pnl_usdt"] > 0]
c2.metric("Win Rate", f"{len(wins) / len(exits) * 100:.1f}%" if len(exits) else "0%")
gp = wins["pnl_usdt"].sum()
gl = abs(exits[exits["pnl_usdt"] <= 0]["pnl_usdt"].sum())
c3.metric("Profit Factor", f"{gp / gl:.2f}" if gl else "inf")
c4.metric("Total PnL", f"{exits['pnl_usdt'].sum():+.2f}")

st.subheader("Cumulative PnL (USDT)")
cum = exits.sort_values("id")["pnl_usdt"].cumsum()
st.line_chart(cum)

st.subheader("PnL per Symbol")
per_sym = exits.groupby("symbol")["pnl_usdt"].sum().sort_values(ascending=False)
st.bar_chart(per_sym)

st.subheader("PnL per Exit Type")
per_exit = exits.groupby("exit_type")["pnl_usdt"].sum()
st.bar_chart(per_exit)

st.subheader("Trade History")
st.dataframe(exits.sort_values("id", ascending=False), use_container_width=True)

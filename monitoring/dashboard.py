"""Live dashboard donal-bot-pro (Streamlit, read-only).

Auto-refresh tiap 10 detik: harga live, regime 4H, posisi + PnL berjalan,
equity curve, breakdown, trade terakhir, dan log tail.
Kendali trading tetap via Telegram (dashboard hanya monitoring).
"""
import glob, json, os, sqlite3, subprocess, sys
import pandas as pd
import requests
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
DB = os.path.join(BASE, "data", "trades.db")

from core.config_loader import ConfigLoader
from strategies.regime_detector import detect_regime

# Fallback kalau streamlit lama tanpa st.fragment
if not hasattr(st, "fragment"):
    def _frag(run_every=None):
        def deco(f): return f
        return deco
    st.fragment = _frag

st.set_page_config(page_title="Donal Bot Pro — Live", layout="wide")
st.title("📡 Donal Bot Pro — Live Dashboard")

@st.cache_data(ttl=300)
def load_cfg():
    return ConfigLoader(os.path.join(BASE, "config.yaml")).load()

CFG = load_cfg()
SYMBOLS = CFG["trading"]["symbols"]
MODE = CFG["trading"].get("mode", "testnet")

def svc(name):
    try:
        return subprocess.run(["systemctl", "is-active", name],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"

def col(df, *names):
    for n in names:
        if n in df.columns: return n
    return None

def q(sql):
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
        return pd.read_sql(sql, con)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def fetch_tickers():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                         params={"symbols": json.dumps(SYMBOLS)}, timeout=5)
        return {x["symbol"]: x for x in r.json()}
    except Exception:
        return {}

@st.cache_data(ttl=60)
def fetch_regime(sym):
    try:
        r = requests.get("https://api.binance.com/api/v3/klines",
                         params={"symbol": sym, "interval": "4h", "limit": 120}, timeout=5)
        k = r.json()
        cols = ["open_time","open","high","low","close","volume","close_time",
                "qvol","trades","tb","tq","ignore"]
        df = pd.DataFrame(k, columns=cols)
        for c in ["open","high","low","close","volume"]:
            df[c] = df[c].astype(float)
        return detect_regime(df).mode.value
    except Exception:
        return "?"

REGIME_ICON = {"TREND":"🟢","SIDEWAYS":"🟡","BEAR":"🔴","TRANSITION":"🟠"}

# ---------- Status bar ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Bot Service", svc("donal-bot-pro"))
c2.metric("Mode", MODE.upper())
c3.metric("Simbol", len(SYMBOLS))
c4.metric("Dashboard", svc("donal-dashboard"))

@st.fragment(run_every=10)
def live_market():
    st.header("🌐 Market Live (refresh 10s)")
    tick = fetch_tickers()
    rows = []
    for sym in SYMBOLS:
        t = tick.get(sym, {})
        price = float(t.get("lastPrice", 0))
        chg = float(t.get("priceChangePercent", 0))
        reg = fetch_regime(sym)
        rows.append({"Simbol": sym, "Harga": f"{price:,.2f}",
                     "24h": f"{chg:+.2f}%",
                     "Regime 4H": f"{REGIME_ICON.get(reg,'❓')} {reg}"})
    st.table(pd.DataFrame(rows))

    # Posisi terbuka + PnL live
    state = q("SELECT * FROM state")
    ip = col(state, "in_position")
    if not state.empty and ip:
        open_pos = state[state[ip].astype(int) == 1]
        if not open_pos.empty:
            st.subheader("🔓 Posisi Terbuka (PnL live)")
            prow = []
            for _, p in open_pos.iterrows():
                sym = p.get("symbol", "?")
                entry = float(p.get("entry_price", 0) or 0)
                qty = float(p.get("qty", 0) or 0)
                px = float(tick.get(sym, {}).get("lastPrice", 0) or 0)
                pnl = (px - entry) * qty if px and entry else 0
                pct = (px - entry) / entry * 100 if px and entry else 0
                prow.append({"Simbol": sym, "Entry": f"{entry:,.2f}",
                             "Now": f"{px:,.2f}", "PnL": f"{pnl:+.2f}",
                             "PnL%": f"{pct:+.2f}%"})
            st.table(pd.DataFrame(prow))
        else:
            st.info("Tidak ada posisi terbuka.")

@st.fragment(run_every=30)
def performance():
    st.header("📈 Performa (refresh 30s)")
    trades = q("SELECT * FROM trades")
    if trades.empty:
        st.info("Belum ada trade tertutup.")
        return
    tcol = col(trades, "exit_time", "close_time", "time")
    pcol = col(trades, "pnl_usdt", "pnl")
    if tcol: trades[tcol] = pd.to_datetime(trades[tcol], errors="coerce")
    if pcol: trades[pcol] = pd.to_numeric(trades[pcol], errors="coerce")
    trades = trades.sort_values(tcol)
    wins = trades[trades[pcol] > 0]
    total = trades[pcol].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Trades", len(trades))
    m2.metric("Win Rate", f"{len(wins)/len(trades)*100:.1f}%")
    m3.metric("Realized PnL", f"{total:+.2f} USDT")
    eq = trades[[tcol, pcol]].copy()
    eq["cum"] = eq[pcol].cumsum()
    eq["dd"] = eq["cum"] - eq["cum"].cummax()
    st.line_chart(eq.set_index(tcol)["cum"], height=250)
    st.area_chart(eq.set_index(tcol)["dd"], height=150, color="#A23B72")
    scol = col(trades, "strategy")
    ecol = col(trades, "exit_type", "exit_reason")
    if scol and ecol:
        a, b = st.columns(2)
        a.subheader("Per Strategi"); a.dataframe(trades.groupby(scol)[pcol].agg(["count","sum"]).round(2))
        b.subheader("Per Exit"); b.dataframe(trades.groupby(ecol)[pcol].agg(["count","sum"]).round(2))
    st.subheader("🕒 10 Trade Terakhir")
    st.dataframe(trades.tail(10).iloc[::-1], use_container_width=True)

live_market()
performance()

with st.expander("📜 Log tail (20 baris terakhir)"):
    logs = sorted(glob.glob(os.path.join(BASE, "logs", "*.log")), key=os.path.getmtime)
    if logs:
        st.code("".join(open(logs[-1]).readlines()[-20:]))
    else:
        st.info("File log tidak ditemukan.")
